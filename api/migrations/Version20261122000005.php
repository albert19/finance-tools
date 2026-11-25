<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

require_once __DIR__.'/ExistingTableGuard.php';

final class Version20261122000005 extends AbstractMigration
{
    public function getDescription(): string { return 'Budget lines'; }

    public function up(Schema $schema): void
    {
        $sql = "CREATE TABLE budget_lines (id CHAR(36) NOT NULL PRIMARY KEY, budget_id CHAR(36) NOT NULL, category_id CHAR(36) NOT NULL, amount DECIMAL(15,2) NOT NULL, notes VARCHAR(255) NOT NULL DEFAULT '', INDEX idx_lines_budget (budget_id), CONSTRAINT fk_line_budget FOREIGN KEY (budget_id) REFERENCES monthly_budgets(id) ON DELETE CASCADE, CONSTRAINT fk_line_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB";
        if (ExistingTableGuard::shouldCreate($this->connection, 'budget_lines', $sql)) {
            $this->addSql($sql);
        }
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Budget lines migration is irreversible: retain existing data.');
    }
}
