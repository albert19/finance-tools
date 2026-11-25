<?php
namespace App\Tests;

use App\Repository\DbalAuthRepository;
use App\Service\Problem;
use Doctrine\DBAL\Connection;
use Doctrine\DBAL\DriverManager;
use PHPUnit\Framework\TestCase;

final class AuthRepositoryTest extends TestCase
{
    private Connection $db;
    private DbalAuthRepository $repository;

    protected function setUp(): void
    {
        $this->db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $this->db->executeStatement('CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, password_hash TEXT, roles TEXT, locale TEXT, disabled INTEGER)');
        $this->db->executeStatement('CREATE TABLE login_throttles (id TEXT PRIMARY KEY, attempts INTEGER, window_started TEXT)');
        $this->db->executeStatement('CREATE TABLE refresh_tokens (id TEXT PRIMARY KEY, user_id TEXT, family_id TEXT, token_hash TEXT UNIQUE, expires_at TEXT, consumed_at TEXT, revoked_at TEXT)');
        $this->db->insert('users', ['id' => 'alice', 'email' => 'alice@example.test', 'password_hash' => 'hash', 'roles' => '["user"]', 'locale' => 'en', 'disabled' => 0]);
        $this->repository = new DbalAuthRepository($this->db);
    }

    public function testUserAccessLocaleAndThrottleWindow(): void
    {
        self::assertNull($this->repository->findUserByEmail('missing@example.test'));
        self::assertSame('alice', $this->repository->findUserByEmail('alice@example.test')['id']);
        $this->repository->updateLocale('alice', 'es');
        self::assertSame('es', $this->repository->findUserById('alice')['locale']);
        for ($i = 1; $i <= 6; ++$i) {
            self::assertSame($i, $this->repository->recordAttempt('hashed-key'));
        }
        $this->db->update('login_throttles', ['window_started' => '2000-01-01 00:00:00'], ['id' => 'hashed-key']);
        self::assertSame(1, $this->repository->recordAttempt('hashed-key'));
        $this->repository->clearAttempts('hashed-key');
        self::assertSame(1, $this->repository->recordAttempt('hashed-key'));
    }

    public function testPasswordChangeRevokesSessionsOnlyWhenCurrentPasswordMatches(): void
    {
        $this->db->update('users', ['password_hash' => password_hash('old-password', PASSWORD_DEFAULT)], ['id' => 'alice']);
        $this->seedToken('old', 'family', 'secret');
        $newHash = password_hash('new-password', PASSWORD_DEFAULT);
        self::assertFalse($this->repository->changePassword('alice', 'wrong-password', $newHash));
        self::assertNull($this->db->fetchOne("SELECT revoked_at FROM refresh_tokens WHERE id = 'old'"));
        self::assertTrue($this->repository->changePassword('alice', 'old-password', $newHash));
        self::assertTrue(password_verify('new-password', $this->repository->findUserById('alice')['password_hash']));
        self::assertNotNull($this->db->fetchOne("SELECT revoked_at FROM refresh_tokens WHERE id = 'old'"));
    }

    public function testFailedSessionRevocationRollsBackPasswordChange(): void
    {
        $this->db->update('users', ['password_hash' => password_hash('old-password', PASSWORD_DEFAULT)], ['id' => 'alice']);
        $this->seedToken('old', 'family', 'secret');
        $this->db->executeStatement("CREATE TRIGGER block_revoke BEFORE UPDATE ON refresh_tokens BEGIN SELECT RAISE(ABORT, 'blocked'); END");

        $error = null;
        try {
            $this->repository->changePassword('alice', 'old-password', password_hash('new-password', PASSWORD_DEFAULT));
        } catch (\Throwable $e) {
            $error = $e;
        }
        self::assertNotNull($error);
        self::assertStringContainsString('blocked', $error->getMessage());
        self::assertTrue(password_verify('old-password', $this->repository->findUserById('alice')['password_hash']));
        self::assertNull($this->db->fetchOne("SELECT revoked_at FROM refresh_tokens WHERE id = 'old'"));
    }

    public function testRotationInsertsReplacementAtomicallyAndReuseRevokesEntireFamily(): void
    {
        $this->seedToken('old', 'family', 'original');
        $issued = $this->repository->rotateRefreshToken(hash('sha256', 'original'), function (array $user, string $family): array {
            $this->repository->insertRefreshToken('new', $user['id'], $family, hash('sha256', 'replacement'), '2999-01-01 00:00:00');
            return ['family' => $family];
        });
        self::assertSame(['family' => 'family'], $issued);
        self::assertNotNull($this->db->fetchOne("SELECT consumed_at FROM refresh_tokens WHERE id = 'old'"));
        self::assertSame('family', $this->db->fetchOne("SELECT family_id FROM refresh_tokens WHERE id = 'new'"));
        try {
            $this->repository->rotateRefreshToken(hash('sha256', 'original'), static fn (): array => self::fail('Reused token issued'));
            self::fail('Reused token accepted');
        } catch (Problem $e) {
            self::assertSame('refresh_reused', $e->problemCode);
        }
        self::assertFalse($this->db->isTransactionActive());
        self::assertNotNull($this->db->fetchOne("SELECT revoked_at FROM refresh_tokens WHERE id = 'new'"));
    }

    public function testFailedIssueRollsBackConsumptionAndReplacement(): void
    {
        $this->seedToken('old', 'family', 'original');
        try {
            $this->repository->rotateRefreshToken(hash('sha256', 'original'), function (array $user, string $family): array {
                $this->repository->insertRefreshToken('new', $user['id'], $family, hash('sha256', 'replacement'), '2999-01-01 00:00:00');
                throw new \RuntimeException('signing failed');
            });
            self::fail('Expected issue failure');
        } catch (\RuntimeException $e) {
            self::assertSame('signing failed', $e->getMessage());
        }
        self::assertNull($this->db->fetchOne("SELECT consumed_at FROM refresh_tokens WHERE id = 'old'"));
        self::assertFalse($this->db->fetchOne("SELECT id FROM refresh_tokens WHERE id = 'new'"));
        self::assertFalse($this->db->isTransactionActive());
    }

    public function testInvalidExpiredAndDisabledTokensDoNotIssueAndLogoutRevokesFamily(): void
    {
        $this->seedToken('old', 'family', 'original');
        $this->seedToken('expired', 'other', 'expired-secret', '2000-01-01 00:00:00');
        foreach (['missing', 'expired-secret'] as $token) {
            try {
                $this->repository->rotateRefreshToken(hash('sha256', $token), static fn (): array => self::fail('Invalid token issued'));
                self::fail('Invalid token accepted');
            } catch (Problem $e) {
                self::assertSame('invalid_refresh', $e->problemCode);
            }
        }
        $this->db->update('users', ['disabled' => 1], ['id' => 'alice']);
        try {
            $this->repository->rotateRefreshToken(hash('sha256', 'original'), static fn (): array => self::fail('Disabled user issued'));
            self::fail('Disabled user accepted');
        } catch (Problem $e) {
            self::assertSame('invalid_refresh', $e->problemCode);
        }
        self::assertNull($this->db->fetchOne("SELECT consumed_at FROM refresh_tokens WHERE id = 'old'"));
        $this->repository->revokeFamilyByTokenHash(hash('sha256', 'original'));
        self::assertNotNull($this->db->fetchOne("SELECT revoked_at FROM refresh_tokens WHERE id = 'old'"));
        self::assertNull($this->db->fetchOne("SELECT revoked_at FROM refresh_tokens WHERE id = 'expired'"));
    }

    public function testPruneKeepsLiveTokensForReuseDetectionAndDropsExpiredRows(): void
    {
        $this->seedToken('live', 'family', 'live-secret');
        $this->seedToken('consumed', 'family', 'consumed-secret');
        $this->db->executeStatement("UPDATE refresh_tokens SET consumed_at = CURRENT_TIMESTAMP WHERE id = 'consumed'");
        $this->seedToken('expired', 'old', 'expired-secret', '2000-01-01 00:00:00');
        $this->repository->recordAttempt('current-window');
        $this->repository->recordAttempt('stale-window');
        $this->db->update('login_throttles', ['window_started' => '2000-01-01 00:00:00'], ['id' => 'stale-window']);

        self::assertSame(['tokens' => 1, 'throttles' => 1], $this->repository->pruneExpired());
        self::assertSame(['consumed', 'live'], $this->db->fetchFirstColumn('SELECT id FROM refresh_tokens ORDER BY id'));
        self::assertSame(['current-window'], $this->db->fetchFirstColumn('SELECT id FROM login_throttles'));
    }

    public function testUpdatePasswordHash(): void
    {
        $this->repository->updatePasswordHash('alice', 'new-hash');
        self::assertSame('new-hash', $this->repository->findUserById('alice')['password_hash']);
    }

    private function seedToken(string $id, string $family, string $raw, string $expires = '2999-01-01 00:00:00'): void
    {
        $this->repository->insertRefreshToken($id, 'alice', $family, hash('sha256', $raw), $expires);
        self::assertSame(hash('sha256', $raw), $this->db->fetchOne('SELECT token_hash FROM refresh_tokens WHERE id = ?', [$id]));
    }
}
