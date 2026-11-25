<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

require_once __DIR__.'/ExistingTableGuard.php';

final class Version20261122000004 extends AbstractMigration
{
    public function getDescription(): string { return 'Monthly budgets'; }

    public function up(Schema $schema): void
    {
        $sql = "CREATE TABLE monthly_budgets (id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL, year SMALLINT NOT NULL, month TINYINT NOT NULL, notes TEXT NOT NULL, version INT NOT NULL DEFAULT 1, UNIQUE INDEX uniq_period (user_id, year, month), CONSTRAINT fk_budget_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB";
        if (ExistingTableGuard::shouldCreate($this->connection, 'monthly_budgets', $sql)) {
            $this->addSql($sql);
        }
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Monthly budgets migration is irreversible: retain existing data.');
    }
}
