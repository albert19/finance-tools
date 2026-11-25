<?php
namespace App\Service;

/** Portfolio comparison follows the Python domain's fractional-month interpolation and ACT/365 XIRR. */
final class PerformanceComparison
{
    public function __construct(private Simulator $simulator) {}

    public function compare(array $parameters, string $startDate, array $snapshots): array
    {
        $projection = $this->simulator->run($parameters);
        $initial = (float)$projection['parameters']['initialCapital'];
        $contributed = $initial;
        $flows = [[$startDate, -$initial]];
        $points = [];
        usort($snapshots, static fn($a, $b) => strcmp($a['date'], $b['date']));
        $start = new \DateTimeImmutable($startDate);
        foreach ($snapshots as $snapshot) {
            $date = $snapshot['date'];
            $contribution = (float)$snapshot['contribution'];
            $withdrawal = (float)$snapshot['withdrawal'];
            $contributed += $contribution - $withdrawal;
            $flows[] = [$date, $withdrawal - $contribution];
            $elapsed = $start->diff(new \DateTimeImmutable($date));
            $months = ($elapsed->invert ? -1 : 1) * $elapsed->days / (365.25 / 12);
            $projected = $this->balanceAt($projection['monthly'], $initial, $months);
            $actual = (float)$snapshot['marketValue'];
            $deviation = $actual - $projected;
            $points[] = ['date' => $date, 'monthsElapsed' => $months, 'projected' => $projected,
                'actual' => $actual, 'contributedActual' => $contributed, 'deviation' => $deviation,
                'deviationPct' => $projected != 0.0 ? $deviation / $projected : null];
        }
        $latest = $points ? $points[array_key_last($points)] : null;
        $actualXirr = $latest && $latest['date'] > $startDate
            ? Simulator::xirr([...$flows, [$latest['date'], $latest['actual']]]) : null;
        $deviationPct = $latest['deviationPct'] ?? null;
        $tolerance = Tolerance::fromEnv('PORTFOLIO_TOLERANCE_PCT');
        return ['projection' => $projection, 'points' => $points,
            'expectedRate' => ($projection['summary']['irrPct'] ?? null) !== null
                ? $projection['summary']['irrPct'] / 100 : $projection['parameters']['annualRate'] / 100,
            'actualXirr' => $actualXirr,
            'status' => $deviationPct === null ? 'No data yet'
                : ($deviationPct > $tolerance ? 'Ahead of plan' : ($deviationPct < -$tolerance ? 'Behind plan' : 'On track'))];
    }

    private function balanceAt(array $monthly, float $initial, float $months): float
    {
        if ($months <= 0 || !$monthly) { return $initial; }
        if ($months >= count($monthly)) { return (float)$monthly[array_key_last($monthly)]['closing']; }
        $whole = (int)$months;
        $lower = $whole > 0 ? (float)$monthly[$whole - 1]['closing'] : $initial;
        return $lower + ((float)$monthly[$whole]['closing'] - $lower) * ($months - $whole);
    }
}
