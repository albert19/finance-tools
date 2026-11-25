<?php
namespace App\Service;

use App\Entity\Investment;
use App\Port\InvestmentRepository;

/** Application boundary: every lookup includes the authenticated owner. */
final class PortfolioService
{
    public function __construct(private InvestmentRepository $investments, private Simulator $simulator, private PerformanceComparison $comparison) {}

    private function owned(string $id, string $user): Investment
    {
        $investment = $this->investments->findOwned($user, $id);
        if (!$investment) { throw new Problem(404, 'not_found', 'Not found'); }
        return $investment;
    }

    public function list(string $user): array
    {
        return $this->investments->listForOwner($user);
    }

    public function create(string $user, array $data): array
    {
        if (!isset($data['parameters']) || !is_array($data['parameters'])) { throw Problem::invalid('parameters', 'Expected simulation parameters'); }
        $investment = $this->investments->create($user,
            Inputs::text($data, 'name', 150), Inputs::date($data, 'startDate'),
            Inputs::text($data, 'notes', 2000, false), $this->simulator->validate($data['parameters']));
        return $this->detail($user, $investment->id);
    }

    public function detail(string $user, string $id): array
    {
        $investment = $this->owned($id, $user);
        $snapshots = $this->investments->snapshots($investment);
        $projection = $this->simulator->run($investment->parameters);
        return ['id' => $investment->id, 'name' => $investment->name,
            'start_date' => $investment->startDate->format('Y-m-d'), 'status' => $investment->status,
            'notes' => $investment->notes, 'parameters' => $investment->parameters,
            'projection' => $projection, 'snapshots' => $snapshots];
    }

    public function compare(string $user, string $id): array
    {
        $investment = $this->owned($id, $user);
        return $this->comparison->compare($investment->parameters, $investment->startDate->format('Y-m-d'), $this->investments->snapshots($investment));
    }

    public function update(string $user, string $id, array $data): array
    {
        $investment = $this->owned($id, $user);
        if (isset($data['name'])) { $investment->name = Inputs::text($data, 'name', 150); }
        if (isset($data['notes'])) { $investment->notes = Inputs::text($data, 'notes', 2000, false); }
        if (isset($data['status'])) {
            if (!in_array($data['status'], ['active', 'closed'], true)) { throw Problem::invalid('status', 'Expected active or closed'); }
            $investment->status = $data['status'];
        }
        $this->investments->save($investment);
        return $this->detail($user, $id);
    }

    public function delete(string $user, string $id): void
    {
        $this->investments->delete($this->owned($id, $user));
    }

    public function snapshot(string $user, string $id, array $data): string
    {
        $date = Inputs::date($data, 'date');
        $value = Inputs::money($data, 'marketValue', false);
        $contribution = isset($data['contribution']) ? Inputs::money($data, 'contribution', false) : '0.00';
        $withdrawal = isset($data['withdrawal']) ? Inputs::money($data, 'withdrawal', false) : '0.00';
        $note = Inputs::text($data, 'note', 255, false);
        return $this->investments->addSnapshot($user, $id, $date, $value, $contribution, $withdrawal, $note);
    }

    public function deleteSnapshot(string $user, string $id, string $snapshotId): void
    {
        $investment = $this->owned($id, $user);
        if (!$this->investments->deleteSnapshot($investment, $snapshotId)) {
            throw new Problem(404, 'not_found', 'Snapshot not found');
        }
    }
}
