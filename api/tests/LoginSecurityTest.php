<?php
namespace App\Tests;

use App\Repository\DbalAuthRepository;
use App\Service\Auth;
use App\Service\Problem;
use App\Service\SameOriginPolicy;
use Doctrine\DBAL\Connection;
use Doctrine\DBAL\DriverManager;
use Firebase\JWT\JWT;
use PHPUnit\Framework\TestCase;
use Symfony\Component\HttpFoundation\Request;

final class LoginSecurityTest extends TestCase
{
    private Connection $db;
    private Auth $auth;
    private string $dir;
    private string $privateKey;
    private array $previous = [];

    protected function setUp(): void
    {
        $this->db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $this->db->executeStatement('CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, password_hash TEXT, roles TEXT, locale TEXT, disabled INTEGER)');
        $this->db->executeStatement('CREATE TABLE login_throttles (id TEXT PRIMARY KEY, attempts INTEGER, window_started TEXT)');
        $this->db->executeStatement('CREATE TABLE refresh_tokens (id TEXT PRIMARY KEY, user_id TEXT, family_id TEXT, token_hash TEXT UNIQUE, expires_at TEXT, consumed_at TEXT, revoked_at TEXT)');
        foreach (['alice' => 0, 'bob' => 1] as $name => $disabled) {
            $this->db->insert('users', ['id' => $name, 'email' => "$name@example.test",
                'password_hash' => password_hash('correct-password', PASSWORD_ARGON2ID),
                'roles' => '["ROLE_USER"]', 'locale' => 'en', 'disabled' => $disabled]);
        }
        $this->auth = new Auth(new DbalAuthRepository($this->db), new SameOriginPolicy());

        $this->dir = sys_get_temp_dir().'/finance-jwt-'.bin2hex(random_bytes(4));
        mkdir($this->dir, 0700);
        $key = openssl_pkey_new(['private_key_type' => OPENSSL_KEYTYPE_EC, 'curve_name' => 'prime256v1']);
        openssl_pkey_export($key, $privateKey);
        $this->privateKey = $privateKey;
        file_put_contents("$this->dir/private.pem", $this->privateKey);
        file_put_contents("$this->dir/public.pem", openssl_pkey_get_details($key)['key']);
        foreach (['JWT_SECRET_KEY' => 'private.pem', 'JWT_PUBLIC_KEY' => 'public.pem'] as $name => $file) {
            $this->previous[$name] = getenv($name);
            putenv("$name=$this->dir/$file");
        }
    }

    protected function tearDown(): void
    {
        foreach ($this->previous as $name => $value) {
            putenv($value === false ? $name : "$name=$value");
        }
        array_map('unlink', glob("$this->dir/*"));
        rmdir($this->dir);
    }

    private function attempt(string $email, string $password, string $ip): ?Problem
    {
        try {
            $this->auth->login($email, $password, $ip);
            return null;
        } catch (Problem $e) {
            return $e;
        }
    }

    public function testAccountLimitIsPerSourceSoOtherClientsCanStillSignIn(): void
    {
        for ($i = 0; $i < 5; ++$i) {
            self::assertSame(401, $this->attempt('alice@example.test', 'wrong-password', '198.51.100.7')->status);
        }
        $throttled = $this->attempt('alice@example.test', 'correct-password', '198.51.100.7');
        self::assertSame(429, $throttled->status);
        self::assertSame(['Retry-After' => '900'], $throttled->headers);

        self::assertNull($this->attempt('ALICE@example.test', 'correct-password', '203.0.113.9'));
    }

    public function testIpLimitStopsSprayingAcrossEmails(): void
    {
        for ($i = 0; $i < 30; ++$i) {
            self::assertSame(401, $this->attempt("user$i@example.test", 'wrong-password', '198.51.100.7')->status);
        }
        self::assertSame(429, $this->attempt('alice@example.test', 'correct-password', '198.51.100.7')->status);
        self::assertNull($this->attempt('alice@example.test', 'correct-password', '203.0.113.9'));
    }

    public function testThrottledSourceCannotExhaustTheEmailCeiling(): void
    {
        for ($i = 0; $i < 40; ++$i) {
            $this->attempt('alice@example.test', 'wrong-password', '198.51.100.7');
        }
        $emailKey = hash('sha256', 'login:email|alice@example.test');
        self::assertSame(5, (int) $this->db->fetchOne('SELECT attempts FROM login_throttles WHERE id = ?', [$emailKey]));
    }

    public function testUnknownAndDisabledUsersGetTheSameGenericError(): void
    {
        foreach (['missing@example.test', 'bob@example.test'] as $email) {
            $error = $this->attempt($email, 'correct-password', '198.51.100.7');
            self::assertSame(401, $error->status);
            self::assertSame('invalid_credentials', $error->problemCode);
        }
    }

    public function testLegacyBcryptHashIsUpgradedAndSuccessClearsAccountThrottle(): void
    {
        $this->db->update('users', ['password_hash' => password_hash('correct-password', PASSWORD_BCRYPT)], ['id' => 'alice']);
        $this->attempt('alice@example.test', 'wrong-password', '198.51.100.7');
        self::assertNull($this->attempt('alice@example.test', 'correct-password', '198.51.100.7'));

        $hash = $this->db->fetchOne("SELECT password_hash FROM users WHERE id = 'alice'");
        self::assertSame(PASSWORD_ARGON2ID, password_get_info($hash)['algo']);
        self::assertTrue(password_verify('correct-password', $hash));
        $acctKey = hash('sha256', 'login:acct|alice@example.test|198.51.100.7');
        self::assertFalse($this->db->fetchOne('SELECT attempts FROM login_throttles WHERE id = ?', [$acctKey]));
    }

    public function testAccessTokenMustCarryIssuerAndAudience(): void
    {
        $session = $this->auth->login('alice@example.test', 'correct-password', '198.51.100.7');
        self::assertSame('alice', $this->auth->user($this->bearer($session['accessToken']))['id']);

        $now = time();
        foreach ([
            ['sub' => 'alice', 'iat' => $now, 'exp' => $now + 60],
            ['iss' => Auth::ISSUER, 'aud' => 'other-service', 'sub' => 'alice', 'iat' => $now, 'exp' => $now + 60],
            ['iss' => 'other-issuer', 'aud' => Auth::AUDIENCE, 'sub' => 'alice', 'iat' => $now, 'exp' => $now + 60],
        ] as $claims) {
            try {
                $this->auth->user($this->bearer(JWT::encode($claims, $this->privateKey, 'ES256')));
                self::fail('Accepted token with claims '.json_encode($claims));
            } catch (Problem $e) {
                self::assertSame(401, $e->status);
            }
        }
    }

    private function bearer(string $token): Request
    {
        return Request::create('http://example.test/api/me', server: ['HTTP_AUTHORIZATION' => "Bearer $token"]);
    }
}
