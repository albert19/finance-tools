<?php
namespace App\Repository;

use App\Port\LedgerRepository;

/** Owner-scoped DBAL persistence for the legacy finance tables. */
final class DbalLedgerRepository implements LedgerRepository
{
    public function __construct(private FinanceStore $store) {}

    public function categories(string $user, bool $includeArchived): array
    {
        return $this->store->db->fetchAllAssociative(
            'SELECT id, name, kind, archived FROM categories WHERE user_id = ?'
            .($includeArchived ? '' : ' AND archived = 0').' ORDER BY kind, name', [$user]);
    }

    public function category(string $user, string $id): array
    {
        return $this->store->owned('categories', $id, $user);
    }

    public function createCategory(string $user, string $kind, string $name): array
    {
        $id = $this->store->id();
        $this->store->db->insert('categories', ['id' => $id, 'user_id' => $user,
            'kind' => $kind, 'name' => $name, 'normalized_name' => strtolower($name), 'archived' => 0]);
        return $this->category($user, $id);
    }

    public function createDefaults(string $user, array $defaults): array
    {
        $created = [];
        foreach ($defaults as $kind => $names) {
            foreach ($names as $name) {
                // Archived categories still occupy the unique (user, kind, name) key.
                if ($this->store->db->fetchOne(
                    'SELECT id FROM categories WHERE user_id = ? AND kind = ? AND normalized_name = ?',
                    [$user, $kind, strtolower($name)]
                )) { continue; }
                $id = $this->store->id();
                $this->store->db->insert('categories', ['id' => $id, 'user_id' => $user,
                    'kind' => $kind, 'name' => $name, 'normalized_name' => strtolower($name)]);
                $created[] = $id;
            }
        }
        return $created;
    }

    public function updateCategory(string $user, string $id, array $patch): array
    {
        if ($patch) {
            if (array_key_exists('name', $patch)) { $patch['normalized_name'] = strtolower($patch['name']); }
            $this->store->db->update('categories', $patch, ['id' => $id, 'user_id' => $user]);
        }
        return $this->category($user, $id);
    }

    public function categoryInUse(string $user, string $id): bool
    {
        return (bool)$this->store->db->fetchOne(
            'SELECT l.id FROM budget_lines l JOIN categories c ON c.id = l.category_id WHERE c.id = ? AND c.user_id = ?'
            .' UNION SELECT t.id FROM transactions t WHERE t.category_id = ? AND t.user_id = ? LIMIT 1',
            [$id, $user, $id, $user]
        );
    }

    public function deleteCategory(string $user, string $id): void
    {
        $this->store->db->delete('categories', ['id' => $id, 'user_id' => $user]);
    }

    public function transactions(string $user, string $start, string $end, ?string $kind): array
    {
        return $this->store->db->fetchAllAssociative(
            'SELECT t.id, t.category_id AS categoryId, c.name AS categoryName, c.kind, t.date, t.amount, t.description'
            .' FROM transactions t JOIN categories c ON c.id = t.category_id'
            .' WHERE t.user_id = ? AND t.date >= ? AND t.date < ?'
            .($kind !== null ? ' AND c.kind = ?' : '').' ORDER BY t.date, t.id',
            $kind !== null ? [$user, $start, $end, $kind] : [$user, $start, $end]
        );
    }

    public function transaction(string $user, string $id): array
    {
        return $this->store->owned('transactions', $id, $user);
    }

    public function saveTransaction(string $user, ?string $id, array $values): array
    {
        if ($id !== null) {
            $this->store->db->update('transactions', $values, ['id' => $id, 'user_id' => $user]);
        } else {
            $id = $this->store->id();
            $this->store->db->insert('transactions', ['id' => $id, 'user_id' => $user, ...$values]);
        }
        return $this->transaction($user, $id);
    }

    public function deleteTransaction(string $user, string $id): void
    {
        $this->store->db->delete('transactions', ['id' => $id, 'user_id' => $user]);
    }
}
