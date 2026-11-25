<?php
namespace App\Tests;

use App\Repository\FinanceStore;
use App\Service\Problem;
use Doctrine\DBAL\DriverManager;
use PHPUnit\Framework\TestCase;

final class FinanceStoreTest extends TestCase
{
    private function store(): FinanceStore
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('CREATE TABLE categories (id TEXT, user_id TEXT, archived INTEGER, name TEXT)');
        $db->executeStatement('CREATE TABLE monthly_budgets (id TEXT, user_id TEXT, version INTEGER)');
        $db->executeStatement("INSERT INTO categories VALUES ('active', 'alice', 0, 'Food'), ('archived', 'alice', 1, 'Old')");
        $db->executeStatement("INSERT INTO monthly_budgets VALUES ('budget', 'alice', 1)");
        return new FinanceStore($db);
    }

    public function testArchivedCategoryIsRejectedForNewRecordsButCanBeReadHistorically(): void
    {
        $store = $this->store();
        self::assertSame('archived', $store->owned('categories', 'archived', 'alice')['id']);
        try {
            $store->category('archived', 'alice');
            self::fail('Archived category accepted');
        } catch (Problem $e) { self::assertSame(422, $e->status); }
        try {
            $store->category('active', 'bob');
            self::fail('Category from other user accepted');
        } catch (Problem $e) { self::assertSame(404, $e->status); }
    }

    public function testVersionUpdateIsAtomicAndOwnerScoped(): void
    {
        $store = $this->store();
        $store->changed('budget', 'alice', 1);
        self::assertSame(2, (int)$store->owned('monthly_budgets', 'budget', 'alice')['version']);
        foreach ([['alice', 1], ['bob', 2]] as [$owner, $version]) {
            try {
                $store->changed('budget', $owner, $version);
                self::fail('Stale or foreign version accepted');
            } catch (Problem $e) { self::assertSame(409, $e->status); }
        }
        self::assertSame(2, (int)$store->owned('monthly_budgets', 'budget', 'alice')['version']);
    }
}
