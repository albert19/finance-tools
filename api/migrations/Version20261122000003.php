<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

require_once __DIR__.'/ExistingTableGuard.php';

final class Version20261122000003 extends AbstractMigration
{
    public function getDescription(): string { return 'Owner-scoped categories'; }

    public function up(Schema $schema): void
    {
        $sql = "CREATE TABLE categories (id CHAR(36) NOT NULL PRIMARY KEY, user_id CHAR(36) NOT NULL, kind VARCHAR(10) NOT NULL, name VARCHAR(100) NOT NULL, normalized_name VARCHAR(100) NOT NULL, archived TINYINT(1) NOT NULL DEFAULT 0, UNIQUE INDEX uniq_category (user_id, kind, normalized_name), CONSTRAINT fk_category_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB";
        if (ExistingTableGuard::shouldCreate($this->connection, 'categories', $sql)) {
            $this->addSql($sql);
        }
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Categories migration is irreversible: retain existing data.');
    }
}
