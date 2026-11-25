<?php
namespace App\Service;

final class Problem extends \RuntimeException
{
    /** @param array<string, string> $headers Extra response headers, e.g. Retry-After. */
    public function __construct(
        public readonly int $status,
        public readonly string $problemCode,
        string $message,
        public readonly array $errors = [],
        public readonly array $headers = [],
    ) { parent::__construct($message); }

    public static function invalid(string $field, string $message): self
    {
        return new self(422, 'validation_error', 'Invalid input', [['field' => $field, 'code' => 'invalid', 'params' => [], 'message' => $message]]);
    }

    public static function throttled(string $message = 'Try again in 15 minutes'): self
    {
        return new self(429, 'too_many_attempts', $message, [], ['Retry-After' => '900']);
    }
}
