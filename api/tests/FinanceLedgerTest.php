<?php
namespace App\Tests;

use App\Service\FinanceLedger;
use App\Repository\FinanceStore;
use App\Service\Problem;
use App\Repository\DbalLedgerRepository;
use Doctrine\DBAL\DriverManager;
use PHPUnit\Framework\TestCase;

final class FinanceLedgerTest extends TestCase
{
    public function testOwnerScopedCategoryAndTransactionMutations(): void
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('CREATE TABLE categories (id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, name TEXT, normalized_name TEXT, archived INTEGER DEFAULT 0)');
        $db->executeStatement('CREATE TABLE transactions (id TEXT PRIMARY KEY, user_id TEXT, category_id TEXT, date TEXT, amount TEXT, description TEXT)');
        $db->executeStatement('CREATE TABLE budget_lines (id TEXT, category_id TEXT)');
        $ledger = new FinanceLedger(new DbalLedgerRepository(new FinanceStore($db)));
        $category = $ledger->createCategory('alice', ['kind' => 'expense', 'name' => 'Food']);
        self::assertCount(0, $ledger->categories('bob', true));
        try { $ledger->updateCategory('bob', $category['id'], ['archived' => true]); self::fail('Foreign category update'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        try { $ledger->deleteCategory('bob', $category['id']); self::fail('Foreign category delete'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        try { $ledger->saveTransaction('bob', ['categoryId' => $category['id'], 'date' => '2024-01-01', 'amount' => '5'], null); self::fail('Foreign category'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        $transaction = $ledger->saveTransaction('alice', ['categoryId' => $category['id'], 'date' => '2024-01-01', 'amount' => '5'], null);
        try { $ledger->saveTransaction('bob', ['categoryId' => $category['id'], 'date' => '2024-01-01', 'amount' => '10'], $transaction['id']); self::fail('Foreign transaction'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        try { $ledger->deleteTransaction('bob', $transaction['id']); self::fail('Foreign transaction delete'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        self::assertCount(1, $ledger->transactions('alice', 2024, 1, null));
        self::assertSame([], $ledger->transactions('bob', 2024, 1, null));
        try { $ledger->deleteCategory('alice', $category['id']); self::fail('In-use category deleted'); }
        catch (Problem $e) { self::assertSame(409, $e->status); }
        $ledger->deleteTransaction('alice', $transaction['id']);
        $ledger->updateCategory('alice', $category['id'], ['archived' => true]);
        self::assertSame([], $ledger->categories('alice', false));
        $ledger->deleteCategory('alice', $category['id']);
    }

    public function testDefaultsRespectArchivedNamesAndOwnerAndTransactionFilters(): void
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('CREATE TABLE categories (id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, name TEXT, normalized_name TEXT, archived INTEGER DEFAULT 0, UNIQUE(user_id, kind, normalized_name))');
        $db->executeStatement('CREATE TABLE transactions (id TEXT PRIMARY KEY, user_id TEXT, category_id TEXT, date TEXT, amount TEXT, description TEXT)');
        $db->executeStatement('CREATE TABLE budget_lines (id TEXT, category_id TEXT)');
        $ledger = new FinanceLedger(new DbalLedgerRepository(new FinanceStore($db)));
        $archived = $ledger->createCategory('alice', ['kind' => 'expense', 'name' => 'Food']);
        $ledger->updateCategory('alice', $archived['id'], ['archived' => true]);
        self::assertCount(7, $ledger->defaults('alice')['created']);
        self::assertSame([], $ledger->defaults('alice')['created']);
        self::assertCount(8, $ledger->defaults('bob')['created']);
        self::assertCount(7, $ledger->categories('alice', false));
        self::assertCount(8, $ledger->categories('alice', true));
        self::assertSame(1, (int)$ledger->categories('alice', true)[0]['archived']);

        try {
            $ledger->saveTransaction('alice', ['categoryId' => $archived['id'], 'date' => '2024-01-01', 'amount' => '5'], null);
            self::fail('Archived category accepted');
        } catch (Problem $e) {
            self::assertSame(422, $e->status);
            self::assertSame('categoryId', $e->errors[0]['field']);
        }
        $income = $ledger->createCategory('alice', ['kind' => 'income', 'name' => 'Consulting']);
        $expense = $ledger->createCategory('alice', ['kind' => 'expense', 'name' => 'Books']);
        $ledger->saveTransaction('alice', ['categoryId' => $income['id'], 'date' => '2024-01-31', 'amount' => '10'], null);
        $ledger->saveTransaction('alice', ['categoryId' => $expense['id'], 'date' => '2024-02-01', 'amount' => '5'], null);
        $ledger->saveTransaction('bob', ['categoryId' => $ledger->categories('bob', false)[0]['id'], 'date' => '2024-01-31', 'amount' => '5'], null);
        self::assertCount(1, $ledger->transactions('alice', 2024, 1, 'income'));
        self::assertSame([], $ledger->transactions('alice', 2024, 1, 'expense'));
        self::assertCount(1, $ledger->transactions('alice', 2024, 2, null));
        self::assertCount(1, $ledger->transactions('bob', 2024, 1, null));
    }

    public function testBudgetLinePreventsDeletingCategory(): void
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('CREATE TABLE categories (id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, name TEXT, normalized_name TEXT, archived INTEGER DEFAULT 0)');
        $db->executeStatement('CREATE TABLE budget_lines (id TEXT, category_id TEXT)');
        $db->executeStatement('CREATE TABLE transactions (id TEXT, user_id TEXT, category_id TEXT)');
        $ledger = new FinanceLedger(new DbalLedgerRepository(new FinanceStore($db)));
        $category = $ledger->createCategory('alice', ['kind' => 'expense', 'name' => 'Food']);
        $db->insert('budget_lines', ['id' => 'line', 'category_id' => $category['id']]);
        try {
            $ledger->deleteCategory('alice', $category['id']);
            self::fail('Category with budget line deleted');
        } catch (Problem $e) {
            self::assertSame(409, $e->status);
            self::assertSame('category_in_use', $e->problemCode);
        }
    }
}
