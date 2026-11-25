<?php
namespace App\Tests;

use App\Port\ReportRepository;
use App\Repository\DbalReportRepository;
use App\Service\FinanceReports;
use App\Repository\FinanceStore;
use Doctrine\DBAL\DriverManager;
use PHPUnit\Framework\TestCase;

final class VarianceTest extends TestCase
{
    public function testExpenseAndIncomeVarianceUseActualMinusPlannedAndRelativeTolerance(): void
    {
        $controller = (new \ReflectionClass(FinanceReports::class))->newInstanceWithoutConstructor();
        $method = new \ReflectionMethod(FinanceReports::class, 'variance');
        $planned = [
            ['categoryId' => 'e', 'name' => 'Food', 'kind' => 'expense', 'amount' => 100],
            ['categoryId' => 'i', 'name' => 'Salary', 'kind' => 'income', 'amount' => 100],
        ];
        $actual = [
            ['categoryId' => 'e', 'name' => 'Food', 'kind' => 'expense', 'amount' => 110],
            ['categoryId' => 'i', 'name' => 'Salary', 'kind' => 'income', 'amount' => 101],
            ['categoryId' => 'extra', 'name' => 'Bonus', 'kind' => 'income', 'amount' => 10],
        ];
        $report = $method->invoke($controller, 2026, 1, null, $planned, $actual);
        $rows = array_column($report['rows'], null, 'categoryId');
        self::assertSame(10.0, $rows['e']['variance']);
        self::assertSame('unfavourable', $rows['e']['status']);
        self::assertSame(1.0, $rows['i']['variance']);
        self::assertSame('on_budget', $rows['i']['status']);
        self::assertSame('favourable', $rows['extra']['status']);
        self::assertNull($rows['extra']['variancePct']);
        self::assertSame(111.0, $report['totals']['actualIncome']);
    }

    public function testMonthlyDelegatesValidatedPeriodAndOwnerToReadPort(): void
    {
        $repo = $this->createMock(ReportRepository::class);
        $repo->expects(self::once())->method('monthlyData')
            ->with('alice', 2026, 2)
            ->willReturn([
                'budget' => ['id' => 'b'],
                'planned' => [['categoryId' => 'food', 'name' => 'Food', 'kind' => 'expense', 'amount' => '50']],
                'actual' => [['categoryId' => 'food', 'name' => 'Food', 'kind' => 'expense', 'amount' => '55']],
            ]);
        $report = (new FinanceReports($repo))->monthly('alice', 2026, 2);
        self::assertSame('b', $report['budget']['id']);
        self::assertSame(5.0, $report['rows'][0]['variance']);
        self::assertSame('unfavourable', $report['rows'][0]['status']);
    }

    public function testDbalReportScopesBudgetAndActualsToOwner(): void
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('CREATE TABLE categories (id TEXT PRIMARY KEY, user_id TEXT, name TEXT, kind TEXT, archived INTEGER)');
        $db->executeStatement('CREATE TABLE monthly_budgets (id TEXT PRIMARY KEY, user_id TEXT, year INTEGER, month INTEGER, notes TEXT, version INTEGER DEFAULT 1)');
        $db->executeStatement('CREATE TABLE budget_lines (id TEXT PRIMARY KEY, budget_id TEXT, category_id TEXT, amount TEXT, notes TEXT)');
        $db->executeStatement('CREATE TABLE transactions (id TEXT PRIMARY KEY, user_id TEXT, category_id TEXT, date TEXT, amount TEXT)');
        $db->executeStatement("INSERT INTO categories VALUES ('a', 'alice', 'Food', 'expense', 0), ('b', 'bob', 'Travel', 'expense', 0)");
        $db->executeStatement("INSERT INTO monthly_budgets (id, user_id, year, month, notes) VALUES ('ba', 'alice', 2026, 1, ''), ('bb', 'bob', 2026, 1, '')");
        $db->executeStatement("INSERT INTO budget_lines VALUES ('la', 'ba', 'a', '10', ''), ('lb', 'bb', 'b', '100', '')");
        $db->executeStatement("INSERT INTO transactions VALUES ('ta', 'alice', 'a', '2026-01-15', '12'), ('tb', 'bob', 'b', '2026-01-15', '120')");
        $report = (new FinanceReports(new DbalReportRepository(new FinanceStore($db))))->monthly('alice', 2026, 1);
        self::assertSame('ba', $report['budget']['id']);
        self::assertCount(1, $report['rows']);
        self::assertSame('a', $report['rows'][0]['categoryId']);
        self::assertSame(10.0, $report['rows'][0]['planned']);
        self::assertSame(12.0, $report['rows'][0]['actual']);
    }
}
