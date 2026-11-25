<?php
namespace App\Port;

use App\Entity\Investment;

interface InvestmentRepository
{
    public function findOwned(string $user, string $id): ?Investment;

    public function listForOwner(string $user): array;

    public function create(string $user, string $name, string $startDate, string $notes, array $parameters): Investment;

    public function save(Investment $investment): void;

    public function delete(Investment $investment): void;

    public function snapshots(Investment $investment): array;

    /** Atomically lock the owned investment, check date/duplicates, and insert a snapshot. */
    public function addSnapshot(string $user, string $id, string $date, string $value, string $contribution, string $withdrawal, string $note): string;

    /** Returns false if the snapshot does not belong to this investment. */
    public function deleteSnapshot(Investment $investment, string $snapshotId): bool;
}
