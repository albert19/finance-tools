<?php
namespace App\Tests;

use PHPUnit\Framework\TestCase;

final class MigrationLayoutTest extends TestCase
{
    public function testEveryVersionCreatesExactlyOneTableInDependencyOrder(): void
    {
        $tables = [
            'users', 'login_throttles', 'refresh_tokens', 'categories',
            'monthly_budgets', 'budget_lines', 'transactions',
            'investments', 'investment_snapshots',
        ];
        $expectedColumns = [
            ['id', 'email', 'password_hash', 'roles', 'locale', 'disabled'],
            ['id', 'attempts', 'window_started'],
            ['id', 'user_id', 'family_id', 'token_hash', 'expires_at', 'consumed_at', 'revoked_at'],
            ['id', 'user_id', 'kind', 'name', 'normalized_name', 'archived'],
            ['id', 'user_id', 'year', 'month', 'notes', 'version'],
            ['id', 'budget_id', 'category_id', 'amount', 'notes'],
            ['id', 'user_id', 'category_id', 'date', 'amount', 'description'],
            ['id', 'user_id', 'name', 'start_date', 'status', 'notes', 'parameters'],
            ['id', 'investment_id', 'date', 'market_value', 'contribution', 'withdrawal', 'note'],
        ];
        $expectedForeignKeys = [
            [], [], ['users'], ['users'], ['users'],
            ['monthly_budgets', 'categories'], ['users', 'categories'],
            ['users'], ['investments'],
        ];
        $expectedIndexes = [
            [], [], ['idx_refresh_family', 'idx_refresh_user'],
            ['uniq_category'], ['uniq_period'], ['idx_lines_budget'],
            ['idx_transactions_period'], ['idx_investment_user'], ['idx_snapshot_investment'],
        ];
        $expectedUnique = [
            ['email'], [], ['token_hash'], [], [], [], [], [], [],
        ];

        $versions = glob(__DIR__.'/../migrations/Version*.php');
        self::assertCount(count($tables), $versions);
        sort($versions);
        foreach ($versions as $index => $path) {
            self::assertSame(sprintf('Version202611220000%02d.php', $index), basename($path));
            $source = file_get_contents($path);
            self::assertSame(1, preg_match_all('/CREATE TABLE ([a-z_]+) \(/', $source, $creates), $path);
            self::assertSame($tables[$index], $creates[1][0], $path);
            self::assertStringNotContainsString('DROP TABLE', $source);
            self::assertMatchesRegularExpression('/function down\(Schema \$schema\).*?abortIf\(true,/s', $source);

            preg_match_all('/(?:\(|, )([a-z_]+) (?:CHAR|VARCHAR|TINYINT|SMALLINT|INT|DATETIME|DATE|TEXT|JSON|DECIMAL)\b/i', $source, $columns);
            self::assertSame($expectedColumns[$index], $columns[1], $path);
            preg_match_all('/REFERENCES ([a-z_]+)\(id\) ON DELETE (CASCADE|RESTRICT)/', $source, $references);
            self::assertSame($expectedForeignKeys[$index], $references[1], $path);
            preg_match_all('/(?:UNIQUE )?INDEX ([a-z_]+) \(/', $source, $indexes);
            self::assertSame($expectedIndexes[$index], $indexes[1], $path);
            preg_match_all('/([a-z_]+) (?:CHAR|VARCHAR)\([0-9]+\) NOT NULL UNIQUE/', $source, $uniques);
            self::assertSame($expectedUnique[$index], $uniques[1], $path);
            if ($index === 3 || $index === 4) {
                self::assertStringContainsString('UNIQUE INDEX', $source);
            }
            if ($index === 5 || $index === 6) {
                self::assertStringContainsString('ON DELETE RESTRICT', $source);
            }
            foreach ($references[1] as $parent) {
                self::assertContains($parent, array_slice($tables, 0, $index), $path);
            }
            if ($index >= 2) {
                self::assertStringContainsString('ExistingTableGuard::shouldCreate', $source);
            }
        }
    }
}
