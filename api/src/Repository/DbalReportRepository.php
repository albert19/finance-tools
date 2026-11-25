<?php
namespace App\Repository;

use App\Port\ReportRepository;

/** DBAL read model: scope budget and transaction aggregates to the requesting user. */
final class DbalReportRepository implements ReportRepository
{
    public function __construct(private FinanceStore $store) {}

    public function monthlyData(string $user, int $year, int $month): array
    {
        $id = $this->store->db->fetchOne(
            'SELECT id FROM monthly_budgets WHERE user_id = ? AND year = ? AND month = ?',
            [$user, $year, $month]
        );
        $planned = $this->store->db->fetchAllAssociative(
            'SELECT c.id AS categoryId, c.name, c.kind, COALESCE(SUM(l.amount), 0) AS amount FROM categories c JOIN budget_lines l ON l.category_id = c.id JOIN monthly_budgets b ON b.id = l.budget_id WHERE b.user_id = ? AND b.year = ? AND b.month = ? GROUP BY c.id, c.name, c.kind',
            [$user, $year, $month]
        );
        $start = sprintf('%04d-%02d-01', $year, $month);
        $actual = $this->store->db->fetchAllAssociative(
            'SELECT c.id AS categoryId, c.name, c.kind, COALESCE(SUM(t.amount), 0) AS amount FROM transactions t JOIN categories c ON c.id = t.category_id WHERE t.user_id = ? AND t.date >= ? AND t.date < ? GROUP BY c.id, c.name, c.kind',
            [$user, $start, (new \DateTimeImmutable($start))->modify('+1 month')->format('Y-m-d')]
        );
        return ['budget' => $id ? $this->store->budget($id, $user) : null, 'planned' => $planned, 'actual' => $actual];
    }
}
