<?php
namespace App\Repository;

use App\Entity\Investment;
use App\Entity\InvestmentSnapshot;
use App\Entity\User;
use App\Port\InvestmentRepository;
use App\Service\Problem;
use Doctrine\DBAL\Platforms\SQLitePlatform;
use Doctrine\ORM\EntityManagerInterface;

final class DoctrineInvestmentRepository implements InvestmentRepository
{
    public function __construct(private EntityManagerInterface $em, private FinanceStore $ids) {}

    public function findOwned(string $user, string $id): ?Investment
    {
        return $this->em->getRepository(Investment::class)->findOneBy(['id' => $id, 'owner' => $user]);
    }

    public function listForOwner(string $user): array
    {
        return $this->em->getConnection()->fetchAllAssociative(
            'SELECT id, name, start_date AS startDate, status, notes FROM investments WHERE user_id = ? ORDER BY start_date, name', [$user]);
    }

    public function create(string $user, string $name, string $startDate, string $notes, array $parameters): Investment
    {
        $investment = new Investment($this->ids->id(), $this->em->getReference(User::class, $user),
            $name, $startDate, $notes, $parameters);
        $this->em->persist($investment);
        $this->em->flush();
        return $investment;
    }

    public function save(Investment $investment): void
    {
        $this->em->flush();
    }

    public function delete(Investment $investment): void
    {
        // DB cascade matches the pre-existing migration.
        $this->em->remove($investment);
        $this->em->flush();
    }

    public function snapshots(Investment $investment): array
    {
        $rows = $this->em->getRepository(InvestmentSnapshot::class)->findBy(['investment' => $investment], ['date' => 'ASC', 'id' => 'ASC']);
        return array_map(static fn(InvestmentSnapshot $snap) => [
            'id' => $snap->id, 'date' => $snap->date->format('Y-m-d'), 'marketValue' => $snap->marketValue,
            'contribution' => $snap->contribution, 'withdrawal' => $snap->withdrawal, 'note' => $snap->note,
        ], $rows);
    }

    public function addSnapshot(string $user, string $id, string $date, string $value, string $contribution, string $withdrawal, string $note): string
    {
        $db = $this->em->getConnection();
        // Lock the parent to serialize same-investment inserts without changing existing tables
        // (including deployments with pre-existing duplicate snapshot dates).
        $db->beginTransaction();
        try {
            $lock = $db->getDatabasePlatform() instanceof SQLitePlatform ? '' : ' FOR UPDATE';
            $row = $db->fetchAssociative('SELECT id, start_date FROM investments WHERE id = ? AND user_id = ?'.$lock, [$id, $user]);
            if (!$row) { throw new Problem(404, 'not_found', 'Not found'); }
            if ($date < $row['start_date']) { throw Problem::invalid('date', 'Snapshot date must be on or after investment start'); }
            if ($db->fetchOne('SELECT id FROM investment_snapshots WHERE investment_id = ? AND date = ? LIMIT 1', [$id, $date])) {
                throw Problem::invalid('date', 'Snapshot already exists on this date');
            }
            $investment = $this->findOwned($user, $id);
            if (!$investment) { throw new Problem(404, 'not_found', 'Not found'); }
            $snap = $investment->addSnapshot($this->ids->id(), $date, $value, $contribution, $withdrawal, $note);
            $this->em->persist($snap);
            $this->em->flush();
            $db->commit();
            return $snap->id;
        } catch (\Throwable $e) {
            $db->rollBack();
            throw $e;
        }
    }

    public function deleteSnapshot(Investment $investment, string $snapshotId): bool
    {
        $snap = $this->em->getRepository(InvestmentSnapshot::class)->findOneBy(['id' => $snapshotId, 'investment' => $investment]);
        if (!$snap) { return false; }
        $this->em->remove($snap);
        $this->em->flush();
        return true;
    }
}
