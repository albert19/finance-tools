<?php
namespace App\Service;

use Symfony\Component\HttpFoundation\Request;

final class SameOriginPolicy
{
    public function matches(Request $request): bool
    {
        $origin = $request->headers->get('Origin');
        if (!$origin) {
            return false;
        }
        if ($origin === $request->getSchemeAndHttpHost()) {
            return true;
        }

        // Local browser previews can rewrite Host while retaining the browser's Origin.
        $preview = getenv('LOCAL_PREVIEW_ORIGIN') ?: '';
        if (!preg_match('~\Ahttp://(?:127\.0\.0\.1|localhost):([0-9]{1,5})\z~', $preview, $match)
            || (int) $match[1] < 1 || (int) $match[1] > 65535) {
            return false;
        }
        return $request->getScheme() === 'http'
            && in_array($request->getHost(), ['127.0.0.1', 'localhost'], true)
            && hash_equals($preview, $origin);
    }
}
