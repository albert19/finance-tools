<?php
namespace App\Controller;

use App\Service\Auth;
use App\Service\Inputs;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Cookie;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Attribute\Route;

final class AuthController
{
    public function __construct(private Auth $auth) {}

    #[Route('/api/auth/login', methods: ['POST'])]
    public function login(Request $request): JsonResponse
    {
        $this->auth->origin($request);
        $data = Inputs::json($request);
        return $this->session($this->auth->login(Inputs::text($data, 'email', 254), Inputs::text($data, 'password', 1024), $request->getClientIp() ?? 'unknown'));
    }

    #[Route('/api/auth/refresh', methods: ['POST'])]
    public function refresh(Request $request): JsonResponse
    {
        $this->auth->origin($request);
        return $this->session($this->auth->refresh($request->cookies->get('refresh_token', '')));
    }

    #[Route('/api/auth/logout', methods: ['POST'])]
    public function logout(Request $request): JsonResponse
    {
        $this->auth->origin($request);
        $this->auth->logout($request->cookies->get('refresh_token', ''));
        $response = new JsonResponse(null, 204);
        $response->headers->clearCookie('refresh_token', '/api/auth', null, true, true, Cookie::SAMESITE_STRICT);
        return $response;
    }

    #[Route('/api/me', methods: ['GET'])]
    public function me(Request $request): JsonResponse { return new JsonResponse($this->auth->user($request)); }

    #[Route('/api/me', methods: ['PATCH'])]
    public function update(Request $request): JsonResponse
    {
        $user = $this->auth->user($request);
        $data = Inputs::json($request);
        return new JsonResponse($this->auth->updateLocale($user, $data));
    }

    #[Route('/api/me/password', methods: ['POST'])]
    public function password(Request $request): JsonResponse
    {
        $this->auth->changePassword($this->auth->user($request), Inputs::json($request));
        $response = new JsonResponse(null, 204);
        $response->headers->clearCookie('refresh_token', '/api/auth', null, true, true, Cookie::SAMESITE_STRICT);
        return $response;
    }

    private function session(array $result): JsonResponse
    {
        $response = new JsonResponse(['accessToken' => $result['accessToken'], 'expiresIn' => $result['expiresIn'], 'user' => $result['user']]);
        $response->headers->setCookie($this->auth->cookie($result['refresh'], $result['refreshTtl']));
        $response->headers->set('Cache-Control', 'no-store');
        return $response;
    }
}
