<?php
namespace App\Port;

interface HealthRepository
{
    public function ping(): bool;
}
