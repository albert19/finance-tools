<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

require_once __DIR__.'/ExistingTableGuard.php';

final class Version20261122000006 extends AbstractMigration
{
    public function getDescription(): string { return 'Owner-scoped transactions'; }

    public function up(Schema $schema): void
    {
        $sql = "CREATE TABLE transactions (id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL, category_id CHAR(36) NOT NULL, date DATE NOT NULL, amount DECIMAL(15,2) NOT NULL, description VARCHAR(255) NOT NULL DEFAULT '', INDEX idx_transactions_period (user_id, date), CONSTRAINT fk_transaction_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, CONSTRAINT fk_transaction_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB";
        if (ExistingTableGuard::shouldCreate($this->connection, 'transactions', $sql)) {
            $this->addSql($sql);
        }
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Transactions migration is irreversible: retain existing data.');
    }
}
