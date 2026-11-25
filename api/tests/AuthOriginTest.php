<?php
namespace App\Tests;

use App\Service\Auth;
use App\Service\Problem;
use App\Service\SameOriginPolicy;
use App\Repository\DbalAuthRepository;
use Doctrine\DBAL\DriverManager;
use PHPUnit\Framework\TestCase;
use Symfony\Component\HttpFoundation\Request;

final class AuthOriginTest extends TestCase
{
    public function testCookieEndpointsRequireExactOriginIncludingPortAndAjaxHeader(): void
    {
        $auth = new Auth(new DbalAuthRepository(DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true])), new SameOriginPolicy());
        $request = Request::create('http://example.test:8080/api/auth/refresh', 'POST', server: [
            'HTTP_ORIGIN' => 'http://example.test:8080',
            'HTTP_X_REQUESTED_WITH' => 'XMLHttpRequest',
        ]);
        $auth->origin($request);
        foreach (['http://example.test:8081', 'https://example.test:8080', 'http://evil.test'] as $origin) {
            $request->headers->set('Origin', $origin);
            try {
                $auth->origin($request);
                self::fail('Accepted foreign origin '.$origin);
            } catch (Problem $e) { self::assertSame(403, $e->status); }
        }
        $request->headers->set('Origin', 'http://example.test:8080');
        $request->headers->remove('X-Requested-With');
        $this->expectException(Problem::class);
        $auth->origin($request);
    }

    public function testExplicitLoopbackPreviewStillRequiresAjaxHeaderAndExactOrigin(): void
    {
        $previous = getenv('LOCAL_PREVIEW_ORIGIN');
        putenv('LOCAL_PREVIEW_ORIGIN=http://127.0.0.1:43801');
        try {
            $auth = new Auth(new DbalAuthRepository(DriverManager::getConnection(['driver' => 'pdo_sqlite', 'memory' => true])), new SameOriginPolicy());
            $request = Request::create('http://127.0.0.1:8080/api/auth/login', 'POST', server: [
                'HTTP_ORIGIN' => 'http://127.0.0.1:43801',
                'HTTP_X_REQUESTED_WITH' => 'XMLHttpRequest',
            ]);
            $auth->origin($request);
            foreach (['http://127.0.0.1:43802', 'http://localhost:43801', 'https://127.0.0.1:43801'] as $origin) {
                $request->headers->set('Origin', $origin);
                try {
                    $auth->origin($request);
                    self::fail('Accepted foreign preview origin '.$origin);
                } catch (Problem $e) { self::assertSame(403, $e->status); }
            }
            $request->headers->set('Origin', 'http://127.0.0.1:43801');
            $request->headers->remove('X-Requested-With');
            try {
                $auth->origin($request);
                self::fail('Accepted preview request without AJAX header');
            } catch (Problem $e) { self::assertSame(403, $e->status); }
        } finally {
            putenv($previous === false ? 'LOCAL_PREVIEW_ORIGIN' : 'LOCAL_PREVIEW_ORIGIN='.$previous);
        }
    }
}
