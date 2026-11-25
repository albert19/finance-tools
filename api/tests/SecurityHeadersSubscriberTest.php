<?php
namespace App\Tests;

use App\Service\ApiErrorSubscriber;
use App\Service\Problem;
use App\Service\SecurityHeadersSubscriber;
use PHPUnit\Framework\TestCase;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpKernel\Event\ExceptionEvent;
use Symfony\Component\HttpKernel\Event\ResponseEvent;
use Symfony\Component\HttpKernel\Exception\MethodNotAllowedHttpException;
use Symfony\Component\HttpKernel\HttpKernelInterface;

final class SecurityHeadersSubscriberTest extends TestCase
{
    public function testApiResponsesAreNotSniffableFramableOrStorable(): void
    {
        $response = new JsonResponse(['balance' => '1.00']);
        $event = new ResponseEvent($this->createStub(HttpKernelInterface::class), Request::create('/api/transactions'),
            HttpKernelInterface::MAIN_REQUEST, $response);
        (new SecurityHeadersSubscriber())->onResponse($event);

        self::assertSame('nosniff', $response->headers->get('X-Content-Type-Options'));
        self::assertSame('DENY', $response->headers->get('X-Frame-Options'));
        self::assertSame("default-src 'none'; frame-ancestors 'none'", $response->headers->get('Content-Security-Policy'));
        self::assertSame('no-referrer', $response->headers->get('Referrer-Policy'));
        self::assertTrue($response->headers->hasCacheControlDirective('no-store'));
        self::assertFalse($response->headers->hasCacheControlDirective('public'));
    }

    public function testErrorsUseSpecificCodesAndProblemHeaders(): void
    {
        $kernel = $this->createStub(HttpKernelInterface::class);
        $subscriber = new ApiErrorSubscriber();

        $event = new ExceptionEvent($kernel, Request::create('/api/me'), HttpKernelInterface::MAIN_REQUEST,
            new MethodNotAllowedHttpException(['GET'], 'secret internal detail'));
        $subscriber->handle($event);
        $body = json_decode($event->getResponse()->getContent(), true);
        self::assertSame([405, 'method_not_allowed', 'Method not allowed'], [$body['status'], $body['code'], $body['title']]);

        $event = new ExceptionEvent($kernel, Request::create('/api/auth/login'), HttpKernelInterface::MAIN_REQUEST, Problem::throttled());
        $subscriber->handle($event);
        self::assertSame(429, $event->getResponse()->getStatusCode());
        self::assertSame('900', $event->getResponse()->headers->get('Retry-After'));

        $event = new ExceptionEvent($kernel, Request::create('/api/me'), HttpKernelInterface::MAIN_REQUEST, new \RuntimeException('db password'));
        $subscriber->handle($event);
        self::assertStringNotContainsString('db password', $event->getResponse()->getContent());
        self::assertSame(500, $event->getResponse()->getStatusCode());
    }
}
