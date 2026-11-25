<?php
namespace App\Tests;

use App\Entity\Investment;
use App\Entity\User;
use App\Port\InvestmentRepository;
use App\Repository\DoctrineInvestmentRepository;
use App\Repository\FinanceStore;
use App\Service\PerformanceComparison;
use App\Service\PortfolioService;
use App\Service\Problem;
use App\Service\Simulator;
use Doctrine\DBAL\DriverManager;
use Doctrine\ORM\EntityManager;
use Doctrine\ORM\ORMSetup;
use Doctrine\ORM\Tools\SchemaTool;
use PHPUnit\Framework\TestCase;

final class PortfolioServiceTest extends TestCase
{
    private function setupService(): array
    {
        $config = ORMSetup::createAttributeMetadataConfiguration([__DIR__.'/../src/Entity'], true);
        $config->enableNativeLazyObjects(true);
        $em = new EntityManager(DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true]), $config);
        $classes = array_map($em->getClassMetadata(...), [
            User::class, \App\Entity\Category::class, \App\Entity\MonthlyBudget::class,
            \App\Entity\BudgetLine::class, \App\Entity\Transaction::class,
            \App\Entity\RefreshToken::class, Investment::class, \App\Entity\InvestmentSnapshot::class,
        ]);
        (new SchemaTool($em))->createSchema($classes);
        $alice = new User(); $alice->id = 'alice'; $alice->email = 'alice@example.com';
        $alice->passwordHash = 'hash'; $alice->roles = ['ROLE_USER'];
        $bob = new User(); $bob->id = 'bob'; $bob->email = 'bob@example.com';
        $bob->passwordHash = 'hash'; $bob->roles = ['ROLE_USER'];
        $em->persist($alice); $em->persist($bob); $em->flush();
        $sim = new Simulator();
        $repository = new DoctrineInvestmentRepository($em, new FinanceStore($em->getConnection()));
        return [$em, new PortfolioService($repository, $sim, new PerformanceComparison($sim))];
    }

    public function testOwnerScopeDateUniquenessAndComparison(): void
    {
        [$em, $portfolio] = $this->setupService();
        $created = $portfolio->create('alice', [
            'name' => 'Index fund', 'startDate' => '2024-01-01',
            'parameters' => ['initialCapital' => 100, 'contribution' => 0, 'annualRate' => 0, 'horizonMonths' => 24],
        ]);
        $id = $created['id'];
        self::assertSame([], $portfolio->list('bob'));
        foreach (['detail', 'compare'] as $operation) {
            try { $portfolio->$operation('bob', $id); self::fail('Foreign investment leaked'); }
            catch (Problem $e) { self::assertSame(404, $e->status); }
        }
        try { $portfolio->snapshot('bob', $id, ['date' => '2024-03-01', 'marketValue' => 110]); self::fail('Foreign write'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        try { $portfolio->snapshot('alice', $id, ['date' => '2023-12-31', 'marketValue' => 110]); self::fail('Pre-start snapshot'); }
        catch (Problem $e) { self::assertSame(422, $e->status); }
        self::assertSame(0, $em->getConnection()->getTransactionNestingLevel());
        $sid = $portfolio->snapshot('alice', $id, ['date' => '2024-12-31', 'marketValue' => 110]);
        try { $portfolio->snapshot('alice', $id, ['date' => '2024-12-31', 'marketValue' => 999]); self::fail('Duplicate snapshot'); }
        catch (Problem $e) { self::assertSame(422, $e->status); }
        self::assertSame(0, $em->getConnection()->getTransactionNestingLevel());
        $report = $portfolio->compare('alice', $id);
        self::assertSame('Ahead of plan', $report['status']);
        self::assertEqualsWithDelta(.1, $report['actualXirr'], 1e-9);
        self::assertEqualsWithDelta(.1, $report['points'][0]['deviationPct'], 1e-9);
        self::assertSame(1, count($portfolio->detail('alice', $id)['snapshots']));
        try { $portfolio->deleteSnapshot('bob', $id, $sid); self::fail('Foreign delete'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        $portfolio->deleteSnapshot('alice', $id, $sid);
        self::assertSame('No data yet', $portfolio->compare('alice', $id)['status']);
        self::assertNull($portfolio->compare('alice', $id)['actualXirr']);
        $em->close();
    }

    public function testCrudAndSnapshotRepresentationRemainOwnerScoped(): void
    {
        [$em, $portfolio] = $this->setupService();
        $created = $portfolio->create('alice', [
            'name' => 'Fund', 'startDate' => '2024-01-01', 'notes' => 'First',
            'parameters' => ['initialCapital' => 100, 'contribution' => 0, 'annualRate' => 0, 'horizonMonths' => 12],
        ]);
        $id = $created['id'];
        self::assertSame('2024-01-01', $created['start_date']);
        self::assertSame('Fund', $portfolio->list('alice')[0]['name']);
        self::assertSame('2024-01-01', $portfolio->list('alice')[0]['startDate']);
        $updated = $portfolio->update('alice', $id, ['name' => 'New fund', 'status' => 'closed', 'notes' => 'Updated']);
        self::assertSame('closed', $updated['status']);
        self::assertSame('Updated', $updated['notes']);
        try { $portfolio->update('bob', $id, ['name' => 'Stolen']); self::fail('Foreign update'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        try { $portfolio->delete('bob', $id); self::fail('Foreign delete'); }
        catch (Problem $e) { self::assertSame(404, $e->status); }
        $snapshot = $portfolio->snapshot('alice', $id, [
            'date' => '2024-03-01', 'marketValue' => 120, 'contribution' => 10,
            'withdrawal' => 5, 'note' => 'Quarterly',
        ]);
        self::assertSame([
            'id' => $snapshot, 'date' => '2024-03-01', 'marketValue' => '120.00',
            'contribution' => '10.00', 'withdrawal' => '5.00', 'note' => 'Quarterly',
        ], $portfolio->detail('alice', $id)['snapshots'][0]);
        self::assertSame(0, $em->getConnection()->getTransactionNestingLevel());
        $portfolio->delete('alice', $id);
        self::assertSame([], $portfolio->list('alice'));
        $em->close();
    }

    public function testServiceCalculatesDetailsThroughRepositoryPort(): void
    {
        $sim = new Simulator();
        $user = new User();
        $user->id = 'alice';
        $investment = new Investment('fund', $user, 'Fund', '2024-01-01', '', [
            'initialCapital' => 100, 'contribution' => 0, 'annualRate' => 0, 'horizonMonths' => 12,
        ]);
        $repository = $this->createMock(InvestmentRepository::class);
        $repository->expects(self::once())->method('findOwned')->with('alice', 'fund')->willReturn($investment);
        $repository->expects(self::once())->method('snapshots')->with($investment)->willReturn([]);
        $service = new PortfolioService($repository, $sim, new PerformanceComparison($sim));
        $detail = $service->detail('alice', 'fund');
        self::assertSame('fund', $detail['id']);
        self::assertSame('Fund', $detail['name']);
        self::assertSame([], $detail['snapshots']);
        self::assertArrayHasKey('projection', $detail);
    }

    public function testFractionalInterpolationAndZeroProjection(): void
    {
        $comparison = new PerformanceComparison(new Simulator());
        $p = ['initialCapital' => 100, 'contribution' => 0, 'annualRate' => 12, 'horizonMonths' => 12];
        $report = $comparison->compare($p, '2024-01-01', [
            ['date' => '2024-01-16', 'marketValue' => '110.00', 'contribution' => '0', 'withdrawal' => '0'],
        ]);
        $months = 15 / (365.25 / 12);
        $closing = $report['projection']['monthly'][0]['closing'];
        self::assertEqualsWithDelta(100 + ($closing - 100) * $months, $report['points'][0]['projected'], 1e-9);
        $zero = $comparison->compare(['initialCapital' => 0, 'contribution' => 10, 'annualRate' => 0, 'horizonMonths' => 12],
            '2024-01-01', [['date' => '2024-01-01', 'marketValue' => '0', 'contribution' => '0', 'withdrawal' => '0']]);
        self::assertNull($zero['points'][0]['deviationPct']);
        self::assertNull($zero['actualXirr']);
        self::assertSame('No data yet', $zero['status']);
    }

    public function testCumulativeCashFlowsAreIncludedInXirrAndProjectionClampsAfterHorizon(): void
    {
        $comparison = new PerformanceComparison(new Simulator());
        $report = $comparison->compare(
            ['initialCapital' => 100, 'contribution' => 0, 'annualRate' => 0, 'horizonMonths' => 12],
            '2024-01-01',
            [
                ['date' => '2025-12-31', 'marketValue' => '140', 'contribution' => '0', 'withdrawal' => '0'],
                ['date' => '2024-12-31', 'marketValue' => '50', 'contribution' => '50', 'withdrawal' => '0'],
            ],
        );
        self::assertSame('2024-12-31', $report['points'][0]['date']);
        self::assertSame(150.0, $report['points'][1]['contributedActual']);
        self::assertSame(100.0, $report['points'][1]['projected']);
        self::assertSame('Ahead of plan', $report['status']);
        self::assertEqualsWithDelta(Simulator::xirr([
            ['2024-01-01', -100], ['2024-12-31', -50], ['2025-12-31', 140],
        ]), $report['actualXirr'], 1e-9);
        $behind = $comparison->compare(
            ['initialCapital' => 100, 'contribution' => 0, 'annualRate' => 0, 'horizonMonths' => 12],
            '2024-01-01', [['date' => '2024-12-31', 'marketValue' => '90', 'contribution' => '0', 'withdrawal' => '0']],
        );
        self::assertSame('Behind plan', $behind['status']);
    }

    public function testStatusToleranceComesFromPortfolioTolerancePct(): void
    {
        $comparison = new PerformanceComparison(new Simulator());
        // 0% growth, so the projection stays at 100 and a 103 valuation is +3%.
        $status = static fn (): string => $comparison->compare(
            ['initialCapital' => 100, 'contribution' => 0, 'annualRate' => 0, 'horizonMonths' => 12],
            '2024-01-01', [['date' => '2024-06-01', 'marketValue' => '103', 'contribution' => '0', 'withdrawal' => '0']],
        )['status'];
        $previous = getenv('PORTFOLIO_TOLERANCE_PCT');
        try {
            putenv('PORTFOLIO_TOLERANCE_PCT');
            self::assertSame('Ahead of plan', $status());
            putenv('PORTFOLIO_TOLERANCE_PCT=5');
            self::assertSame('On track', $status());
            putenv('PORTFOLIO_TOLERANCE_PCT=not-a-number');
            self::assertSame('Ahead of plan', $status());
        } finally {
            putenv($previous === false ? 'PORTFOLIO_TOLERANCE_PCT' : 'PORTFOLIO_TOLERANCE_PCT='.$previous);
        }
    }
}
