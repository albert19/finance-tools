<?php
namespace App\Repository;

use App\Service\Problem;
use Doctrine\DBAL\Connection;
use Symfony\Component\Uid\Uuid;

final class FinanceStore
{
    public function __construct(public readonly Connection $db) {}

    public function id(): string { return Uuid::v7()->toRfc4122(); }

    public function owned(string $table, string $id, string $user): array
    {
        if (!in_array($table, ['categories', 'monthly_budgets', 'transactions', 'investments'], true)) {
            throw new \LogicException('Invalid table');
        }
        $row = $this->db->fetchAssociative("SELECT * FROM $table WHERE id = ? AND user_id = ?", [$id, $user]);
        if (!$row) { throw new Problem(404, 'not_found', 'Not found'); }
        return $row;
    }

    public function category(string $id, string $user): array
    {
        $category = $this->owned('categories', $id, $user);
        if ($category['archived']) { throw Problem::invalid('categoryId', 'Category is archived'); }
        return $category;
    }

    public function budget(string $id, string $user): array
    {
        $budget = $this->owned('monthly_budgets', $id, $user);
        $budget['lines'] = $this->db->fetchAllAssociative(
            'SELECT l.id, l.category_id AS categoryId, c.name AS categoryName, c.kind, l.amount, l.notes FROM budget_lines l JOIN categories c ON c.id = l.category_id WHERE l.budget_id = ? ORDER BY c.kind, c.name, l.id', [$id]);
        return $budget;
    }

    public function changed(string $id, string $user, int $version): void
    {
        $updated = $this->db->executeStatement('UPDATE monthly_budgets SET version = version + 1 WHERE id = ? AND user_id = ? AND version = ?', [$id, $user, $version]);
        if (!$updated) { throw new Problem(409, 'version_conflict', 'Budget was changed; reload and try again'); }
    }

    public function line(string $budgetId, string $lineId): array
    {
        $line = $this->db->fetchAssociative('SELECT * FROM budget_lines WHERE id = ? AND budget_id = ?', [$lineId, $budgetId]);
        if (!$line) { throw new Problem(404, 'not_found', 'Line not found'); }
        return $line;
    }
}
