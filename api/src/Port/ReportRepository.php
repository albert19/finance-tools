<?php
namespace App\Port;

/** Owner-scoped raw monthly reporting data, before variance calculations. */
interface ReportRepository
{
    /** @return array{budget: ?array, planned: array, actual: array} */
    public function monthlyData(string $user, int $year, int $month): array;
}
