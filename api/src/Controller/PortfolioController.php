<?php
namespace App\Controller;

use App\Service\Auth;
use App\Service\Inputs;
use App\Service\PortfolioService;
use App\Service\Simulator;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Attribute\Route;

final class PortfolioController
{
    public function __construct(private Auth $auth, private PortfolioService $portfolio, private Simulator $simulator) {}
    private function uid(Request $r): string { return $this->auth->user($r)['id']; }

    #[Route('/api/simulations', methods: ['POST'])]
    public function simulate(Request $r): JsonResponse
    {
        $this->uid($r);
        return new JsonResponse($this->simulator->run(Inputs::json($r)));
    }

    #[Route('/api/simulations/scenarios', methods: ['POST'])]
    public function scenarios(Request $r): JsonResponse
    {
        $this->uid($r); $p = Inputs::json($r);
        $base = $this->simulator->run($p);
        return new JsonResponse(['pessimistic' => $this->simulator->run([...$p, 'annualRate' => max(-50, $base['parameters']['annualRate'] - 2)]),
            'base' => $base, 'optimistic' => $this->simulator->run([...$p, 'annualRate' => min(100, $base['parameters']['annualRate'] + 2)])]);
    }

    #[Route('/api/investments', methods: ['GET'])]
    public function list(Request $r): JsonResponse
    {
        return new JsonResponse($this->portfolio->list($this->uid($r)));
    }

    #[Route('/api/investments', methods: ['POST'])]
    public function create(Request $r): JsonResponse
    {
        return new JsonResponse($this->portfolio->create($this->uid($r), Inputs::json($r)), 201);
    }

    #[Route('/api/investments/{id}', methods: ['GET'])]
    public function detail(Request $r, string $id): JsonResponse
    {
        return new JsonResponse($this->portfolio->detail($this->uid($r), $id));
    }

    #[Route('/api/investments/{id}/comparison', methods: ['GET'])]
    public function comparison(Request $r, string $id): JsonResponse
    {
        return new JsonResponse($this->portfolio->compare($this->uid($r), $id));
    }

    #[Route('/api/investments/{id}', methods: ['PATCH'])]
    public function update(Request $r, string $id): JsonResponse
    {
        return new JsonResponse($this->portfolio->update($this->uid($r), $id, Inputs::json($r)));
    }

    #[Route('/api/investments/{id}', methods: ['DELETE'])]
    public function delete(Request $r, string $id): JsonResponse
    {
        $this->portfolio->delete($this->uid($r), $id);
        return new JsonResponse(null, 204);
    }

    #[Route('/api/investments/{id}/snapshots', methods: ['POST'])]
    public function snapshot(Request $r, string $id): JsonResponse
    {
        return new JsonResponse(['id' => $this->portfolio->snapshot($this->uid($r), $id, Inputs::json($r))], 201);
    }

    #[Route('/api/investments/{id}/snapshots/{snapshotId}', methods: ['DELETE'])]
    public function deleteSnapshot(Request $r, string $id, string $snapshotId): JsonResponse
    {
        $this->portfolio->deleteSnapshot($this->uid($r), $id, $snapshotId);
        return new JsonResponse(null, 204);
    }
}
