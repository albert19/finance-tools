<?php
namespace App\Controller;

use App\Service\Auth;
use App\Service\FinanceReports;
use App\Service\FinanceLedger;
use App\Service\BudgetService;
use App\Service\Inputs;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Attribute\Route;

final class FinanceController
{
    public function __construct(private Auth $auth, private BudgetService $budgets, private FinanceReports $reports, private FinanceLedger $ledger) {}

    private function uid(Request $r): string { return $this->auth->user($r)['id']; }
    private function data(Request $r): array { return Inputs::json($r); }
    private function json(mixed $value, int $status = 200): JsonResponse { return new JsonResponse($value, $status); }

    #[Route('/api/categories', methods: ['GET'])]
    public function categories(Request $r): JsonResponse
    {
        return $this->json($this->ledger->categories($this->uid($r), $r->query->get('includeArchived') !== 'false'));
    }

    #[Route('/api/categories', methods: ['POST'])]
    public function createCategory(Request $r): JsonResponse
    {
        return $this->json($this->ledger->createCategory($this->uid($r), $this->data($r)), 201);
    }

    #[Route('/api/categories/defaults', methods: ['POST'])]
    public function defaults(Request $r): JsonResponse
    {
        return $this->json($this->ledger->defaults($this->uid($r)), 201);
    }

    #[Route('/api/categories/{id}', methods: ['PATCH'])]
    public function updateCategory(Request $r, string $id): JsonResponse
    {
        return $this->json($this->ledger->updateCategory($this->uid($r), $id, $this->data($r)));
    }

    #[Route('/api/categories/{id}', methods: ['DELETE'])]
    public function deleteCategory(Request $r, string $id): JsonResponse
    {
        $this->ledger->deleteCategory($this->uid($r), $id);
        return $this->json(null, 204);
    }

    #[Route('/api/budgets', methods: ['GET'])]
    public function budgets(Request $r): JsonResponse
    {
        return $this->json($this->budgets->list($this->uid($r), $r->query->get('year')));
    }

    #[Route('/api/budgets/{year}/{month}', methods: ['GET'], requirements: ['year' => '\d+', 'month' => '\d+'])]
    public function budgetPeriod(Request $r, int $year, int $month): JsonResponse
    {
        return $this->json($this->budgets->period($this->uid($r), $year, $month));
    }

    #[Route('/api/budgets', methods: ['POST'])]
    public function createBudget(Request $r): JsonResponse
    {
        return $this->json($this->budgets->create($this->uid($r), $this->data($r)), 201);
    }

    #[Route('/api/budgets/{id}', methods: ['PATCH'])]
    public function updateBudget(Request $r, string $id): JsonResponse
    {
        return $this->json($this->budgets->update($this->uid($r), $id, $this->data($r)));
    }

    #[Route('/api/budgets/{id}', methods: ['DELETE'])]
    public function deleteBudget(Request $r, string $id): JsonResponse
    {
        $this->budgets->delete($this->uid($r), $id);
        return $this->json(null, 204);
    }

    #[Route('/api/budgets/{id}/lines', methods: ['POST'])]
    public function addLine(Request $r, string $id): JsonResponse
    {
        return $this->saveLine($r, $id, null);
    }

    #[Route('/api/budgets/{id}/lines/{lineId}', methods: ['PUT'])]
    public function putLine(Request $r, string $id, string $lineId): JsonResponse
    {
        return $this->saveLine($r, $id, $lineId);
    }

    private function saveLine(Request $r, string $id, ?string $lineId): JsonResponse
    {
        return $this->json($this->budgets->saveLine($this->uid($r), $id, $lineId, $this->data($r)), $r->isMethod('PUT') ? 200 : 201);
    }

    #[Route('/api/budgets/{id}/lines/{lineId}', methods: ['DELETE'])]
    public function deleteLine(Request $r, string $id, string $lineId): JsonResponse
    {
        $this->budgets->deleteLine($this->uid($r), $id, $lineId, $this->data($r));
        return $this->json(null, 204);
    }

    #[Route('/api/transactions', methods: ['GET'])]
    public function transactions(Request $r): JsonResponse
    {
        return $this->json($this->ledger->transactions($this->uid($r), $r->query->get('year'), $r->query->get('month'), $r->query->get('kind')));
    }

    #[Route('/api/transactions', methods: ['POST'])]
    public function createTransaction(Request $r): JsonResponse { return $this->saveTransaction($r, null); }

    #[Route('/api/transactions/{id}', methods: ['PUT'])]
    public function putTransaction(Request $r, string $id): JsonResponse { return $this->saveTransaction($r, $id); }

    private function saveTransaction(Request $r, ?string $id): JsonResponse
    {
        return $this->json($this->ledger->saveTransaction($this->uid($r), $this->data($r), $id), $r->isMethod('PUT') ? 200 : 201);
    }

    #[Route('/api/transactions/{id}', methods: ['DELETE'])]
    public function deleteTransaction(Request $r, string $id): JsonResponse
    {
        $this->ledger->deleteTransaction($this->uid($r), $id);
        return $this->json(null, 204);
    }

    #[Route('/api/reports/monthly/{year}/{month}', methods: ['GET'], requirements: ['year' => '\d+', 'month' => '\d+'])]
    public function reportMonth(Request $r, int $year, int $month): JsonResponse
    {
        return $this->json($this->reports->monthly($this->uid($r), $year, $month));
    }

    #[Route('/api/reports/annual/{year}', methods: ['GET'], requirements: ['year' => '\d+'])]
    public function reportYear(Request $r, int $year): JsonResponse
    {
        return $this->json($this->reports->annual($this->uid($r), $year));
    }
}
