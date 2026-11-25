<?php
namespace App\Service;

/** Monthly projection with Python-domain cash-flow timing and tax basis. */
final class Simulator
{
    private const FREQUENCIES = ['daily' => 365, 'monthly' => 12, 'quarterly' => 4, 'semiannual' => 2, 'annual' => 1];

    public function validate(array $p): array
    {
        $initial = $this->number($p, 'initialCapital', 0, 9999999999999);
        $contribution = $this->number($p, 'contribution', 0, 9999999999999);
        if ($initial == 0 && $contribution == 0) { throw Problem::invalid('initialCapital', 'Enter initial capital or a contribution'); }
        $months = $p['horizonMonths'] ?? null;
        if (filter_var($months, FILTER_VALIDATE_INT) === false || (int)$months < 1 || (int)$months > 1200) { throw Problem::invalid('horizonMonths', 'Expected 1–1200 months'); }
        $frequency = $p['contributionFrequency'] ?? 'monthly';
        $compounding = $p['compoundingFrequency'] ?? 'monthly';
        $withdrawalFrequency = $p['withdrawalFrequency'] ?? 'monthly';
        foreach (['contributionFrequency' => $frequency, 'compoundingFrequency' => $compounding, 'withdrawalFrequency' => $withdrawalFrequency] as $field => $value) {
            if (!is_string($value) || !isset(self::FREQUENCIES[$value]) || ($field !== 'compoundingFrequency' && $value === 'daily')) { throw Problem::invalid($field, 'Unsupported frequency'); }
        }
        $timing = $p['contributionTiming'] ?? 'end';
        if (!in_array($timing, ['beginning', 'end'], true)) { throw Problem::invalid('contributionTiming', 'Expected beginning or end'); }
        $start = $p['withdrawalStartMonth'] ?? 0;
        if (filter_var($start, FILTER_VALIDATE_INT) === false || (int)$start < 0) { throw Problem::invalid('withdrawalStartMonth', 'Expected non-negative month'); }
        $withdrawal = $this->number($p, 'withdrawalAmount', 0, 9999999999999, 0);
        if ($withdrawal > 0 && (int)$start >= (int)$months) { throw Problem::invalid('withdrawalStartMonth', 'Withdrawals must start before the end of the horizon'); }
        $taxes = $p['applyTaxes'] ?? false;
        if (!is_bool($taxes)) { throw Problem::invalid('applyTaxes', 'Expected boolean'); }
        return [
            'initialCapital' => $initial, 'contribution' => $contribution, 'annualRate' => $this->number($p, 'annualRate', -50, 100),
            'horizonMonths' => (int)$months, 'contributionFrequency' => $frequency, 'compoundingFrequency' => $compounding,
            'contributionTiming' => $timing, 'inflation' => $this->number($p, 'inflation', 0, 50, 0),
            'ter' => $this->number($p, 'ter', 0, 10, 0), 'contributionIncrease' => $this->number($p, 'contributionIncrease', 0, 50, 0),
            'withdrawalAmount' => $withdrawal, 'withdrawalFrequency' => $withdrawalFrequency, 'withdrawalStartMonth' => (int)$start,
            'applyTaxes' => $taxes,
        ];
    }

    private function number(array $p, string $field, float $min, float $max, ?float $default = null): float
    {
        $v = $p[$field] ?? $default;
        if ((!is_int($v) && !is_float($v) && !is_string($v)) || !is_numeric($v) || !is_finite((float)$v) || (float)$v < $min || (float)$v > $max) {
            throw Problem::invalid($field, "Expected number between $min and $max");
        }
        return (float)$v;
    }

    public function run(array $input): array
    {
        $p = $this->validate($input);
        $n = self::FREQUENCIES[$p['compoundingFrequency']];
        $growth = (1 + $p['annualRate'] / 100 / $n) ** ($n / 12) - 1;
        $feeRate = 1 - (1 + $p['ter'] / 100) ** (-1 / 12);
        $step = 12 / self::FREQUENCIES[$p['contributionFrequency']];
        $withdrawalStep = 12 / self::FREQUENCIES[$p['withdrawalFrequency']];
        $beginning = $p['contributionTiming'] === 'beginning';
        $balance = $basis = $p['initialCapital'];
        $contributed = $balance; $withdrawn = $feesTotal = $taxesTotal = $yearGain = 0.0;
        $depletion = null; $rows = []; $years = [];
        $grossFlows = $netFlows = [[0.0, -$balance]];
        for ($month = 1; $month <= $p['horizonMonths']; ++$month) {
            $index = $month - 1; $opening = $balance;
            $inWithdrawal = $p['withdrawalAmount'] > 0 && $month > $p['withdrawalStartMonth'];
            $due = $index % $step === ($beginning ? 0 : $step - 1);
            $amount = $due && !$inWithdrawal && $depletion === null
                ? $p['contribution'] * (1 + $p['contributionIncrease'] / 100) ** intdiv($index, 12) : 0.0;
            if ($beginning && $amount) {
                $balance += $amount; $basis += $amount;
                $grossFlows[] = $netFlows[] = [$index / 12, -$amount];
            }
            $interest = $balance * $growth;
            $fees = ($balance + $interest) * $feeRate;
            $balance += $interest - $fees;
            if (!$beginning && $amount) {
                $balance += $amount; $basis += $amount;
                $grossFlows[] = $netFlows[] = [$month / 12, -$amount];
            }
            $withdrawal = 0.0;
            if ($inWithdrawal && $depletion === null && ($month - $p['withdrawalStartMonth']) % $withdrawalStep === 0) {
                $withdrawal = min($p['withdrawalAmount'], max($balance, 0.0));
                if ($balance > 0) {
                    $basisShare = $basis * $withdrawal / $balance;
                    $yearGain += $withdrawal - $basisShare;
                    $basis -= $basisShare;
                }
                $balance -= $withdrawal; $withdrawn += $withdrawal;
                $grossFlows[] = $netFlows[] = [$month / 12, $withdrawal];
                if ($balance < 0.005) { $balance = $basis = 0.0; $depletion = $month; }
            }
            $taxes = 0.0;
            if ($month % 12 === 0 || $month === $p['horizonMonths']) {
                $taxes = $p['applyTaxes'] ? $this->tax($yearGain) : 0.0;
                if ($taxes) { $netFlows[] = [$month / 12, -$taxes]; }
                $taxesTotal += $taxes;
                if ($month !== $p['horizonMonths']) { $yearGain = 0.0; }
            }
            $contributed += $amount; $feesTotal += $fees;
            $rows[] = ['index' => $month, 'opening' => $opening, 'contribution' => $amount, 'interest' => $interest,
                'fees' => $fees, 'withdrawal' => $withdrawal, 'taxes' => $taxes, 'closing' => $balance,
                'costBasis' => $basis, 'gains' => $balance - $basis,
                'realClosing' => $balance / (1 + $p['inflation'] / 100) ** ($month / 12)];
        }
        foreach (array_chunk($rows, 12) as $index => $chunk) {
            $last = $chunk[array_key_last($chunk)];
            $year = ['index' => $index + 1, 'opening' => $chunk[0]['opening']];
            foreach (['contribution', 'interest', 'fees', 'withdrawal', 'taxes'] as $field) { $year[$field] = array_sum(array_column($chunk, $field)); }
            foreach (['closing', 'costBasis', 'gains', 'realClosing'] as $field) { $year[$field] = $last[$field]; }
            $years[] = $year;
        }
        $finalTax = $p['applyTaxes'] ? $this->tax($yearGain + $balance - $basis) - $this->tax($yearGain) : 0.0;
        $net = $balance - $finalTax;
        $deflator = (1 + $p['inflation'] / 100) ** ($p['horizonMonths'] / 12);
        $grossFlows[] = [$p['horizonMonths'] / 12, $balance];
        $netFlows[] = [$p['horizonMonths'] / 12, $net];
        $gain = $balance + $withdrawn - $contributed;
        $irr = self::irr($grossFlows); $irrNet = self::irr($netFlows);
        return ['parameters' => $p, 'summary' => [
            'finalCapital' => $balance, 'finalCapitalNet' => $net, 'totalContributed' => $contributed,
            'totalWithdrawn' => $withdrawn, 'interestEarned' => $gain, 'totalFees' => $feesTotal,
            'totalTaxes' => $taxesTotal + $finalTax, 'finalTax' => $finalTax,
            'realFinalCapital' => $balance / $deflator, 'realFinalCapitalNet' => $net / $deflator,
            'totalReturn' => $contributed ? $gain / $contributed : 0.0,
            'totalReturnPct' => $contributed ? $gain / $contributed * 100 : 0.0,
            'irrPct' => $irr === null ? null : $irr * 100, 'irrNetPct' => $irrNet === null ? null : $irrNet * 100,
            'depletionMonth' => $depletion,
        ], 'monthly' => $rows, 'yearly' => $years];
    }

    private function tax(float $gain): float
    {
        $total = $lower = 0.0;
        foreach ([[6000, .19], [50000, .21], [200000, .23], [300000, .27], [INF, .30]] as [$upper, $rate]) {
            $total += max(0, min($gain, $upper) - $lower) * $rate;
            $lower = $upper;
        }
        return $total;
    }

    /** Annualized money-weighted return; XIRR uses ACT/365. */
    public static function irr(array $flows): ?float
    {
        $flows = array_values(array_filter($flows, static fn($f) => $f[1] != 0));
        if (!array_filter($flows, static fn($f) => $f[1] < 0) || !array_filter($flows, static fn($f) => $f[1] > 0)) { return null; }
        $npv = static function (float $rate) use ($flows): float {
            $sum = 0.0;
            foreach ($flows as [$t, $amount]) { $sum += $amount / (1 + $rate) ** $t; }
            return $sum;
        };
        $rate = 0.05;
        for ($i = 0; $i < 50; ++$i) {
            $value = $slope = 0.0;
            foreach ($flows as [$t, $amount]) {
                $value += $amount / (1 + $rate) ** $t;
                $slope += -$t * $amount / (1 + $rate) ** ($t + 1);
            }
            if ($slope == 0 || !is_finite($slope) || !is_finite($value)) { break; }
            $next = $rate - $value / $slope;
            if ($next <= -0.99) { break; }
            if (abs($next - $rate) < 1e-10) { return $next; }
            $rate = $next;
        }
        $grid = [-0.99, -0.5, -0.2, 0.0, 0.1, 0.3, 1.0, 5.0, 100.0];
        for ($i = 1; $i < count($grid); ++$i) {
            $lo = $grid[$i - 1]; $hi = $grid[$i];
            $flo = $npv($lo); $fhi = $npv($hi);
            if ($flo == 0) { return $lo; }
            if (($flo > 0) === ($fhi > 0)) { continue; }
            for ($j = 0; $j < 200; ++$j) {
                $mid = ($lo + $hi) / 2; $fm = $npv($mid);
                if (abs($fm) < 1e-9 || $hi - $lo < 1e-12) { return $mid; }
                if (($fm > 0) === ($flo > 0)) { $lo = $mid; $flo = $fm; }
                else { $hi = $mid; }
            }
            return ($lo + $hi) / 2;
        }
        return null;
    }

    public static function xirr(array $datedFlows): ?float
    {
        if (!$datedFlows) { return null; }
        $start = min(array_column($datedFlows, 0));
        return self::irr(array_map(static fn($f) => [(strtotime($f[0]) - strtotime($start)) / 86400 / 365, $f[1]], $datedFlows));
    }
}
