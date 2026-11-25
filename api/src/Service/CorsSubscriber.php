<?php
namespace App\Service;

use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Event\RequestEvent;
use Symfony\Component\HttpKernel\Event\ResponseEvent;
use Symfony\Component\HttpKernel\KernelEvents;

/**
 * CORS is exclusively for the bearer-token API. Cookie-based auth remains
 * same-origin and is never advertised to another origin.
 */
final class CorsSubscriber implements EventSubscriberInterface
{
    private const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
    private const HEADERS = ['authorization', 'content-type'];

    public function __construct(private SameOriginPolicy $originPolicy) {}

    public static function getSubscribedEvents(): array
    {
        return [
            KernelEvents::REQUEST => ['onRequest', 100],
            KernelEvents::RESPONSE => ['onResponse', -100],
        ];
    }

    public function onRequest(RequestEvent $event): void
    {
        if (!$event->isMainRequest()) {
            return;
        }
        $request = $event->getRequest();
        $path = $request->getPathInfo();
        $origin = $request->headers->get('Origin');
        if ($origin === null || !str_starts_with($path, '/api/')) {
            return;
        }
        // Exact origin, including scheme and port; never echo an arbitrary Origin.
        if ($this->originPolicy->matches($request)) {
            return;
        }
        if (str_starts_with($path, '/api/auth/') || !$this->allowed($origin)
            || $request->headers->has('Cookie')
            || (!$request->isMethod('OPTIONS') && !in_array($request->getMethod(), self::METHODS, true))) {
            $event->setResponse(new Response('', 403));
            return;
        }

        if ($request->isMethod('OPTIONS')) {
            $method = $request->headers->get('Access-Control-Request-Method', '');
            $requested = $request->headers->get('Access-Control-Request-Headers', '');
            $headers = $requested === '' ? [] : array_map('trim', explode(',', strtolower($requested)));
            if (!in_array($method, self::METHODS, true)
                || array_diff($headers, self::HEADERS) !== []
                || in_array('', $headers, true)) {
                $event->setResponse(new Response('', 403));
                return;
            }
            $response = new Response('', 204);
            $this->headers($response, $origin);
            $response->headers->set('Access-Control-Allow-Methods', implode(', ', self::METHODS));
            $response->headers->set('Access-Control-Allow-Headers', 'Authorization, Content-Type');
            $response->headers->set('Access-Control-Max-Age', '600');
            $response->setVary(['Origin', 'Access-Control-Request-Method', 'Access-Control-Request-Headers']);
            $event->setResponse($response);
            return;
        }
        $request->attributes->set('_cors_origin', $origin);
    }

    public function onResponse(ResponseEvent $event): void
    {
        if (!$event->isMainRequest()) {
            return;
        }
        $origin = $event->getRequest()->attributes->get('_cors_origin');
        if (is_string($origin)) {
            $this->headers($event->getResponse(), $origin);
            $event->getResponse()->setVary(['Origin'], false);
        }
    }

    private function headers(Response $response, string $origin): void
    {
        $response->headers->set('Access-Control-Allow-Origin', $origin);
        // No wildcard and no Access-Control-Allow-Credentials.
    }

    private function allowed(string $origin): bool
    {
        if (!$this->validOrigin($origin)) {
            return false;
        }
        foreach (explode(',', getenv('CORS_ALLOW_ORIGIN') ?: '') as $candidate) {
            $candidate = trim($candidate);
            if ($this->validOrigin($candidate) && hash_equals($candidate, $origin)) {
                return true;
            }
        }
        return false;
    }

    private function validOrigin(string $origin): bool
    {
        // An origin has no path, userinfo, query, fragment, wildcard or whitespace.
        if (!preg_match('~\Ahttps?://(?:[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*|\[[0-9a-fA-F:.]+\])(?::[0-9]{1,5})?\z~D', $origin)) {
            return false;
        }
        $port = parse_url($origin, PHP_URL_PORT);
        return $port === null || ($port > 0 && $port <= 65535);
    }
}
