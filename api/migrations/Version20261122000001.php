<?php
namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20261122000001 extends AbstractMigration
{
    public function getDescription(): string { return 'Shared MySQL-backed login throttle'; }
    public function up(Schema $schema): void
    {
        $this->addSql('CREATE TABLE login_throttles (id CHAR(64) NOT NULL PRIMARY KEY, attempts INT NOT NULL, window_started DATETIME NOT NULL) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE = InnoDB');
    }
    public function down(Schema $schema): void
    {
        $this->abortIf(true, 'Login throttles migration is irreversible: retain existing data.');
    }
}
