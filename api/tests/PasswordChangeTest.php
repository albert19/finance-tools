<?php
namespace App\Tests;

use App\Port\AuthRepository;
use App\Service\Auth;
use App\Service\Problem;
use App\Service\SameOriginPolicy;
use PHPUnit\Framework\TestCase;

final class PasswordChangeTest extends TestCase
{
    public function testPasswordChangeRequiresCurrentPasswordAndRevokesSessions(): void
    {
        $repository = $this->createMock(AuthRepository::class);
        $repository->method('recordAttempt')->willReturn(1);
        $repository->expects($this->once())->method('changePassword')
            ->with('user', 'current-password', $this->callback(
                static fn (string $hash): bool => password_get_info($hash)['algo'] === PASSWORD_ARGON2ID
                    && password_verify('different-long-password', $hash)))
            ->willReturn(true);
        $repository->expects($this->once())->method('clearAttempts')->with(hash('sha256', 'pwchange|user'));
        $auth = new Auth($repository, new SameOriginPolicy());
        $auth->changePassword(['id' => 'user'], ['currentPassword' => 'current-password', 'newPassword' => 'different-long-password']);
    }

    public function testWrongCurrentPasswordIsForbiddenNotUnauthorized(): void
    {
        // 401 would make the SPA treat the bearer token as expired, refresh and retry.
        $repository = $this->createMock(AuthRepository::class);
        $repository->method('recordAttempt')->willReturn(1);
        $repository->expects($this->once())->method('changePassword')->willReturn(false);
        $repository->expects($this->never())->method('clearAttempts');
        $auth = new Auth($repository, new SameOriginPolicy());
        try {
            $auth->changePassword(['id' => 'user'], ['currentPassword' => 'wrong-password', 'newPassword' => 'different-long-password']);
            self::fail('Accepted an incorrect current password');
        } catch (Problem $e) {
            self::assertSame(403, $e->status);
            self::assertSame('invalid_credentials', $e->problemCode);
        }
    }

    public function testRepeatedGuessesAreThrottledBeforeVerification(): void
    {
        $repository = $this->createMock(AuthRepository::class);
        $repository->expects($this->once())->method('recordAttempt')->with(hash('sha256', 'pwchange|user'))->willReturn(6);
        $repository->expects($this->never())->method('changePassword');
        $auth = new Auth($repository, new SameOriginPolicy());
        try {
            $auth->changePassword(['id' => 'user'], ['currentPassword' => 'guess-password', 'newPassword' => 'different-long-password']);
            self::fail('Did not throttle');
        } catch (Problem $e) {
            self::assertSame(429, $e->status);
            self::assertSame(['Retry-After' => '900'], $e->headers);
        }
    }

    public function testNewPasswordPolicy(): void
    {
        $repository = $this->createMock(AuthRepository::class);
        $repository->expects($this->never())->method('changePassword');
        $auth = new Auth($repository, new SameOriginPolicy());
        foreach (['short', 'has internal space', str_repeat('a', 1025)] as $next) {
            try {
                $auth->changePassword(['id' => 'user'], ['currentPassword' => 'current-password', 'newPassword' => $next]);
                self::fail('Accepted weak password');
            } catch (Problem $e) {
                self::assertSame(422, $e->status);
            }
        }
    }
}
