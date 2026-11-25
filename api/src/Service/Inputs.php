<?php
namespace App\Service;

use Symfony\Component\HttpFoundation\Request;

final class Inputs
{
    public static function json(Request $request): array
    {
        if (!str_contains($request->headers->get('Content-Type', ''), 'application/json')) {
            throw new Problem(415, 'unsupported_media_type', 'Expected application/json');
        }
        $raw = $request->getContent();
        try { $data = json_decode($raw, true, 32, JSON_THROW_ON_ERROR); }
        catch (\JsonException) { throw Problem::invalid('body', 'Invalid JSON'); }
        if (!is_array($data) || !str_starts_with(ltrim($raw), '{')) { throw Problem::invalid('body', 'Expected JSON object'); }
        return $data;
    }

    public static function text(array $data, string $key, int $max = 255, bool $required = true): string
    {
        $value = $data[$key] ?? ($required ? null : '');
        if (!is_string($value) || ($required && trim($value) === '') || strlen($value) > $max) {
            throw Problem::invalid($key, "Expected non-empty text up to $max characters");
        }
        return trim($value);
    }

    public static function period(mixed $year, mixed $month): array
    {
        if (filter_var($year, FILTER_VALIDATE_INT) === false || (int)$year < 1900 || (int)$year > 9999 ||
            filter_var($month, FILTER_VALIDATE_INT) === false || (int)$month < 1 || (int)$month > 12) {
            throw Problem::invalid('period', 'Expected year 1900–9999 and month 1–12');
        }
        return [(int)$year, (int)$month];
    }

    public static function money(array $data, string $key, bool $positive = true): string
    {
        $value = $data[$key] ?? null;
        if ((!is_string($value) && !is_int($value) && !is_float($value)) || !preg_match('/^\d{1,13}(\.\d{1,2})?$/D', (string)$value) || ($positive && (float)$value <= 0)) {
            throw Problem::invalid($key, 'Expected a positive decimal amount (at most two decimal places)');
        }
        return number_format((float)$value, 2, '.', '');
    }

    public static function date(array $data, string $key): string
    {
        $v = self::text($data, $key, 10);
        $date = \DateTimeImmutable::createFromFormat('!Y-m-d', $v);
        if (!$date || $date->format('Y-m-d') !== $v) { throw Problem::invalid($key, 'Expected YYYY-MM-DD'); }
        return $v;
    }
}
