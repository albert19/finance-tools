<?php
namespace App\Tests;

use App\Service\RequestLogSubscriber;
use PHPUnit\Framework\TestCase;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Event\RequestEvent;
use Symfony\Component\HttpKernel\Event\ResponseEvent;
use Symfony\Component\HttpKernel\HttpKernelInterface;

final class RequestLogSubscriberTest extends TestCase
{
    public function testOnlyAllowlistedFieldsAreLoggedAndUnknownPathsAreNotLeaked(): void
    {
        $file = tempnam(sys_get_temp_dir(), 'finance-log-');
        try {
            $subscriber = new RequestLogSubscriber($file);
            $kernel = $this->createStub(HttpKernelInterface::class);
            $request = Request::create('/api/me?token=query-secret&password=query-secret', 'PATCH', server: [
                'HTTP_AUTHORIZATION' => 'Bearer header-secret',
                'HTTP_COOKIE' => 'refresh_token=cookie-secret',
                'HTTP_X_REQUEST_ID' => 'injected-secret',
            ], content: '{"password":"body-secret"}');
            $request->attributes->set('_route', 'app_me_update');
            $request->attributes->set('user_id', 'unverified-secret');
            $subscriber->onRequest(new RequestEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST));
            $subscriber->onResponse(new ResponseEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST, new Response('', 422)));

            $unknown = Request::create('/api/token/path-secret?password=query-secret', 'GET');
            $subscriber->onRequest(new RequestEvent($kernel, $unknown, HttpKernelInterface::MAIN_REQUEST));
            $subscriber->onResponse(new ResponseEvent($kernel, $unknown, HttpKernelInterface::MAIN_REQUEST, new Response('', 404)));

            $raw = file_get_contents($file);
            foreach (['query-secret', 'header-secret', 'cookie-secret', 'body-secret', 'injected-secret', 'path-secret', 'unverified-secret'] as $secret) {
                self::assertStringNotContainsString($secret, $raw);
            }
            $lines = array_filter(explode("\n", trim($raw)));
            self::assertCount(2, $lines);
            [$first, $second] = array_map(fn ($line) => json_decode($line, true, 512, JSON_THROW_ON_ERROR), $lines);
            self::assertSame(['request_id', 'route', 'method', 'status', 'duration_ms'], array_keys($first));
            self::assertMatchesRegularExpression('/\A[a-f0-9]{32}\z/', $first['request_id']);
            self::assertSame('app_me_update', $first['route']);
            self::assertSame('PATCH', $first['method']);
            self::assertSame(422, $first['status']);
            self::assertGreaterThanOrEqual(0, $first['duration_ms']);
            self::assertSame('[unmatched]', $second['route']);
            self::assertNotSame($first['request_id'], $second['request_id']);
        } finally {
            unlink($file);
        }
    }

    public function testHealthProbesAndSubrequestsAreNotLogged(): void
    {
        $file = tempnam(sys_get_temp_dir(), 'finance-log-');
        try {
            $subscriber = new RequestLogSubscriber($file);
            $kernel = $this->createStub(HttpKernelInterface::class);
            foreach (['/healthz', '/readyz'] as $path) {
                $request = Request::create($path);
                $subscriber->onRequest(new RequestEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST));
                $subscriber->onResponse(new ResponseEvent($kernel, $request, HttpKernelInterface::MAIN_REQUEST, new Response()));
            }
            $request = Request::create('/api/me');
            $subscriber->onRequest(new RequestEvent($kernel, $request, HttpKernelInterface::SUB_REQUEST));
            $subscriber->onResponse(new ResponseEvent($kernel, $request, HttpKernelInterface::SUB_REQUEST, new Response()));
            self::assertSame('', file_get_contents($file));
        } finally {
            unlink($file);
        }
    }
}
