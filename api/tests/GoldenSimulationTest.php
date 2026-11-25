<?php
namespace App\Tests;

use App\Service\Problem;
use App\Service\Simulator;
use PHPUnit\Framework\TestCase;

final class GoldenSimulationTest extends TestCase
{
    public function testAllFiveLegacyPythonVectors(): void
    {
        $vectors = json_decode(file_get_contents(__DIR__.'/../../contracts/simulation-vectors/legacy-python.json'), true, 512, JSON_THROW_ON_ERROR);
        self::assertCount(5, $vectors);
        $fields = [
            'initial_capital' => 'initialCapital', 'contribution' => 'contribution',
            'contribution_frequency' => 'contributionFrequency', 'annual_rate_pct' => 'annualRate',
            'compounding_frequency' => 'compoundingFrequency', 'horizon_months' => 'horizonMonths',
            'contribution_timing' => 'contributionTiming', 'inflation_pct' => 'inflation',
            'ter_pct' => 'ter', 'contribution_increase_pct' => 'contributionIncrease',
            'withdrawal_amount' => 'withdrawalAmount', 'withdrawal_frequency' => 'withdrawalFrequency',
            'withdrawal_start_month' => 'withdrawalStartMonth', 'apply_taxes' => 'applyTaxes',
        ];
        $summaryFields = [
            'final_capital' => 'finalCapital', 'final_capital_net' => 'finalCapitalNet',
            'total_contributed' => 'totalContributed', 'total_withdrawn' => 'totalWithdrawn',
            'interest_earned' => 'interestEarned', 'total_fees' => 'totalFees',
            'total_taxes' => 'totalTaxes', 'real_final_capital' => 'realFinalCapital',
            'real_final_capital_net' => 'realFinalCapitalNet', 'total_return_pct' => 'totalReturnPct',
            'irr_pct' => 'irrPct', 'irr_net_pct' => 'irrNetPct', 'depletion_month' => 'depletionMonth',
        ];
        $rowFields = [
            'index' => 'index', 'opening' => 'opening', 'contribution' => 'contribution',
            'interest' => 'interest', 'fees' => 'fees', 'withdrawal' => 'withdrawal',
            'taxes' => 'taxes', 'closing' => 'closing', 'cost_basis' => 'costBasis',
            'gains' => 'gains', 'real_closing' => 'realClosing',
        ];
        foreach ($vectors as $vector) {
            $input = [];
            foreach ($fields as $source => $target) { $input[$target] = $vector['input'][$source]; }
            $result = (new Simulator())->run($input);
            foreach ($summaryFields as $source => $target) {
                $this->compare($vector['expected']['summary'][$source], $result['summary'][$target], $vector['name']." summary.$source");
            }
            foreach (['monthly', 'yearly'] as $period) {
                self::assertCount(count($vector['expected'][$period]), $result[$period], $vector['name']." $period count");
                foreach ($vector['expected'][$period] as $i => $expected) {
                    foreach ($rowFields as $source => $target) {
                        $this->compare($expected[$source], $result[$period][$i][$target], $vector['name']." {$period}[{$i}].{$source}");
                    }
                }
            }
        }
    }

    private function compare(mixed $expected, mixed $actual, string $label): void
    {
        if (is_numeric($expected)) { self::assertEqualsWithDelta((float)$expected, (float)$actual, max(1e-7, abs((float)$expected) * 1e-9), $label); }
        else { self::assertSame($expected, $actual, $label); }
    }

    public function testIrrAndDatedXirr(): void
    {
        self::assertEqualsWithDelta(.1, Simulator::irr([[0, -100], [1, 110]]), 1e-10);
        self::assertEqualsWithDelta(.1, Simulator::xirr([['2024-01-01', -100], ['2024-12-31', 110]]), 1e-10);
        self::assertNull(Simulator::irr([[0, -100], [1, -100]]));
    }

    public function testInvalidWithdrawalStartAndBoolean(): void
    {
        foreach ([['withdrawalAmount' => 50, 'withdrawalStartMonth' => 12], ['applyTaxes' => 'false']] as $invalid) {
            try {
                (new Simulator())->run(['initialCapital' => 100, 'contribution' => 0, 'annualRate' => 5, 'horizonMonths' => 12, ...$invalid]);
                self::fail('Expected validation error');
            } catch (Problem $e) { self::assertSame(422, $e->status); }
        }
    }
}
