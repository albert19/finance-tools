<?php
namespace App\Tests;

use App\Command\DemoSeedCommand;
use Doctrine\DBAL\Connection;
use Doctrine\DBAL\DriverManager;
use PHPUnit\Framework\TestCase;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Tester\CommandTester;

final class DemoSeedCommandTest extends TestCase
{
    private array $originalEnv;
    private string $passwordFile;

    protected function setUp(): void
    {
        foreach (['APP_ENV', 'APP_DEMO_EMAIL', 'APP_DEMO_PASSWORD_FILE'] as $name) {
            $this->originalEnv[$name] = [getenv($name), $_SERVER[$name] ?? null, $_ENV[$name] ?? null];
            unset($_SERVER[$name], $_ENV[$name]);
            putenv($name);
        }
        $file = tempnam(sys_get_temp_dir(), 'demo-seed-');
        self::assertNotFalse($file);
        $this->passwordFile = $file;
        file_put_contents($file, 'local-test-password-only');
        chmod($file, 0600);
    }

    protected function tearDown(): void
    {
        foreach ($this->originalEnv as $name => [$value, $server, $env]) {
            if ($value === false) { putenv($name); } else { putenv("$name=$value"); }
            if ($server !== null) { $_SERVER[$name] = $server; }
            if ($env !== null) { $_ENV[$name] = $env; }
        }
        unlink($this->passwordFile);
    }

    private function configureEnv(): void
    {
        putenv('APP_ENV=test');
        putenv('APP_DEMO_EMAIL=demo@example.test');
        putenv('APP_DEMO_PASSWORD_FILE='.$this->passwordFile);
    }

    private function database(): Connection
    {
        $db = DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]);
        $db->executeStatement('PRAGMA foreign_keys = ON');
        foreach ([
            'CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, roles TEXT, locale TEXT, disabled INTEGER)',
            'CREATE TABLE categories (id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), kind TEXT, name TEXT, normalized_name TEXT, archived INTEGER, UNIQUE(user_id, kind, normalized_name))',
            'CREATE TABLE monthly_budgets (id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), year INTEGER, month INTEGER, notes TEXT, version INTEGER, UNIQUE(user_id, year, month))',
            'CREATE TABLE budget_lines (id TEXT PRIMARY KEY, budget_id TEXT REFERENCES monthly_budgets(id), category_id TEXT REFERENCES categories(id), amount TEXT, notes TEXT)',
            'CREATE TABLE transactions (id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), category_id TEXT REFERENCES categories(id), date TEXT, amount TEXT, description TEXT)',
            'CREATE TABLE investments (id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), name TEXT, start_date TEXT, status TEXT, notes TEXT, parameters TEXT)',
            'CREATE TABLE investment_snapshots (id TEXT PRIMARY KEY, investment_id TEXT REFERENCES investments(id), date TEXT, market_value TEXT, contribution TEXT, withdrawal TEXT, note TEXT)',
        ] as $sql) { $db->executeStatement($sql); }
        return $db;
    }

    public function testProductionAndMissingCredentialsFailBeforeAnyDatabaseAccess(): void
    {
        $tester = new CommandTester(new DemoSeedCommand(DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true])));
        $this->configureEnv();
        putenv('APP_ENV=prod');
        self::assertSame(Command::FAILURE, $tester->execute([]));
        self::assertStringContainsString('only with APP_ENV=dev or APP_ENV=test', $tester->getDisplay());
        putenv('APP_ENV=test');
        putenv('APP_DEMO_PASSWORD_FILE');
        self::assertSame(Command::FAILURE, $tester->execute([]));
        self::assertStringContainsString('APP_DEMO_PASSWORD_FILE', $tester->getDisplay());
    }

    public function testIdempotentSeedingPreservesExistingRecordsAndOtherOwners(): void
    {
        $this->configureEnv();
        $db = $this->database();
        $tester = new CommandTester(new DemoSeedCommand($db));
        $db->insert('users', ['id' => 'other', 'email' => 'other@example.test', 'password_hash' => 'other-hash',
            'roles' => '["ROLE_USER"]', 'locale' => 'en', 'disabled' => 0]);
        self::assertSame(Command::SUCCESS, $tester->execute([]));
        $user = $db->fetchAssociative('SELECT * FROM users WHERE email = ?', ['demo@example.test']);
        self::assertNotFalse($user);
        self::assertTrue(password_verify('local-test-password-only', $user['password_hash']));
        self::assertSame(PASSWORD_ARGON2ID, password_get_info($user['password_hash'])['algo']);
        self::assertSame(['ROLE_USER'], json_decode($user['roles'], true));
        self::assertSame(4, (int) $db->fetchOne('SELECT count(*) FROM categories WHERE user_id = ?', [$user['id']]));
        self::assertSame(2, (int) $db->fetchOne('SELECT count(*) FROM monthly_budgets WHERE user_id = ?', [$user['id']]));
        self::assertSame(10, (int) $db->fetchOne('SELECT count(*) FROM budget_lines'));
        self::assertSame(4, (int) $db->fetchOne("SELECT count(*) FROM budget_lines l JOIN categories c ON c.id = l.category_id WHERE c.name = 'Demo Food'"));
        self::assertSame(10, (int) $db->fetchOne('SELECT count(*) FROM transactions'));
        self::assertSame(1, (int) $db->fetchOne('SELECT count(*) FROM investments'));
        self::assertSame(3, (int) $db->fetchOne('SELECT count(*) FROM investment_snapshots'));

        $db->executeStatement("UPDATE users SET password_hash = 'changed' WHERE id = ?", [$user['id']]);
        $db->executeStatement("UPDATE transactions SET amount = '999.00' WHERE description = 'Demo dinner'");
        self::assertSame(Command::FAILURE, $tester->execute([]));
        self::assertStringContainsString('--allow-existing-user', $tester->getDisplay());
        self::assertSame(Command::SUCCESS, $tester->execute(['--allow-existing-user' => true]));
        self::assertSame(Command::SUCCESS, $tester->execute(['--allow-existing-user' => true]));
        self::assertSame('changed', $db->fetchOne('SELECT password_hash FROM users WHERE id = ?', [$user['id']]));
        self::assertSame('999.00', $db->fetchOne("SELECT amount FROM transactions WHERE description = 'Demo dinner' LIMIT 1"));
        foreach (['categories' => 4, 'monthly_budgets' => 2, 'budget_lines' => 10,
            'transactions' => 10, 'investments' => 1, 'investment_snapshots' => 3] as $table => $count) {
            self::assertSame($count, (int) $db->fetchOne("SELECT count(*) FROM $table"));
        }
        self::assertSame('other-hash', $db->fetchOne("SELECT password_hash FROM users WHERE id = 'other'"));
        $db->close();
    }

    public function testExistingPeriodAndInvestmentAreNotReusedOrModified(): void
    {
        $this->configureEnv();
        $db = $this->database();
        $db->insert('users', ['id' => 'demo-owner', 'email' => 'demo@example.test', 'password_hash' => 'original',
            'roles' => '["ROLE_ADMIN"]', 'locale' => 'es', 'disabled' => 0]);
        $db->insert('monthly_budgets', ['id' => 'personal-budget', 'user_id' => 'demo-owner',
            'year' => 2024, 'month' => 1, 'notes' => 'Personal', 'version' => 7]);
        $db->insert('investments', ['id' => 'personal-investment', 'user_id' => 'demo-owner',
            'name' => 'Demo Index Fund', 'start_date' => '2023-01-01', 'status' => 'closed',
            'notes' => 'Personal', 'parameters' => '{}']);
        $tester = new CommandTester(new DemoSeedCommand($db));
        self::assertSame(Command::SUCCESS, $tester->execute(['--allow-existing-user' => true]));
        self::assertSame('original', $db->fetchOne("SELECT password_hash FROM users WHERE id = 'demo-owner'"));
        self::assertSame('["ROLE_ADMIN"]', $db->fetchOne("SELECT roles FROM users WHERE id = 'demo-owner'"));
        self::assertSame('Personal', $db->fetchOne("SELECT notes FROM monthly_budgets WHERE id = 'personal-budget'"));
        self::assertSame(0, (int) $db->fetchOne("SELECT count(*) FROM budget_lines WHERE budget_id = 'personal-budget'"));
        self::assertSame(2, (int) $db->fetchOne('SELECT count(*) FROM monthly_budgets'));
        self::assertSame('closed', $db->fetchOne("SELECT status FROM investments WHERE id = 'personal-investment'"));
        self::assertSame(0, (int) $db->fetchOne('SELECT count(*) FROM investment_snapshots'));
        self::assertSame(5, (int) $db->fetchOne('SELECT count(*) FROM transactions'));
        $db->close();
    }
}
