<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

require_once __DIR__.'/ExistingTableGuard.php';

final class Version20261122000007 extends AbstractMigration
{
    public function getDescription(): string { return 'Owner-scoped investments'; }

    public function up(Schema $schema): void
    {
        $sql = "CREATE TABLE investments (id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL, name VARCHAR(150) NOT NULL, start_date DATE NOT NULL, status VARCHAR(10) NOT NULL DEFAULT 'active', notes TEXT NOT NULL, parameters JSON NOT NULL, INDEX idx_investment_user (user_id), CONSTRAINT fk_investment_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB";
        if (ExistingTableGuard::shouldCreate($this->connection, 'investments', $sql)) {
            $this->addSql($sql);
        }
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Investments migration is irreversible: retain existing data.');
    }
}
