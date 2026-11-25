<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261122000000 extends AbstractMigration
{
    public function getDescription(): string { return 'Users'; }

    public function up(Schema $schema): void
    {
        $this->addSql("CREATE TABLE users (id CHAR(36) NOT NULL PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, roles JSON NOT NULL, locale VARCHAR(5) NOT NULL DEFAULT 'en', disabled TINYINT(1) NOT NULL DEFAULT 0) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB");
    }

    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Users migration is irreversible: retain existing data.');
    }
}
