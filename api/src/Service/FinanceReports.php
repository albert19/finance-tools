<?php
namespace App\Service;

use App\Port\ReportRepository;

/** Read-side reporting: repository applies owner predicates to source data. */
final class FinanceReports
{
    public function __construct(private ReportRepository $reports) {}

    public function monthly(string $uid, int $year, int $month): array
    {
        Inputs::period($year, $month);
        $data = $this->reports->monthlyData($uid, $year, $month);
        return $this->variance($year, $month, $data['budget'], $data['planned'], $data['actual']);
    }

    public function annual(string $uid, int $year): array
    {
        Inputs::period($year, 1);
        $months = [];
        for ($m = 1; $m <= 12; ++$m) { $months[] = $this->monthly($uid, $year, $m); }
        $planned = []; $actual = [];
        foreach ($months as $month) {
            foreach ($month['rows'] as $row) {
                $id = $row['categoryId'];
                $base = ['categoryId' => $id, 'name' => $row['name'], 'kind' => $row['kind'], 'amount' => 0];
                $planned[$id] ??= $base; $actual[$id] ??= $base;
                $planned[$id]['amount'] += $row['planned'];
                $actual[$id]['amount'] += $row['actual'];
            }
        }
        $annual = $this->variance($year, 0, null, array_values($planned), array_values($actual));
        return ['year' => $year, 'rows' => $annual['rows'], 'months' => $months, 'totals' => $annual['totals']];
    }

    public function variance(int $year, int $month, ?array $budget, array $planned, array $actual): array
    {
        $tolerance = Tolerance::fromEnv('BUDGET_TOLERANCE_PCT');
        $rows = []; $totals = ['plannedIncome' => 0, 'actualIncome' => 0, 'plannedExpense' => 0, 'actualExpense' => 0];
        foreach (['planned' => $planned, 'actual' => $actual] as $key => $set) {
            foreach ($set as $row) {
                $id = $row['categoryId']; $kind = $row['kind'];
                $rows[$id] ??= ['categoryId' => $id, 'name' => $row['name'], 'kind' => $kind, 'planned' => 0, 'actual' => 0];
                $rows[$id][$key] = (float)$row['amount'];
                $totals[$key.ucfirst($kind)] += (float)$row['amount'];
            }
        }
        foreach ($rows as &$row) {
            $row['variance'] = $row['actual'] - $row['planned'];
            $row['variancePct'] = $row['planned'] != 0 ? $row['variance'] / $row['planned'] : null;
            $directional = $row['kind'] === 'income' ? $row['variance'] : -$row['variance'];
            $row['status'] = abs($row['variance']) < 0.005 || ($row['planned'] != 0 && abs($directional / $row['planned']) <= $tolerance)
                ? 'on_budget' : ($directional > 0 ? 'favourable' : 'unfavourable');
        }
        unset($row);
        $rows = array_values($rows);
        usort($rows, static fn($a, $b) => ($a['kind'] === 'income') <=> ($b['kind'] === 'income') ?: strcasecmp($a['name'], $b['name']));
        $totals['plannedNet'] = $totals['plannedIncome'] - $totals['plannedExpense'];
        $totals['actualNet'] = $totals['actualIncome'] - $totals['actualExpense'];
        return ['year' => $year, 'month' => $month, 'budget' => $budget, 'rows' => $rows, 'totals' => $totals];
    }
}
