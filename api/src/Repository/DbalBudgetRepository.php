<?php
namespace App\Repository;

use App\Port\BudgetRepository;
use App\Service\Problem;

/** DBAL-backed budget persistence; all read/write paths are owner-scoped. */
final class DbalBudgetRepository implements BudgetRepository
{
    public function __construct(private FinanceStore $store) {}

    public function list(string $user, ?int $year): array
    {
        $rows = $this->store->db->fetchAllAssociative(
            'SELECT * FROM monthly_budgets WHERE user_id = ?'.($year !== null ? ' AND year = ?' : '').' ORDER BY year, month',
            $year !== null ? [$user, $year] : [$user]
        );
        return array_map(fn($row) => $this->store->budget($row['id'], $user), $rows);
    }

    public function period(string $user, int $year, int $month): array
    {
        $id = $this->store->db->fetchOne(
            'SELECT id FROM monthly_budgets WHERE user_id = ? AND year = ? AND month = ?',
            [$user, $year, $month]
        );
        if (!$id) { throw new Problem(404, 'not_found', 'Budget not found'); }
        return $this->store->budget($id, $user);
    }

    public function create(string $user, int $year, int $month, string $notes, ?array $copyFrom): array
    {
        $id = $this->store->id();
        $this->store->db->transactional(function () use ($user, $year, $month, $notes, $copyFrom, $id): void {
            $copy = [];
            if ($copyFrom !== null) {
                [$y, $m] = $copyFrom;
                $source = $this->store->db->fetchOne(
                    'SELECT id FROM monthly_budgets WHERE user_id = ? AND year = ? AND month = ?',
                    [$user, $y, $m]
                );
                if (!$source) { throw new Problem(404, 'not_found', 'Source budget not found'); }
                foreach ($this->store->db->fetchAllAssociative(
                    'SELECT category_id, amount, notes FROM budget_lines WHERE budget_id = ?',
                    [$source]
                ) as $line) {
                    $this->store->category($line['category_id'], $user);
                    $copy[] = $line;
                }
            }
            $this->store->db->insert('monthly_budgets', [
                'id' => $id, 'user_id' => $user, 'year' => $year, 'month' => $month, 'notes' => $notes,
            ]);
            foreach ($copy as $line) {
                $this->store->db->insert('budget_lines', [
                    'id' => $this->store->id(), 'budget_id' => $id, ...$line,
                ]);
            }
        });
        return $this->store->budget($id, $user);
    }

    public function update(string $user, string $id, int $version, ?string $notes): array
    {
        $this->store->db->transactional(function () use ($user, $id, $version, $notes): void {
            $this->store->owned('monthly_budgets', $id, $user);
            $this->store->changed($id, $user, $version);
            if ($notes !== null) {
                $this->store->db->update('monthly_budgets', ['notes' => $notes], ['id' => $id, 'user_id' => $user]);
            }
        });
        return $this->store->budget($id, $user);
    }

    public function delete(string $user, string $id): void
    {
        $this->store->db->transactional(function () use ($user, $id): void {
            $this->store->owned('monthly_budgets', $id, $user);
            $this->store->db->delete('monthly_budgets', ['id' => $id, 'user_id' => $user]);
        });
    }

    public function saveLine(string $user, string $id, ?string $lineId, string $categoryId, string $amount, string $notes, int $version): array
    {
        $put = $lineId !== null;
        $lineId ??= $this->store->id();
        $this->store->db->transactional(function () use ($user, $id, $lineId, $categoryId, $amount, $notes, $version, $put): void {
            $this->store->owned('monthly_budgets', $id, $user);
            if ($put) { $this->store->line($id, $lineId); }
            $category = $this->store->category($categoryId, $user);
            $this->store->changed($id, $user, $version);
            $values = ['category_id' => $category['id'], 'amount' => $amount, 'notes' => $notes];
            if ($put) {
                $this->store->db->update('budget_lines', $values, ['id' => $lineId, 'budget_id' => $id]);
            } else {
                $this->store->db->insert('budget_lines', ['id' => $lineId, 'budget_id' => $id, ...$values]);
            }
        });
        return $this->store->budget($id, $user);
    }

    public function deleteLine(string $user, string $id, string $lineId, int $version): void
    {
        $this->store->db->transactional(function () use ($user, $id, $lineId, $version): void {
            $this->store->owned('monthly_budgets', $id, $user);
            $this->store->line($id, $lineId);
            $this->store->changed($id, $user, $version);
            $this->store->db->delete('budget_lines', ['id' => $lineId, 'budget_id' => $id]);
        });
    }
}
