<?php
namespace App\Service;

/** Single Argon2id hashing and password policy for the API and console commands. */
final class PasswordHasher
{
    // Argon2id hash of a random throwaway string with the default cost, used to
    // keep login timing equal when the account does not exist or is disabled.
    private const DUMMY_HASH = '$argon2id$v=19$m=65536,t=4,p=1$NUl2dS9Yckg1Q0lvVTl2Yg$m9rIYSoyfJzTTddej32lPoor5Ri01Ji7bePTOwVh1gs';

    public function hash(string $password): string
    {
        return password_hash($password, PASSWORD_ARGON2ID);
    }

    /** Always performs one hash verification; returns false when $hash is null. */
    public function verifyOrDummy(string $password, ?string $hash): bool
    {
        $valid = password_verify($password, $hash ?? self::DUMMY_HASH);
        return $hash !== null && $valid;
    }

    public function needsRehash(string $hash): bool
    {
        return password_needs_rehash($hash, PASSWORD_ARGON2ID);
    }

    public static function policyError(string $password): ?string
    {
        return strlen($password) < 12 || strlen($password) > 1024 || preg_match('/\s/', $password)
            ? 'Use 12 to 1024 characters without spaces' : null;
    }
}
