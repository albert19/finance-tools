<?php
namespace App\Tests;

use App\Service\CorsSubscriber;
use App\Service\SameOriginPolicy;
use PHPUnit\Framework\TestCase;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Event\RequestEvent;
use Symfony\Component\HttpKernel\Event\ResponseEvent;
use Symfony\Component\HttpKernel\HttpKernelInterface;

final class CorsSubscriberTest extends TestCase
{
    private string|false $previous;

    protected function setUp(): void
    {
        $this->previous = getenv('CORS_ALLOW_ORIGIN');
        putenv('CORS_ALLOW_ORIGIN=https://app.example:8443, https://other.example');
    }

    protected function tearDown(): void
    {
        putenv($this->previous === false ? 'CORS_ALLOW_ORIGIN' : 'CORS_ALLOW_ORIGIN='.$this->previous);
    }

    private function events(string $path, string $method, array $server = []): array
    {
        $kernel = $this->createStub(HttpKernelInterface::class);
        $request = Request::create('https://api.example'.$path, $method, server: $server);
        return [
            new RequestEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST),
            $kernel,
            $request,
        ];
    }

    public function testAllowedPreflightAndBearerResponseIncludingError(): void
    {
        $subscriber = new CorsSubscriber(new SameOriginPolicy());
        [$event, $kernel, $request] = $this->events('/api/me?password=secret', 'OPTIONS', [
            'HTTP_ORIGIN' => 'https://app.example:8443',
            'HTTP_ACCESS_CONTROL_REQUEST_METHOD' => 'PATCH',
            'HTTP_ACCESS_CONTROL_REQUEST_HEADERS' => 'authorization, content-type',
        ]);
        $subscriber->onRequest($event);
        self::assertTrue($event->hasResponse());
        $preflight = $event->getResponse();
        self::assertSame(204, $preflight->getStatusCode());
        self::assertSame('https://app.example:8443', $preflight->headers->get('Access-Control-Allow-Origin'));
        self::assertStringContainsString('PATCH', $preflight->headers->get('Access-Control-Allow-Methods'));
        self::assertSame('Authorization, Content-Type', $preflight->headers->get('Access-Control-Allow-Headers'));
        self::assertFalse($preflight->headers->has('Access-Control-Allow-Credentials'));

        [$event, $kernel, $request] = $this->events('/api/v1/me?token=secret', 'GET', [
            'HTTP_ORIGIN' => 'https://other.example',
            'HTTP_AUTHORIZATION' => 'Bearer secret',
        ]);
        $subscriber->onRequest($event);
        self::assertFalse($event->hasResponse());
        $response = new Response('unauthorized', 401);
        $subscriber->onResponse(new ResponseEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST, $response));
        self::assertSame('https://other.example', $response->headers->get('Access-Control-Allow-Origin'));
        self::assertContains('Origin', $response->getVary());
        self::assertFalse($response->headers->has('Access-Control-Allow-Credentials'));
    }

    public function testDeniedOriginsAuthAndCookieRequestsCannotUseCors(): void
    {
        $subscriber = new CorsSubscriber(new SameOriginPolicy());
        foreach ([
            ['https://evil.example', '/api/me', []],
            ['https://app.example', '/api/me', []], // port is part of origin
            ['https://app.example:8443', '/api/auth/login', []],
            ['https://app.example:8443', '/api/auth/refresh', []],
            ['https://app.example:8443', '/api/me', ['HTTP_COOKIE' => 'refresh_token=secret']],
        ] as [$origin, $path, $extra]) {
            [$event, $kernel, $request] = $this->events($path, 'POST', ['HTTP_ORIGIN' => $origin, ...$extra]);
            $subscriber->onRequest($event);
            self::assertSame(403, $event->getResponse()->getStatusCode(), $path);
            $subscriber->onResponse(new ResponseEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST, $event->getResponse()));
            self::assertFalse($event->getResponse()->headers->has('Access-Control-Allow-Origin'));
        }
        putenv('CORS_ALLOW_ORIGIN=*');
        [$event] = $this->events('/api/me', 'GET', ['HTTP_ORIGIN' => 'https://evil.example']);
        $subscriber->onRequest($event);
        self::assertSame(403, $event->getResponse()->getStatusCode());
        putenv('CORS_ALLOW_ORIGIN');
        [$event] = $this->events('/api/me', 'GET', ['HTTP_ORIGIN' => 'https://other.example']);
        $subscriber->onRequest($event);
        self::assertSame(403, $event->getResponse()->getStatusCode());
        putenv('CORS_ALLOW_ORIGIN=https://other.example/path');
        [$event] = $this->events('/api/me', 'GET', ['HTTP_ORIGIN' => 'https://other.example/path']);
        $subscriber->onRequest($event);
        self::assertSame(403, $event->getResponse()->getStatusCode());
    }

    public function testInvalidPreflightIsRejectedAndSameOriginIsUntouched(): void
    {
        $subscriber = new CorsSubscriber(new SameOriginPolicy());
        foreach ([
            ['DELETE', 'cookie'],
            ['TRACE', 'authorization'],
            ['', 'authorization'],
        ] as [$method, $headers]) {
            [$event] = $this->events('/api/me', 'OPTIONS', [
                'HTTP_ORIGIN' => 'https://other.example',
                'HTTP_ACCESS_CONTROL_REQUEST_METHOD' => $method,
                'HTTP_ACCESS_CONTROL_REQUEST_HEADERS' => $headers,
            ]);
            $subscriber->onRequest($event);
            self::assertSame(403, $event->getResponse()->getStatusCode());
        }
        [$event, $kernel, $request] = $this->events('/api/me', 'GET', ['HTTP_ORIGIN' => 'https://api.example']);
        $subscriber->onRequest($event);
        $response = new Response();
        $subscriber->onResponse(new ResponseEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST, $response));
        self::assertFalse($response->headers->has('Access-Control-Allow-Origin'));
        [$event] = $this->events('/healthz', 'OPTIONS', ['HTTP_ORIGIN' => 'https://other.example']);
        $subscriber->onRequest($event);
        self::assertFalse($event->hasResponse());
    }

    public function testExplicitLocalPreviewDoesNotEnableCredentialedCors(): void
    {
        $previous = getenv('LOCAL_PREVIEW_ORIGIN');
        putenv('LOCAL_PREVIEW_ORIGIN=http://127.0.0.1:43801');
        try {
            $subscriber = new CorsSubscriber(new SameOriginPolicy());
            $kernel = $this->createStub(HttpKernelInterface::class);
            $request = Request::create('http://127.0.0.1:8080/api/auth/login', 'POST', server: [
                'HTTP_ORIGIN' => 'http://127.0.0.1:43801',
                'HTTP_COOKIE' => 'refresh_token=placeholder',
            ]);
            $event = new RequestEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST);
            $subscriber->onRequest($event);
            self::assertFalse($event->hasResponse());
            $response = new Response();
            $subscriber->onResponse(new ResponseEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST, $response));
            self::assertFalse($response->headers->has('Access-Control-Allow-Origin'));
            self::assertFalse($response->headers->has('Access-Control-Allow-Credentials'));

            $request->headers->set('Origin', 'http://127.0.0.1:43802');
            $event = new RequestEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST);
            $subscriber->onRequest($event);
            self::assertSame(403, $event->getResponse()->getStatusCode());
        } finally {
            putenv($previous === false ? 'LOCAL_PREVIEW_ORIGIN' : 'LOCAL_PREVIEW_ORIGIN='.$previous);
        }
    }
}
