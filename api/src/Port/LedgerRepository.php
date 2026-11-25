<?php
namespace App\Port;

/** Persistence operations for the category and transaction use cases. */
interface LedgerRepository
{
    public function categories(string $user, bool $includeArchived): array;
    public function category(string $user, string $id): array;
    public function createCategory(string $user, string $kind, string $name): array;
    /** @param array<string, list<string>> $defaults */
    public function createDefaults(string $user, array $defaults): array;
    public function updateCategory(string $user, string $id, array $patch): array;
    public function categoryInUse(string $user, string $id): bool;
    public function deleteCategory(string $user, string $id): void;

    public function transactions(string $user, string $start, string $end, ?string $kind): array;
    public function transaction(string $user, string $id): array;
    public function saveTransaction(string $user, ?string $id, array $values): array;
    public function deleteTransaction(string $user, string $id): void;
}
