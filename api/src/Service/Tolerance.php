<?php
namespace App\Service;

/** Relative tolerance from a percentage env var (0–100), defaulting to 2%. */
final class Tolerance
{
    public static function fromEnv(string $name): float
    {
        $configured = getenv($name);
        return $configured !== false && is_numeric($configured) && is_finite((float)$configured)
            && (float)$configured >= 0 && (float)$configured <= 100
            ? (float)$configured / 100 : 0.02;
    }
}
