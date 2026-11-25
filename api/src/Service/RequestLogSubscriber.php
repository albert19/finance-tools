<?php
namespace App\Service;

use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\HttpKernel\Event\RequestEvent;
use Symfony\Component\HttpKernel\Event\ResponseEvent;
use Symfony\Component\HttpKernel\KernelEvents;

/** One allowlisted JSON record per main request, suitable for container log collection. */
final class RequestLogSubscriber implements EventSubscriberInterface
{
    public function __construct(private readonly string $stream = 'php://stderr') {}

    public static function getSubscribedEvents(): array
    {
        return [
            KernelEvents::REQUEST => ['onRequest', 200],
            KernelEvents::RESPONSE => ['onResponse', -128],
        ];
    }

    public function onRequest(RequestEvent $event): void
    {
        if (!$event->isMainRequest()) {
            return;
        }
        $request = $event->getRequest();
        if (in_array($request->getPathInfo(), ['/healthz', '/readyz'], true)) {
            return;
        }
        $request->attributes->set('_log_start', hrtime(true));
        // Never trust client-provided request IDs: they may contain secrets or log injection.
        $request->attributes->set('_log_id', bin2hex(random_bytes(16)));
    }

    public function onResponse(ResponseEvent $event): void
    {
        if (!$event->isMainRequest()) {
            return;
        }
        $request = $event->getRequest();
        $start = $request->attributes->get('_log_start');
        if (!is_int($start)) {
            return;
        }
        $route = $request->attributes->get('_route');
        // Route names are static; never log the raw URI (which may contain tokens).
        $record = [
            'request_id' => $request->attributes->get('_log_id'),
            'route' => is_string($route) && preg_match('/\A[a-zA-Z0-9_.-]{1,128}\z/D', $route) ? $route : '[unmatched]',
            'method' => in_array($request->getMethod(), ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'], true)
                ? $request->getMethod() : 'OTHER',
            'status' => $event->getResponse()->getStatusCode(),
            'duration_ms' => round(max(0, hrtime(true) - $start) / 1_000_000, 3),
        ];
        // Auth::user() does not place a verified identity on the Request. Do not
        // infer one from an unverified JWT, header, route parameter or query.
        $line = json_encode($record, JSON_THROW_ON_ERROR)."\n";
        $handle = @fopen($this->stream, 'ab');
        if ($handle !== false) {
            @fwrite($handle, $line);
            fclose($handle);
        }
    }
}
