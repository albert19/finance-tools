# AGENTS.md

- Finance manager is a React/TypeScript SPA in `webapp/` and a Symfony/PHP API
  in `api/`, backed by Doctrine and MySQL. There is no Python runtime package.
- Shared simulation vectors in `contracts/simulation-vectors/` preserve
  compatibility with the retired desktop engine. No Google Sheets import.
- Compose services and ports are in `compose.yaml`; copy `.env.example` to a
  private `.env` and keep all real secrets in gitignored `secrets/`.
- Do not deploy to production. Kubernetes readiness is an architectural goal,
  not an existing deployment or set of manifests.
- API endpoints require user-scoped authorization. Access JWT TTL defaults to
  120 seconds; refresh cookies rotate and require exact Origin + custom header.
  Never log credentials, bearer tokens or cookies.
- API controllers delegate to `src/Service` use cases; application services
  depend on `src/Port` repository interfaces and must not issue SQL. Doctrine
  DBAL/ORM adapters live in `src/Repository`. Finance entity mappings are in
  `src/Entity`; do not claim DBAL-backed routes use ORM.
- Run `docker compose config --quiet`; backend test stage:
  `docker build --target build -t finance-api-test ./api` then
  `docker run --rm -v "$PWD/contracts:/contracts:ro" finance-api-test vendor/bin/phpunit`.
- Frontend test/lint/build with Node 26 in Docker; bind repo root so shared
  simulation vectors under `contracts/simulation-vectors/` are available.
- Login/password-change throttling, Argon2id hashing and JWT `iss`/`aud`
  live in `src/Service/Auth.php` and `PasswordHasher.php`. Run `make audit`
  for dependency advisories; `make prune-auth` prunes auth tables.
- Keep English/Spanish translations synchronized. TypeScript `tsc` and ESLint
  should pass. Avoid adding dependencies less than 7 days old except an
  explicitly approved security release.
