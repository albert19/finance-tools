<?php
namespace App\Tests;

use PHPUnit\Framework\TestCase;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Yaml\Yaml;

final class OpenApiContractTest extends TestCase
{
    public function testEveryDocumentedOperationMatchesAControllerRoute(): void
    {
        $document = Yaml::parseFile(__DIR__.'/../../contracts/openapi.yaml');
        self::assertSame('3.1.0', $document['openapi']);
        $documented = [];
        foreach ($document['paths'] as $path => $operations) {
            foreach (['get', 'post', 'put', 'patch', 'delete'] as $method) {
                if (isset($operations[$method])) {
                    $documented[] = strtoupper($method).' '.$path;
                }
            }
        }

        $routes = [];
        foreach (glob(__DIR__.'/../src/Controller/*Controller.php') as $file) {
            $class = 'App\\Controller\\'.basename($file, '.php');
            $reflection = new \ReflectionClass($class);
            foreach ($reflection->getMethods() as $method) {
                foreach ($method->getAttributes(Route::class) as $attribute) {
                    $route = $attribute->newInstance();
                    foreach ($route->methods as $httpMethod) {
                        $routes[] = $httpMethod.' '.$route->path;
                    }
                }
            }
        }
        sort($routes);
        sort($documented);
        self::assertSame($routes, $documented);

        $this->assertReferencesExist($document, $document);
    }

    private function assertReferencesExist(array $node, array $document): void
    {
        foreach ($node as $key => $value) {
            if ($key === '$ref') {
                self::assertIsString($value);
                self::assertStringStartsWith('#/', $value);
                $target = $document;
                foreach (explode('/', substr($value, 2)) as $segment) {
                    $segment = str_replace(['~1', '~0'], ['/', '~'], $segment);
                    self::assertArrayHasKey($segment, $target, $value);
                    $target = $target[$segment];
                }
            } elseif (is_array($value)) {
                $this->assertReferencesExist($value, $document);
            }
        }
    }
}
