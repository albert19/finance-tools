<?php
namespace App\Tests;

use App\Service\Inputs;
use App\Service\Problem;
use App\Service\Simulator;
use PHPUnit\Framework\TestCase;

final class SimulatorTest extends TestCase
{
    public function testNoGrowthMonthlyEndContributions(): void
    {
        $result = (new Simulator())->run(['initialCapital' => 1000, 'contribution' => 100,
            'annualRate' => 0, 'horizonMonths' => 12]);
        self::assertEqualsWithDelta(2200, $result['summary']['finalCapital'], 1e-8);
        self::assertCount(12, $result['monthly']);
        self::assertEqualsWithDelta(2200, $result['summary']['totalContributed'], 1e-8);
    }

    public function testSpanishTaxOnUnrealisedGain(): void
    {
        $result = (new Simulator())->run(['initialCapital' => 10000, 'contribution' => 0,
            'annualRate' => 12, 'horizonMonths' => 12, 'applyTaxes' => true]);
        $expected = 10000 * 1.01 ** 12;
        self::assertEqualsWithDelta($expected, $result['summary']['finalCapital'], 1e-6);
        self::assertEqualsWithDelta(($expected - 10000) * .19, $result['summary']['finalTax'], 1e-6);
    }

    public function testInvalidInputs(): void
    {
        $this->expectException(Problem::class);
        (new Simulator())->run(['initialCapital' => 0, 'contribution' => 0, 'annualRate' => 5, 'horizonMonths' => 12]);
    }

    public function testMoneyRejectsMoreThanTwoPlaces(): void
    {
        $this->expectException(Problem::class);
        Inputs::money(['amount' => '10.001'], 'amount');
    }
}
