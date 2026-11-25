<?php
namespace App\Port;

interface AuthRepository
{
    public function updateLocale(string $userId, string $locale): void;

    public function findUserById(string $userId): ?array;

    public function findUserByEmail(string $email): ?array;

    /** Atomically increments a 15-minute throttle window and returns the current attempt count. */
    public function recordAttempt(string $key): int;

    public function clearAttempts(string $key): void;

    public function updatePasswordHash(string $userId, string $passwordHash): void;

    /**
     * Delete refresh tokens past expiry (consumed ones are kept until then for
     * reuse detection) and throttle windows that have ended.
     *
     * @return array{tokens: int, throttles: int}
     */
    public function pruneExpired(): array;

    /**
     * Lock and consume a refresh token, then call $issue($user, $familyId) within
     * the same transaction. $issue must insert the replacement token before
     * returning. Reuse revokes the whole family and commits that revocation
     * before reporting refresh_reused.
     *
     * @param callable(array, string): array $issue
     */
    public function rotateRefreshToken(string $tokenHash, callable $issue): array;

    public function revokeFamilyByTokenHash(string $tokenHash): void;

    /** Verify the current password and atomically replace it and revoke sessions. */
    public function changePassword(string $userId, string $currentPassword, string $passwordHash): bool;

    public function insertRefreshToken(string $id, string $userId, string $familyId, string $tokenHash, string $expiresAt): void;
}
