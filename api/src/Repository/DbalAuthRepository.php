<?php
namespace App\Repository;

use App\Port\AuthRepository;
use App\Service\Problem;
use Doctrine\DBAL\Connection;
use Doctrine\DBAL\Platforms\SQLitePlatform;

final class DbalAuthRepository implements AuthRepository
{
    public function __construct(private Connection $db) {}

    public function updateLocale(string $userId, string $locale): void
    {
        $this->db->update('users', ['locale' => $locale], ['id' => $userId]);
    }

    public function findUserById(string $userId): ?array
    {
        return $this->db->fetchAssociative('SELECT * FROM users WHERE id = ?', [$userId]) ?: null;
    }

    public function findUserByEmail(string $email): ?array
    {
        return $this->db->fetchAssociative('SELECT * FROM users WHERE email = ?', [$email]) ?: null;
    }

    public function recordAttempt(string $key): int
    {
        if ($this->db->getDatabasePlatform() instanceof SQLitePlatform) {
            $this->db->executeStatement("INSERT INTO login_throttles (id, attempts, window_started) VALUES (?, 1, CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET attempts = CASE WHEN window_started < datetime('now', '-15 minutes') THEN 1 ELSE attempts + 1 END, window_started = CASE WHEN window_started < datetime('now', '-15 minutes') THEN CURRENT_TIMESTAMP ELSE window_started END", [$key]);
        } else {
            $this->db->executeStatement("INSERT INTO login_throttles (id, attempts, window_started) VALUES (?, 1, UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE attempts = IF(window_started < UTC_TIMESTAMP() - INTERVAL 15 MINUTE, 1, attempts + 1), window_started = IF(window_started < UTC_TIMESTAMP() - INTERVAL 15 MINUTE, UTC_TIMESTAMP(), window_started)", [$key]);
        }
        return (int) $this->db->fetchOne('SELECT attempts FROM login_throttles WHERE id = ?', [$key]);
    }

    public function clearAttempts(string $key): void
    {
        $this->db->delete('login_throttles', ['id' => $key]);
    }

    public function updatePasswordHash(string $userId, string $passwordHash): void
    {
        $this->db->update('users', ['password_hash' => $passwordHash], ['id' => $userId]);
    }

    public function pruneExpired(): array
    {
        $sqlite = $this->db->getDatabasePlatform() instanceof SQLitePlatform;
        $windowEnd = $sqlite ? "datetime('now', '-15 minutes')" : 'UTC_TIMESTAMP() - INTERVAL 15 MINUTE';
        return [
            'tokens' => (int) $this->db->executeStatement('DELETE FROM refresh_tokens WHERE expires_at < '.$this->utcNow()),
            'throttles' => (int) $this->db->executeStatement('DELETE FROM login_throttles WHERE window_started < '.$windowEnd),
        ];
    }

    public function rotateRefreshToken(string $tokenHash, callable $issue): array
    {
        $this->db->beginTransaction();
        try {
            $lock = $this->db->getDatabasePlatform() instanceof SQLitePlatform ? '' : ' FOR UPDATE';
            $row = $this->db->fetchAssociative('SELECT * FROM refresh_tokens WHERE token_hash = ?'.$lock, [$tokenHash]);
            if (!$row) { throw new Problem(401, 'invalid_refresh', 'Invalid refresh token'); }
            if ($row['consumed_at'] !== null) {
                $this->db->executeStatement('UPDATE refresh_tokens SET revoked_at = '.$this->utcNow().' WHERE family_id = ?', [$row['family_id']]);
                $this->db->commit();
                // Throw only after commit so a reused token cannot roll back family revocation.
                throw new Problem(401, 'refresh_reused', 'Refresh token reuse detected; session revoked');
            }
            if ($row['revoked_at'] !== null || strtotime($row['expires_at'].' UTC') <= time()) {
                throw new Problem(401, 'invalid_refresh', 'Expired or revoked refresh token');
            }
            $user = $this->db->fetchAssociative('SELECT * FROM users WHERE id = ?'.$lock, [$row['user_id']]);
            if (!$user || $user['disabled']) { throw new Problem(401, 'invalid_refresh', 'User disabled'); }
            $this->db->executeStatement('UPDATE refresh_tokens SET consumed_at = '.$this->utcNow().' WHERE id = ?', [$row['id']]);
            $result = $issue($user, $row['family_id']);
            $this->db->commit();
            return $result;
        } catch (\Throwable $e) {
            if ($this->db->isTransactionActive()) { $this->db->rollBack(); }
            throw $e;
        }
    }

    public function revokeFamilyByTokenHash(string $tokenHash): void
    {
        $family = $this->db->fetchOne('SELECT family_id FROM refresh_tokens WHERE token_hash = ?', [$tokenHash]);
        if ($family) { $this->db->executeStatement('UPDATE refresh_tokens SET revoked_at = '.$this->utcNow().' WHERE family_id = ?', [$family]); }
    }

    public function changePassword(string $userId, string $currentPassword, string $passwordHash): bool
    {
        return $this->db->transactional(function () use ($userId, $currentPassword, $passwordHash): bool {
            $lock = $this->db->getDatabasePlatform() instanceof SQLitePlatform ? '' : ' FOR UPDATE';
            $currentHash = $this->db->fetchOne('SELECT password_hash FROM users WHERE id = ?'.$lock, [$userId]);
            if (!is_string($currentHash) || !password_verify($currentPassword, $currentHash)) {
                return false;
            }
            $this->db->update('users', ['password_hash' => $passwordHash], ['id' => $userId]);
            $this->db->executeStatement('UPDATE refresh_tokens SET revoked_at = '.$this->utcNow().' WHERE user_id = ?', [$userId]);
            return true;
        });
    }

    public function insertRefreshToken(string $id, string $userId, string $familyId, string $tokenHash, string $expiresAt): void
    {
        $this->db->insert('refresh_tokens', [
            'id' => $id, 'user_id' => $userId, 'family_id' => $familyId,
            'token_hash' => $tokenHash, 'expires_at' => $expiresAt,
        ]);
    }

    private function utcNow(): string
    {
        return $this->db->getDatabasePlatform() instanceof SQLitePlatform ? 'CURRENT_TIMESTAMP' : 'UTC_TIMESTAMP()';
    }
}
