<?php
namespace App\Port;

/** Persistence contract for owner-scoped budgets; mutations enforce version CAS atomically. */
interface BudgetRepository
{
    public function list(string $user, ?int $year): array;
    public function period(string $user, int $year, int $month): array;
    public function create(string $user, int $year, int $month, string $notes, ?array $copyFrom): array;
    public function update(string $user, string $id, int $version, ?string $notes): array;
    public function delete(string $user, string $id): void;
    public function saveLine(string $user, string $id, ?string $lineId, string $categoryId, string $amount, string $notes, int $version): array;
    public function deleteLine(string $user, string $id, string $lineId, int $version): void;
}
