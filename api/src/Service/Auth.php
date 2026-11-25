<?php
namespace App\Service;

use App\Port\AuthRepository;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;
use Symfony\Component\HttpFoundation\Cookie;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Uid\Uuid;

final class Auth
{
    public const ISSUER = 'finance-api';
    public const AUDIENCE = 'finance-api';
    /** Attempts per 15 minutes, checked in order: client IP, email + IP, then a per-email ceiling. */
    private const LOGIN_LIMITS = ['ip' => 30, 'acct' => 5, 'email' => 100];
    private const PASSWORD_CHANGE_LIMIT = 5;

    public function __construct(
        private AuthRepository $repository,
        private SameOriginPolicy $originPolicy,
        private PasswordHasher $hasher = new PasswordHasher(),
    ) {}

    public function updateLocale(array $user, array $data): array
    {
        $locale = Inputs::text($data, 'locale', 5);
        if (!in_array($locale, ['en', 'es'], true)) { throw Problem::invalid('locale', 'Expected en or es'); }
        $this->repository->updateLocale($user['id'], $locale);
        $user['locale'] = $locale;
        return $user;
    }

    public function changePassword(array $user, array $data): void
    {
        $current = Inputs::text($data, 'currentPassword', 1024);
        $next = Inputs::text($data, 'newPassword', 1024);
        if ($error = PasswordHasher::policyError($next)) {
            throw Problem::invalid('newPassword', $error);
        }
        if (hash_equals($current, $next)) {
            throw Problem::invalid('newPassword', 'Choose a different password');
        }
        $key = hash('sha256', 'pwchange|'.$user['id']);
        if ($this->repository->recordAttempt($key) > self::PASSWORD_CHANGE_LIMIT) {
            throw Problem::throttled();
        }
        // 403, not 401: the bearer token is valid, and 401 would make clients refresh and retry.
        if (!$this->repository->changePassword($user['id'], $current, $this->hasher->hash($next))) {
            throw new Problem(403, 'invalid_credentials', 'Current password is incorrect');
        }
        $this->repository->clearAttempts($key);
    }

    public function user(Request $request): array
    {
        $header = $request->headers->get('Authorization', '');
        if (!preg_match('/^Bearer ([A-Za-z0-9_.-]+)$/', $header, $match)) { throw new Problem(401, 'unauthorized', 'Bearer token required'); }
        try {
            $claims = (array) JWT::decode($match[1], new Key($this->key('JWT_PUBLIC_KEY'), 'ES256'));
            if (!isset($claims['sub']) || !is_string($claims['sub'])
                || ($claims['iss'] ?? null) !== self::ISSUER || ($claims['aud'] ?? null) !== self::AUDIENCE) {
                throw new \RuntimeException('Invalid claims');
            }
            $user = $this->repository->findUserById($claims['sub']);
            if (!$user || $user['disabled']) { throw new \RuntimeException('Disabled user'); }
            return $this->present($user);
        } catch (\Throwable $e) {
            throw new Problem(401, 'unauthorized', 'Invalid or expired access token');
        }
    }

    public function login(string $email, string $password, string $clientIp): array
    {
        $email = strtolower($email);
        $keys = [];
        // Stop at the first exceeded limit so a throttled source cannot keep
        // feeding the per-email counter and lock the account out.
        foreach (['ip' => $clientIp, 'acct' => "$email|$clientIp", 'email' => $email] as $scope => $value) {
            $keys[$scope] = hash('sha256', "login:$scope|$value");
            if ($this->repository->recordAttempt($keys[$scope]) > self::LOGIN_LIMITS[$scope]) {
                throw Problem::throttled();
            }
        }
        $user = $this->repository->findUserByEmail($email);
        $hash = $user && !$user['disabled'] ? $user['password_hash'] : null;
        // Always verify one hash so response time does not reveal whether the account exists.
        if (!$this->hasher->verifyOrDummy($password, $hash)) {
            throw new Problem(401, 'invalid_credentials', 'Invalid credentials');
        }
        if ($this->hasher->needsRehash($hash)) {
            $this->repository->updatePasswordHash($user['id'], $this->hasher->hash($password));
        }
        $result = $this->issue($user, Uuid::v7()->toRfc4122());
        $this->repository->clearAttempts($keys['acct']);
        $this->repository->clearAttempts($keys['email']);
        return $result;
    }

    public function refresh(string $token): array
    {
        return $this->repository->rotateRefreshToken(hash('sha256', $token), $this->issue(...));
    }

    /** @return array{tokens: int, throttles: int} */
    public function prune(): array
    {
        return $this->repository->pruneExpired();
    }

    public function logout(string $token): void
    {
        $this->repository->revokeFamilyByTokenHash(hash('sha256', $token));
    }

    private function issue(array $user, string $family): array
    {
        $ttl = max(1, (int)(getenv('JWT_TTL') ?: 120));
        $refreshTtl = max(1, (int)(getenv('REFRESH_TOKEN_TTL') ?: 2592000));
        $now = time();
        $roles = is_array($user['roles']) ? $user['roles'] : json_decode($user['roles'], true);
        $jwt = JWT::encode(['iss' => self::ISSUER, 'aud' => self::AUDIENCE, 'sub' => $user['id'], 'roles' => $roles, 'iat' => $now, 'exp' => $now + $ttl, 'jti' => Uuid::v7()->toRfc4122()], $this->key('JWT_PRIVATE_KEY'), 'ES256');
        $raw = bin2hex(random_bytes(32));
        $this->repository->insertRefreshToken(
            Uuid::v7()->toRfc4122(), $user['id'], $family,
            hash('sha256', $raw), gmdate('Y-m-d H:i:s', $now + $refreshTtl),
        );
        return ['accessToken' => $jwt, 'expiresIn' => $ttl, 'user' => $this->present($user), 'refresh' => $raw, 'refreshTtl' => $refreshTtl];
    }

    public function cookie(string $token, int $ttl): Cookie
    {
        return Cookie::create('refresh_token', $token, time() + $ttl, '/api/auth', null, true, true, false, Cookie::SAMESITE_STRICT);
    }

    public function origin(Request $request): void
    {
        // Refresh cookies must never be usable by a different origin, even when
        // the browser sends credentials on a cross-origin request.
        if (!$this->originPolicy->matches($request) ||
            $request->headers->get('X-Requested-With') !== 'XMLHttpRequest') {
            throw new Problem(403, 'origin_denied', 'Origin and X-Requested-With required');
        }
    }

    private function key(string $name): string
    {
        $file = getenv($name === 'JWT_PRIVATE_KEY' ? 'JWT_SECRET_KEY' : $name);
        $key = $file ? @file_get_contents($file) : false;
        if (!$key) { throw new \RuntimeException("$name must point to a readable ES256 PEM key"); }
        return $key;
    }

    public function present(array $user): array
    {
        return ['id' => $user['id'], 'email' => $user['email'],
            'roles' => is_array($user['roles']) ? $user['roles'] : json_decode($user['roles'], true),
            'locale' => $user['locale']];
    }
}
