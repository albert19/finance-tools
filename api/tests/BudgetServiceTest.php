<?php
namespace App\Tests;

use App\Service\BudgetService;
use App\Repository\FinanceStore;
use App\Service\Problem;
use App\Port\BudgetRepository;
use App\Repository\DbalBudgetRepository;
use Doctrine\DBAL\DriverManager;
use PHPUnit\Framework\TestCase;

final class BudgetServiceTest extends TestCase
{
    public function testCopyLineVersionAndOwnership(): void
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('CREATE TABLE categories (id TEXT PRIMARY KEY, user_id TEXT, name TEXT, kind TEXT, archived INTEGER)');
        $db->executeStatement('CREATE TABLE monthly_budgets (id TEXT PRIMARY KEY, user_id TEXT, year INTEGER, month INTEGER, notes TEXT, version INTEGER DEFAULT 1)');
        $db->executeStatement('CREATE TABLE budget_lines (id TEXT PRIMARY KEY, budget_id TEXT, category_id TEXT, amount TEXT, notes TEXT)');
        $db->executeStatement("INSERT INTO categories VALUES ('food', 'alice', 'Food', 'expense', 0)");
        $budgets = new BudgetService(new DbalBudgetRepository(new FinanceStore($db)));
        $source = $budgets->create('alice', ['year' => 2024, 'month' => 1]);
        $budgets->saveLine('alice', $source['id'], null, ['categoryId' => 'food', 'amount' => '25', 'version' => 1]);
        self::assertSame(2, (int)$budgets->period('alice', 2024, 1)['version']);
        try { $budgets->update('bob', $source['id'], ['version' => 2]); self::fail('Foreign budget update'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        try { $budgets->update('alice', $source['id'], ['version' => 1]); self::fail('Stale update'); }
        catch (Problem $e) { self::assertSame(409, $e->status); }
        $copy = $budgets->create('alice', ['year' => 2024, 'month' => 2, 'copyFrom' => ['year' => 2024, 'month' => 1]]);
        self::assertCount(1, $copy['lines']);
        self::assertSame('food', $copy['lines'][0]['categoryId']);
        try { $budgets->create('bob', ['year' => 2024, 'month' => 2, 'copyFrom' => ['year' => 2024, 'month' => 1]]); self::fail('Foreign copy'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        self::assertCount(0, $budgets->list('bob', null));
    }

    public function testServiceValidatesAndDelegatesNormalizedCommandsToPort(): void
    {
        $repo = $this->createMock(BudgetRepository::class);
        $repo->expects(self::once())->method('create')
            ->with('alice', 2024, 2, 'plan', [2024, 1])
            ->willReturn(['id' => 'created']);
        $repo->expects(self::once())->method('saveLine')
            ->with('alice', 'created', null, 'food', '25.00', '', 1)
            ->willReturn(['id' => 'created', 'version' => 2]);
        $service = new BudgetService($repo);
        self::assertSame(['id' => 'created'], $service->create('alice', [
            'year' => '2024', 'month' => '2', 'notes' => ' plan ',
            'copyFrom' => ['year' => 2024, 'month' => 1],
        ]));
        self::assertSame(2, $service->saveLine('alice', 'created', null, [
            'categoryId' => ' food ', 'amount' => '25', 'version' => '1',
        ])['version']);
        try {
            $service->update('alice', 'created', ['version' => 0]);
            self::fail('Invalid version must not reach repository');
        } catch (Problem $e) {
            self::assertSame(422, $e->status);
        }
        try {
            $service->create('alice', ['year' => 2024, 'month' => 3, 'copyFrom' => 'wrong']);
            self::fail('Invalid copyFrom must not reach repository');
        } catch (Problem $e) {
            self::assertSame(422, $e->status);
        }
    }

    public function testFailedLineMutationRollsBackVersionAndRetainsOwnership(): void
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('CREATE TABLE categories (id TEXT PRIMARY KEY, user_id TEXT, name TEXT, kind TEXT, archived INTEGER)');
        $db->executeStatement('CREATE TABLE monthly_budgets (id TEXT PRIMARY KEY, user_id TEXT, year INTEGER, month INTEGER, notes TEXT, version INTEGER DEFAULT 1)');
        $db->executeStatement('CREATE TABLE budget_lines (id TEXT PRIMARY KEY, budget_id TEXT, category_id TEXT, amount TEXT, notes TEXT)');
        $db->executeStatement("INSERT INTO categories VALUES ('food', 'alice', 'Food', 'expense', 0)");
        $budgets = new BudgetService(new DbalBudgetRepository(new FinanceStore($db)));
        $budget = $budgets->create('alice', ['year' => 2024, 'month' => 1]);
        $id = $budget['id'];
        try {
            $budgets->saveLine('alice', $id, 'missing', ['categoryId' => 'food', 'amount' => 25, 'version' => 1]);
            self::fail('Unknown line must not increment budget version');
        } catch (Problem $e) {
            self::assertSame(404, $e->status);
        }
        self::assertSame(1, (int)$budgets->period('alice', 2024, 1)['version']);
        try {
            $budgets->saveLine('bob', $id, null, ['categoryId' => 'food', 'amount' => 25, 'version' => 1]);
            self::fail('Foreign line write must not succeed');
        } catch (Problem $e) {
            self::assertSame(404, $e->status);
        }
        self::assertSame(1, (int)$budgets->period('alice', 2024, 1)['version']);
        self::assertSame([], $budgets->period('alice', 2024, 1)['lines']);
    }
}
