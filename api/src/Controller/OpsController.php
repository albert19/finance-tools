<?php
namespace App\Controller;

use App\Port\HealthRepository;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\Routing\Attribute\Route;

final class OpsController
{
    #[Route('/healthz', methods: ['GET'])]
    public function health(): JsonResponse { return new JsonResponse(['status' => 'ok']); }

    #[Route('/readyz', methods: ['GET'])]
    public function ready(HealthRepository $db): JsonResponse
    {
        return $db->ping()
            ? new JsonResponse(['status' => 'ready'])
            : new JsonResponse(['status' => 'unavailable'], 503);
    }
}
