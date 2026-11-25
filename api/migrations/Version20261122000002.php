<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

require_once __DIR__.'/ExistingTableGuard.php';

final class Version20261122000002 extends AbstractMigration
{
    public function getDescription(): string { return 'Rotating refresh tokens'; }

    public function up(Schema $schema): void
    {
        $sql = "CREATE TABLE refresh_tokens (id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL, family_id CHAR(36) NOT NULL, token_hash CHAR(64) NOT NULL UNIQUE, expires_at DATETIME NOT NULL, consumed_at DATETIME DEFAULT NULL, revoked_at DATETIME DEFAULT NULL, INDEX idx_refresh_family (family_id), INDEX idx_refresh_user (user_id), CONSTRAINT fk_refresh_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB";
        if (ExistingTableGuard::shouldCreate($this->connection, 'refresh_tokens', $sql)) {
            $this->addSql($sql);
        }
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Refresh tokens migration is irreversible: retain existing data.');
    }
}
