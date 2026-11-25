<?php
namespace App\Tests;

use App\Port\LedgerRepository;
use App\Service\FinanceLedger;
use App\Service\Problem;
use PHPUnit\Framework\TestCase;

final class LedgerUseCaseTest extends TestCase
{
    public function testValidationHappensBeforePersistence(): void
    {
        $repository = $this->createMock(LedgerRepository::class);
        $repository->expects(self::never())->method('createCategory');
        $repository->expects(self::never())->method('transactions');
        $ledger = new FinanceLedger($repository);
        try {
            $ledger->createCategory('alice', ['kind' => 'transfer', 'name' => 'Wrong']);
            self::fail('Invalid kind accepted');
        } catch (Problem $e) {
            self::assertSame('kind', $e->errors[0]['field']);
        }
        try {
            $ledger->transactions('alice', 2024, 13, null);
            self::fail('Invalid period accepted');
        } catch (Problem $e) {
            self::assertSame('period', $e->errors[0]['field']);
        }
    }

    public function testServiceEnforcesArchivedCategoryAndInUseDeletion(): void
    {
        $repository = $this->createMock(LedgerRepository::class);
        $repository->expects(self::exactly(2))->method('category')
            ->with('alice', 'category')->willReturn(['id' => 'category', 'archived' => 1]);
        $repository->expects(self::once())->method('categoryInUse')->with('alice', 'category')->willReturn(true);
        $repository->expects(self::never())->method('saveTransaction');
        $repository->expects(self::never())->method('deleteCategory');
        $ledger = new FinanceLedger($repository);
        try {
            $ledger->saveTransaction('alice', ['categoryId' => 'category', 'date' => '2024-01-01', 'amount' => '4'], null);
            self::fail('Archived category accepted');
        } catch (Problem $e) {
            self::assertSame(422, $e->status);
            self::assertSame('categoryId', $e->errors[0]['field']);
        }
        try {
            $ledger->deleteCategory('alice', 'category');
            self::fail('In-use category deleted');
        } catch (Problem $e) {
            self::assertSame(409, $e->status);
            self::assertSame('category_in_use', $e->problemCode);
        }
    }

    public function testValidatedTransactionIsPassedToRepository(): void
    {
        $repository = $this->createMock(LedgerRepository::class);
        $repository->expects(self::once())->method('category')->with('alice', 'category')
            ->willReturn(['id' => 'category', 'archived' => 0]);
        $repository->expects(self::once())->method('saveTransaction')->with('alice', null, [
            'category_id' => 'category', 'date' => '2024-02-29', 'amount' => '5.20', 'description' => 'Lunch',
        ])->willReturn(['id' => 'transaction', 'user_id' => 'alice']);
        $ledger = new FinanceLedger($repository);
        self::assertSame('transaction', $ledger->saveTransaction('alice', [
            'categoryId' => 'category', 'date' => '2024-02-29', 'amount' => '5.2', 'description' => ' Lunch ',
        ], null)['id']);
    }

    public function testInvalidDateAndAmountNeverReachPersistence(): void
    {
        $repository = $this->createMock(LedgerRepository::class);
        $repository->method('category')->willReturn(['id' => 'category', 'archived' => 0]);
        $repository->expects(self::never())->method('saveTransaction');
        $ledger = new FinanceLedger($repository);
        foreach ([
            ['date' => '2024-02-30', 'amount' => '5', 'field' => 'date'],
            ['date' => '2024-02-29', 'amount' => '-5', 'field' => 'amount'],
        ] as $data) {
            try {
                $ledger->saveTransaction('alice', ['categoryId' => 'category', ...$data], null);
                self::fail('Invalid transaction accepted');
            } catch (Problem $e) {
                self::assertSame(422, $e->status);
                self::assertSame($data['field'], $e->errors[0]['field']);
            }
        }
    }
}
