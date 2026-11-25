<?php
namespace App\Command;

use App\Service\PasswordHasher;
use Doctrine\DBAL\Connection;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Uid\Uuid;

#[AsCommand(name: 'app:seed:demo', description: 'Add sample finance data to a development/test demo account')]
final class DemoSeedCommand extends Command
{
    public function __construct(private Connection $db, private PasswordHasher $hasher = new PasswordHasher()) { parent::__construct(); }

    protected function configure(): void
    {
        $this->addOption('allow-existing-user', null, InputOption::VALUE_NONE,
            'Explicitly allow adding missing demo records to an existing account (never updates existing records)');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        // Refuse before even connecting to the database or reading the credential file.
        $environments = array_filter([getenv('APP_ENV') ?: null, $_SERVER['APP_ENV'] ?? null, $_ENV['APP_ENV'] ?? null]);
        if (!$environments || array_diff($environments, ['dev', 'test'])) {
            $output->writeln('<error>Demo seeding is permitted only with APP_ENV=dev or APP_ENV=test; no data changed.</error>');
            return Command::FAILURE;
        }
        $email = strtolower(trim(getenv('APP_DEMO_EMAIL') ?: ''));
        $file = getenv('APP_DEMO_PASSWORD_FILE') ?: '';
        if (!filter_var($email, FILTER_VALIDATE_EMAIL) || !$file || !is_file($file) || !is_readable($file)) {
            $output->writeln('<error>Set APP_DEMO_EMAIL to a valid email and APP_DEMO_PASSWORD_FILE to a readable, private password file; no data changed.</error>');
            return Command::FAILURE;
        }
        $password = @file_get_contents($file);
        $password = $password === false ? '' : rtrim($password, "\r\n");
        if (PasswordHasher::policyError($password)) {
            $output->writeln('<error>APP_DEMO_PASSWORD_FILE must contain a single password of 12 to 1024 characters without spaces; no data changed.</error>');
            return Command::FAILURE;
        }

        // All inserts are atomic. Existing rows are never updated, replaced or deleted.
        $this->db->beginTransaction();
        try {
            $user = $this->db->fetchOne('SELECT id FROM users WHERE email = ?', [$email]);
            if ($user && !$input->getOption('allow-existing-user')) {
                $output->writeln('<error>Account already exists. To add only missing demo data to this account, rerun with --allow-existing-user; no data changed.</error>');
                $this->db->rollBack();
                return Command::FAILURE;
            }
            if (!$user) {
                $user = Uuid::v7()->toRfc4122();
                $this->db->insert('users', ['id' => $user, 'email' => $email,
                    'password_hash' => $this->hasher->hash($password),
                    'roles' => json_encode(['ROLE_USER'], JSON_THROW_ON_ERROR), 'locale' => 'en', 'disabled' => 0]);
            }
            $this->seed($user);
            $this->db->commit();
            $output->writeln('Demo data ready (existing records were left unchanged).');
            return Command::SUCCESS;
        } catch (\Throwable $e) {
            $this->db->rollBack();
            throw $e;
        }
    }

    private static function id(string $user, string $key): string
    {
        return Uuid::v5(Uuid::fromString('b1321d42-5832-4578-a3ed-c319cf3bec6b'), "$user/$key")->toRfc4122();
    }

    private function seed(string $user): void
    {
        $categories = [];
        foreach (['income' => ['Demo Salary'], 'expense' => ['Demo Housing', 'Demo Food', 'Demo Transport']] as $kind => $names) {
            foreach ($names as $name) {
                $normalized = strtolower($name);
                $existing = $this->db->fetchOne(
                    'SELECT id FROM categories WHERE user_id = ? AND kind = ? AND normalized_name = ?',
                    [$user, $kind, $normalized],
                );
                $id = $existing ?: self::id($user, "category/$kind/$normalized");
                if (!$existing) {
                    $this->db->insert('categories', ['id' => $id, 'user_id' => $user,
                        'kind' => $kind, 'name' => $name, 'normalized_name' => $normalized, 'archived' => 0]);
                }
                $categories[$name] = $id;
            }
        }

        foreach ([1, 2] as $month) {
            $budget = self::id($user, "budget/2024/$month");
            $existing = $this->db->fetchOne(
                'SELECT id FROM monthly_budgets WHERE user_id = ? AND year = ? AND month = ?',
                [$user, 2024, $month],
            );
            if ($existing && $existing !== $budget) {
                // Never add lines to a budget that was not created by this fixture.
                continue;
            }
            if (!$existing) {
                $this->db->insert('monthly_budgets', ['id' => $budget, 'user_id' => $user,
                    'year' => 2024, 'month' => $month, 'notes' => 'Demo monthly plan', 'version' => 1]);
            }
            foreach ([
                ['Demo Salary', '3200.00', 'Main salary'],
                ['Demo Housing', '950.00', 'Rent'],
                ['Demo Food', '240.00', 'Groceries'],
                ['Demo Food', '85.00', 'Dining out'],
                ['Demo Transport', '60.00', 'Transit'],
            ] as $line) {
                [$category, $amount, $notes] = $line;
                $id = self::id($user, "line/2024/$month/$notes");
                $this->insertMissing('budget_lines', $id, 'budget_id', $budget, [
                    'budget_id' => $budget, 'category_id' => $categories[$category],
                    'amount' => $amount, 'notes' => $notes,
                ]);
            }
            foreach ([
                ['Demo Salary', '05', '3200.00', 'Demo paycheck'],
                ['Demo Housing', '06', '950.00', 'Demo rent'],
                ['Demo Food', '10', '72.50', 'Demo groceries'],
                ['Demo Food', '20', '36.00', 'Demo dinner'],
                ['Demo Transport', '14', '24.00', 'Demo transit'],
            ] as $transaction) {
                [$category, $day, $amount, $description] = $transaction;
                $date = sprintf('2024-%02d-%s', $month, $day);
                $this->insertMissing('transactions', self::id($user, "transaction/$date/$description"),
                    'user_id', $user, ['user_id' => $user, 'category_id' => $categories[$category],
                        'date' => $date, 'amount' => $amount, 'description' => $description]);
            }
        }

        $investment = self::id($user, 'investment/index-fund');
        $existing = $this->db->fetchAssociative('SELECT id, start_date FROM investments WHERE user_id = ? AND name = ?',
            [$user, 'Demo Index Fund']);
        if ($existing && ($existing['id'] !== $investment || $existing['start_date'] !== '2024-01-01')) {
            return; // Do not attach snapshots to a pre-existing investment.
        }
        if (!$existing) {
            $this->db->insert('investments', ['id' => $investment, 'user_id' => $user,
                'name' => 'Demo Index Fund', 'start_date' => '2024-01-01', 'status' => 'active',
                'notes' => 'Example long-term investment',
                'parameters' => json_encode(['initialCapital' => 1000, 'contribution' => 100,
                    'annualRate' => 5, 'horizonMonths' => 120], JSON_THROW_ON_ERROR)]);
        }
        foreach (['2024-02-01' => '1110.00', '2024-03-01' => '1232.00', '2024-04-01' => '1350.00'] as $date => $value) {
            // Snapshot dates are unique per investment at the application layer, not in the schema.
            if ($this->db->fetchOne('SELECT id FROM investment_snapshots WHERE investment_id = ? AND date = ?',
                [$investment, $date])) {
                continue;
            }
            $this->insertMissing('investment_snapshots', self::id($user, "snapshot/$date"),
                'investment_id', $investment, ['investment_id' => $investment, 'date' => $date,
                    'market_value' => $value, 'contribution' => '100.00', 'withdrawal' => '0.00',
                    'note' => 'Demo monthly valuation']);
        }
    }

    private function insertMissing(string $table, string $id, string $parentColumn, string $parent, array $values): void
    {
        $existing = $this->db->fetchOne("SELECT $parentColumn FROM $table WHERE id = ?", [$id]);
        if ($existing !== false) {
            if ($existing !== $parent) {
                throw new \RuntimeException('Demo fixture ID belongs to another owner or parent; refusing to seed.');
            }
            return;
        }
        $this->db->insert($table, ['id' => $id, ...$values]);
    }
}
