<?php
namespace App\Service;

use App\Port\LedgerRepository;

/** Category and transaction use cases, independent of the persistence adapter. */
final class FinanceLedger
{
    public function __construct(private LedgerRepository $ledger) {}

    public static function kind(mixed $value): string
    {
        if (!in_array($value, ['income', 'expense'], true)) { throw Problem::invalid('kind', 'Expected income or expense'); }
        return $value;
    }

    public function categories(string $user, bool $includeArchived): array
    {
        return $this->ledger->categories($user, $includeArchived);
    }

    public function createCategory(string $user, array $data): array
    {
        $name = Inputs::text($data, 'name', 100);
        return $this->ledger->createCategory($user, self::kind($data['kind'] ?? null), $name);
    }

    public function defaults(string $user): array
    {
        return ['created' => $this->ledger->createDefaults($user, [
            'income' => ['Salary', 'Other income'],
            'expense' => ['Housing', 'Food', 'Transport', 'Health', 'Leisure', 'Other expense'],
        ])];
    }

    public function updateCategory(string $user, string $id, array $data): array
    {
        $this->ledger->category($user, $id);
        $patch = [];
        if (array_key_exists('name', $data)) { $patch['name'] = Inputs::text($data, 'name', 100); }
        if (array_key_exists('archived', $data)) {
            if (!is_bool($data['archived'])) { throw Problem::invalid('archived', 'Expected boolean'); }
            $patch['archived'] = (int)$data['archived'];
        }
        return $this->ledger->updateCategory($user, $id, $patch);
    }

    public function deleteCategory(string $user, string $id): void
    {
        $this->ledger->category($user, $id);
        if ($this->ledger->categoryInUse($user, $id)) {
            throw new Problem(409, 'category_in_use', 'Category is in use');
        }
        $this->ledger->deleteCategory($user, $id);
    }

    public function transactions(string $user, mixed $year, mixed $month, mixed $kind): array
    {
        [$year, $month] = Inputs::period($year, $month);
        if ($kind !== null) { self::kind($kind); }
        return $this->ledger->transactions($user, sprintf('%04d-%02d-01', $year, $month),
            date('Y-m-d', strtotime("$year-$month-01 +1 month")), $kind);
    }

    public function saveTransaction(string $user, array $data, ?string $id): array
    {
        if ($id) { $this->ledger->transaction($user, $id); }
        $category = $this->ledger->category($user, Inputs::text($data, 'categoryId', 36));
        if ($category['archived']) { throw Problem::invalid('categoryId', 'Category is archived'); }
        $values = ['category_id' => $category['id'], 'date' => Inputs::date($data, 'date'),
            'amount' => Inputs::money($data, 'amount'), 'description' => Inputs::text($data, 'description', 255, false)];
        return $this->ledger->saveTransaction($user, $id, $values);
    }

    public function deleteTransaction(string $user, string $id): void
    {
        $this->ledger->transaction($user, $id);
        $this->ledger->deleteTransaction($user, $id);
    }
}
