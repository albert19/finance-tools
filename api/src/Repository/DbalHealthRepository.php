<?php
namespace App\Repository;

use App\Port\HealthRepository;
use Doctrine\DBAL\Connection;

final class DbalHealthRepository implements HealthRepository
{
    public function __construct(private Connection $db) {}

    public function ping(): bool
    {
        try {
            $this->db->executeQuery('SELECT 1');
            return true;
        } catch (\Throwable) {
            return false;
        }
    }
}
