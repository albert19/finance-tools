<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Connection;
use RuntimeException;

/**
 * Old version 00000 created all finance tables. Later versions must adopt
 * those existing tables, but must not mark a drifted schema as migrated.
 */
final class ExistingTableGuard
{
    public static function shouldCreate(Connection $connection, string $table, string $sql): bool
    {
        $manager = $connection->createSchemaManager();
        if (!$manager->tablesExist([$table])) {
            return true;
        }

        $actual = $manager->introspectTable($table);
        // The SQL is the source of truth for both new and legacy installations.
        preg_match_all('/(?:\(|, )([a-z_]+) (?:CHAR|VARCHAR|TINYINT|SMALLINT|INT|DATETIME|DATE|TEXT|JSON|DECIMAL)\b/i', $sql, $columnMatches);
        $expectedColumns = $columnMatches[1];
        $actualColumns = array_map(static fn ($column): string => $column->getName(), $actual->getColumns());
        sort($expectedColumns);
        sort($actualColumns);
        self::assertSame($table, 'columns', $expectedColumns, $actualColumns);

        preg_match_all(
            "/(?:\(|, )([a-z_]+) ((?:CHAR|VARCHAR|TINYINT|SMALLINT|INT|DATETIME|DATE|TEXT|JSON|DECIMAL)(?:\([0-9,]+\))?) (NOT NULL|DEFAULT NULL)(?: (?:PRIMARY KEY|UNIQUE))?(?: DEFAULT ('[^']*'|[0-9]+))?/i",
            $sql,
            $definitions,
            PREG_SET_ORDER,
        );
        $expectedDefinitions = [];
        foreach ($definitions as $definition) {
            $default = isset($definition[4]) ? trim($definition[4], "'") : null;
            if ($default !== null && preg_match('/^DECIMAL\(\d+,(\d+)\)$/i', $definition[2], $scale)) {
                $default = number_format((float) $default, (int) $scale[1], '.', '');
            }
            $expectedDefinitions[$definition[1]] = [
                strtolower($definition[2]),
                $definition[3] === 'NOT NULL' ? 'NO' : 'YES',
                $default,
            ];
        }
        $actualDefinitions = [];
        foreach ($connection->fetchAllAssociative(
            'SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS
             WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?',
            [$table],
        ) as $column) {
            $actualDefinitions[$column['COLUMN_NAME']] = [
                strtolower($column['COLUMN_TYPE']), $column['IS_NULLABLE'], $column['COLUMN_DEFAULT'],
            ];
        }
        ksort($expectedDefinitions);
        ksort($actualDefinitions);
        self::assertSame($table, 'column definitions', $expectedDefinitions, $actualDefinitions);

        $expectedIndexes = ['primary' => ['columns' => ['id'], 'unique' => true]];
        if (preg_match('/\b([a-z_]+) [A-Z]+(?:\([0-9,]+\))? NOT NULL UNIQUE\b/i', $sql, $uniqueColumn)) {
            $expectedIndexes[$uniqueColumn[1]] = ['columns' => [$uniqueColumn[1]], 'unique' => true];
        }
        preg_match_all('/(UNIQUE )?INDEX ([a-z_]+) \(([a-z_, ]+)\)/i', $sql, $indexMatches, PREG_SET_ORDER);
        foreach ($indexMatches as $index) {
            $expectedIndexes[$index[2]] = ['columns' => explode(', ', $index[3]), 'unique' => $index[1] !== ''];
        }
        $actualIndexes = [];
        // DBAL synthesizes extra IDX_* entries for FK constraints; use actual
        // MySQL indexes rather than those virtual schema-manager entries.
        foreach ($connection->fetchAllAssociative(
            'SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?
             ORDER BY INDEX_NAME, SEQ_IN_INDEX',
            [$table],
        ) as $index) {
            $name = strtolower($index['INDEX_NAME']);
            $actualIndexes[$name]['columns'][] = $index['COLUMN_NAME'];
            $actualIndexes[$name]['unique'] = (int) $index['NON_UNIQUE'] === 0;
        }
        ksort($actualIndexes);

        preg_match_all('/CONSTRAINT ([a-z_]+) FOREIGN KEY \(([a-z_]+)\) REFERENCES ([a-z_]+)\(([a-z_]+)\) ON DELETE (CASCADE|RESTRICT)/i', $sql, $foreignMatches, PREG_SET_ORDER);
        $expectedForeign = [];
        foreach ($foreignMatches as $match) {
            $expectedForeign[$match[1]] = [$match[2], $match[3], $match[4], $match[5]];
            // MySQL automatically adds a supporting index if no explicit index
            // has the FK's local column as its leftmost column.
            if (!array_filter($expectedIndexes, static fn (array $index): bool => $index['columns'][0] === $match[2])) {
                $expectedIndexes[$match[1]] = ['columns' => [$match[2]], 'unique' => false];
            }
        }
        ksort($expectedIndexes);
        self::assertSame($table, 'indexes', $expectedIndexes, $actualIndexes);
        $actualForeign = [];
        foreach ($actual->getForeignKeys() as $foreign) {
            // MySQL reports explicitly declared RESTRICT as NO ACTION.
            $onDelete = $foreign->getOnDeleteAction()->value;
            $actualForeign[$foreign->getName()] = [
                $foreign->getLocalColumns()[0], $foreign->getForeignTableName(),
                $foreign->getForeignColumns()[0], $onDelete === 'NO ACTION' ? 'RESTRICT' : $onDelete,
            ];
        }
        ksort($expectedForeign);
        ksort($actualForeign);
        self::assertSame($table, 'foreign keys', $expectedForeign, $actualForeign);
        return false;
    }

    private static function assertSame(string $table, string $part, array $expected, array $actual): void
    {
        if ($expected !== $actual) {
            throw new RuntimeException("Existing $table has unexpected $part; refusing to adopt it");
        }
    }
}
