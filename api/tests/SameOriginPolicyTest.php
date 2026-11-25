<?php
namespace App\Tests;

use App\Service\SameOriginPolicy;
use PHPUnit\Framework\TestCase;
use Symfony\Component\HttpFoundation\Request;

final class SameOriginPolicyTest extends TestCase
{
    public function testPreviewOriginMustBeExactLoopbackHttpWithValidPort(): void
    {
        $previous = getenv('LOCAL_PREVIEW_ORIGIN');
        $request = Request::create('http://127.0.0.1:8080/api/auth/login', 'POST', server: [
            'HTTP_ORIGIN' => 'http://127.0.0.1:43801',
        ]);
        try {
            $policy = new SameOriginPolicy();
            putenv('LOCAL_PREVIEW_ORIGIN=http://127.0.0.1:43801');
            self::assertTrue($policy->matches($request));
            foreach ([
                'http://127.0.0.1:43801/',
                'https://127.0.0.1:43801',
                'http://127.0.0.1:0',
                'http://127.0.0.1:65536',
                'http://evil.test:43801',
                '*',
            ] as $configured) {
                putenv('LOCAL_PREVIEW_ORIGIN='.$configured);
                self::assertFalse($policy->matches($request), $configured);
            }
            putenv('LOCAL_PREVIEW_ORIGIN=http://127.0.0.1:43801');
            foreach (['http://api.example:8000', 'https://127.0.0.1:8000'] as $host) {
                $request = Request::create($host.'/api/auth/login', 'POST', server: [
                    'HTTP_ORIGIN' => 'http://127.0.0.1:43801',
                ]);
                self::assertFalse($policy->matches($request), $host);
            }
        } finally {
            putenv($previous === false ? 'LOCAL_PREVIEW_ORIGIN' : 'LOCAL_PREVIEW_ORIGIN='.$previous);
        }
    }
}
