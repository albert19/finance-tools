<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

require_once __DIR__.'/ExistingTableGuard.php';

final class Version20261122000008 extends AbstractMigration
{
    public function getDescription(): string { return 'Investment snapshots'; }

    public function up(Schema $schema): void
    {
        $sql = "CREATE TABLE investment_snapshots (id CHAR(36) NOT NULL PRIMARY KEY, investment_id CHAR(36) NOT NULL, date DATE NOT NULL, market_value DECIMAL(15,2) NOT NULL, contribution DECIMAL(15,2) NOT NULL DEFAULT 0, withdrawal DECIMAL(15,2) NOT NULL DEFAULT 0, note VARCHAR(255) NOT NULL DEFAULT '', INDEX idx_snapshot_investment (investment_id), CONSTRAINT fk_snapshot_investment FOREIGN KEY (investment_id) REFERENCES investments(id) ON DELETE CASCADE) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB";
        if (ExistingTableGuard::shouldCreate($this->connection, 'investment_snapshots', $sql)) {
            $this->addSql($sql);
        }
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Investment snapshots migration is irreversible: retain existing data.');
    }
}
