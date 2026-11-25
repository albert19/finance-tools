<?php
namespace App\Service;

use App\Port\BudgetRepository;

/** Validate budget commands and delegate owner-scoped persistence to the repository. */
final class BudgetService
{
    public function __construct(private BudgetRepository $budgets) {}

    public function list(string $user, mixed $year): array
    {
        if ($year !== null) { [$year] = Inputs::period($year, 1); }
        return $this->budgets->list($user, $year);
    }

    public function period(string $user, int $year, int $month): array
    {
        Inputs::period($year, $month);
        return $this->budgets->period($user, $year, $month);
    }

    public function create(string $user, array $data): array
    {
        [$year, $month] = Inputs::period($data['year'] ?? null, $data['month'] ?? null);
        $notes = Inputs::text($data, 'notes', 2000, false);
        $copyFrom = null;
        if (isset($data['copyFrom'])) {
            if (!is_array($data['copyFrom'])) { throw Problem::invalid('copyFrom', 'Expected {year, month}'); }
            $copyFrom = Inputs::period($data['copyFrom']['year'] ?? null, $data['copyFrom']['month'] ?? null);
        }
        return $this->budgets->create($user, $year, $month, $notes, $copyFrom);
    }

    public function update(string $user, string $id, array $data): array
    {
        $version = self::version($data);
        $notes = array_key_exists('notes', $data) ? Inputs::text($data, 'notes', 2000, false) : null;
        return $this->budgets->update($user, $id, $version, $notes);
    }

    public function delete(string $user, string $id): void
    {
        $this->budgets->delete($user, $id);
    }

    public function saveLine(string $user, string $id, ?string $lineId, array $data): array
    {
        $categoryId = Inputs::text($data, 'categoryId', 36);
        $amount = Inputs::money($data, 'amount');
        $notes = Inputs::text($data, 'notes', 255, false);
        return $this->budgets->saveLine($user, $id, $lineId, $categoryId, $amount, $notes, self::version($data));
    }

    public function deleteLine(string $user, string $id, string $lineId, array $data): void
    {
        $this->budgets->deleteLine($user, $id, $lineId, self::version($data));
    }

    private static function version(array $data): int
    {
        if (!isset($data['version']) || filter_var($data['version'], FILTER_VALIDATE_INT) === false || (int)$data['version'] < 1) {
            throw Problem::invalid('version', 'Expected current positive integer version');
        }
        return (int)$data['version'];
    }
}
