<?php
namespace App\Service;

use Doctrine\DBAL\Exception\UniqueConstraintViolationException;
use Doctrine\DBAL\Exception\ForeignKeyConstraintViolationException;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpKernel\Event\ExceptionEvent;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;
use Symfony\Component\HttpKernel\KernelEvents;

final class ApiErrorSubscriber implements EventSubscriberInterface
{
    private const CODES = [400 => ['bad_request', 'Bad request'], 404 => ['not_found', 'Not found'], 405 => ['method_not_allowed', 'Method not allowed']];

    public static function getSubscribedEvents(): array { return [KernelEvents::EXCEPTION => 'handle']; }

    public function handle(ExceptionEvent $event): void
    {
        $e = $event->getThrowable();
        if ($e instanceof UniqueConstraintViolationException) { $e = new Problem(409, 'conflict', 'Resource already exists'); }
        if ($e instanceof ForeignKeyConstraintViolationException) { $e = new Problem(409, 'resource_in_use', 'Resource is in use'); }
        if (!$e instanceof Problem) {
            $status = $e instanceof HttpExceptionInterface ? $e->getStatusCode() : 500;
            // Never expose exception messages; only well-known client errors get a specific code.
            [$code, $title] = self::CODES[$status] ?? ['internal_error', 'Internal server error'];
            $e = new Problem($status, $code, $title);
        }
        $event->setResponse(new JsonResponse([
            'type' => 'about:blank', 'title' => $e->getMessage(), 'status' => $e->status,
            'code' => $e->problemCode, 'errors' => $e->errors,
        ], $e->status, ['Content-Type' => 'application/problem+json', ...$e->headers]));
    }
}
