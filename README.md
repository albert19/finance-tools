# Finance manager

A React single-page app and PHP API for investment projections, a portfolio,
monthly budgets, categories and manual income/expense entries. MySQL is the
persistent store; Elasticsearch, Logstash, Kibana and Filebeat form an optional
local observability stack. The legacy PySide6/Google Sheets source and tests
have been removed. Existing Sheets data is not imported into MySQL; the
spreadsheets remain untouched. **No production deployment has been made.**

## Start locally

Requires Docker Engine + Compose, GNU Make and OpenSSL. From the project root:

```bash
make local-start EMAIL=you@example.com
```

This creates private `.env` and secret files if missing, configures MySQL,
generates JWT keys, runs migrations and creates the first admin. It then starts
the webapp and prints an access guide. Existing secrets, database rows, and
admin passwords are not replaced. On later runs, `make local-start` needs no
email. If Make is unavailable, use
`EMAIL=you@example.com bash ops/local.sh start` instead. To see URLs and login
details at any time, run `make access` (or `bash ops/local.sh access`).

For optional Elasticsearch, Logstash, Kibana, and Filebeat (at least 4 GB
additional RAM), run `make local-start OBSERVABILITY=1`. This also selects
Elastic's same-version Docker Hub images when its registry is unavailable.

**Where to log in:**

| Tool | Address / access | Username | Password |
| --- | --- | --- | --- |
| Finance manager | `http://127.0.0.1:8080/` | Your admin email | `secrets/seed_admin_password` |
| Kibana (optional) | `http://127.0.0.1:5601/` | `elastic` | `secrets/elastic_password` |
| MySQL (local) | `make db-shell` (no web UI) | `finance` | Supplied by the container secret |
| API, Elasticsearch, Logstash, Filebeat | No separate browser login | - | - |

`make access` displays configured ports, the admin email and password-file
paths without printing passwords. To read a password for manual browser login,
run `cat secrets/seed_admin_password` or `cat secrets/elastic_password` in your
private terminal; never paste the output into chat or logs. The
`secrets/kibana_password` file is only for Kibana's internal service account.
The first admin is created once by `app:seed`; rerunning setup never changes
its stored password. If you need to choose a new admin password, run
`make admin-reset-password` (hidden prompt, minimum 12 characters). It revokes
refresh tokens and updates the local admin password file after a successful
reset. For another account, use `make user-reset-password EMAIL=user@example.com`
or `make user-create EMAIL=user@example.com` (see `api/README.md`).
Changing the password in the webapp also revokes refresh sessions, but it
cannot update `secrets/seed_admin_password` on the host. Sign in with the new
password thereafter; use `make admin-reset-password` if you need the local file
to match again.

Local `.env` and `secrets/` are ignored by Git; do not commit them. Password
files are plaintext inputs, while account passwords are hashed in MySQL.

## Advanced configuration

`make local-setup EMAIL=you@example.com` prepares local configuration without
starting containers. For an external MySQL database, configure `.env` manually
from `.env.example`, use a private `DATABASE_URL`, generate secrets with
`bash ops/local.sh secrets` and `bash ops/local.sh jwt-keys`, then run
`make up` (or `docker compose up -d --build`).

`WEBAPP_PORT`, `API_PORT`, `MYSQL_PORT` and all ELK host ports are configured
in `.env`. If port 3306 is occupied, set `MYSQL_PORT=3307`; keep
`DATABASE_URL` pointed at `dbapp:3306` inside Compose. For an external MySQL
server, set `DATABASE_URL` to its private connection string and leave
`COMPOSE_PROFILES` empty; do not start `dbapp`. Local DB is enabled by
`COMPOSE_PROFILES=localdb`. `docker compose down` stops the stack without
removing database volumes. Do **not** run `docker compose down -v` unless you
intend to erase local data.

If a local browser preview opens a different loopback port and login returns
403 despite valid credentials, its proxy may rewrite `Host` while preserving
the browser's `Origin`. Set `LOCAL_PREVIEW_ORIGIN` in the private `.env` to the
exact preview URL (for example `http://127.0.0.1:43801`), then run
`docker compose up -d --no-deps --build api`. This exception only accepts
loopback HTTP preview origins with a loopback API host; never set it in
production. The normal `http://127.0.0.1:8080` route needs no exception.

ELK host ports bind to localhost through a dedicated ingress network. Local
Elasticsearch requires Linux `vm.max_map_count >= 262144`. Filebeat uses a
local Docker socket mount; Kubernetes should use a DaemonSet instead. The
core API/SPA/MySQL stack does not depend on ELK.

## Architecture and security

- `webapp/`: React + TypeScript/Vite SPA. The banknote-inspired UI has EN/ES
  localization. The simulator calculates immediately in the browser; the API
  recalculates on save. Both engines are checked against preserved reference
  outputs in `contracts/simulation-vectors/`.
- `api/`: Symfony 8.1 on PHP 8.5. Controllers delegate to application services
  that depend on repository ports; Doctrine DBAL/ORM adapters own data access.
  Each table has its own creation migration in foreign-key order. This is an
  incremental port, not a fully isolated DDD model; see `api/README.md`.
- `compose.yaml`: API, webapp, migration job, optional MySQL and separately
  deployed Elasticsearch, Logstash, Kibana, Filebeat services. Secrets are
  mounted from ignored local files, never embedded in images.
- Access JWT TTL defaults to 120 seconds (`JWT_TTL`); refresh tokens rotate
  and are stored hashed in MySQL. The refresh cookie is Secure, HttpOnly and
  SameSite=Strict. Serve the SPA and `/api` from one HTTPS origin outside
  localhost; browser access tokens stay in memory.
- Login is throttled per 15 minutes: 30 attempts per client IP, 5 per email
  and IP, and a 100-per-email ceiling (429 with `Retry-After`). Password
  changes allow 5 attempts per user. The API trusts `X-Forwarded-For` only
  from `TRUSTED_PROXIES` (compose default `private_ranges`, i.e. the webapp
  nginx); set the exact ingress CIDR in production. `TRUSTED_HOSTS` optionally
  restricts the `Host` header. Passwords are hashed with Argon2id; older
  bcrypt hashes are upgraded on the next login.
- `app:auth:prune` (run by the migrate job, or `make prune-auth`) deletes
  expired refresh tokens and stale throttle rows; schedule it daily (cron or a
  Kubernetes CronJob) on long-running deployments.
- The API image runs as a non-root user whose UID (`APP_UID`, set by local
  setup to `id -u`) must own the mode-600 files in `secrets/`. `make audit`
  checks locked PHP and production npm dependencies for advisories.
- `contracts/openapi.yaml` documents the implemented `/api/*` routes and their
  request/response schemas. Cross-origin bearer-only access is opt-in via
  `CORS_ALLOW_ORIGIN`; cookie-based auth remains same-origin.

## Verification

```bash
docker compose config --quiet
# Backend unit/golden tests: build the test stage; production image omits tests.
docker build --target build -t finance-api-test ./api
docker run --rm -v "$PWD/contracts:/contracts:ro" finance-api-test vendor/bin/phpunit
# Frontend unit/golden tests (bind the repo root so vectors are available).
docker run --rm -v "$PWD:/workspace" -w /workspace/webapp node:26.13.1-bookworm-slim sh -ec 'npm ci && npm test && npm run lint && npm run build'
```

`make test`/`make lint` provide wrappers where Make is installed. For optional
disposable development fixtures, see `api/README.md`; they are not seeded by
default and are refused when `APP_ENV=prod`.
With the local stack running, `make e2e E2E_EMAIL=your-admin@example.test
E2E_PASSWORD_FILE=secrets/seed_admin_password` runs a Chromium login/navigation
smoke test in a pinned Playwright image (Linux Docker host networking). The
test reads the password file without printing it and makes no finance writes.

## Kubernetes readiness (not deployed)

The images separate webapp and API, use environment-based config, expose
`/healthz` and `/readyz`, and provide an idempotent migration command for a
pre-deployment Job. Use an external managed MySQL, mounted secrets, TLS at the
Ingress (`/api` to API, `/` to webapp), and a Filebeat DaemonSet with ECK for
Elastic. No Helm chart, manifests or production cluster deployment is included.
Before any public deployment, set `TRUSTED_PROXIES` to the ingress CIDR,
configure `TRUSTED_HOSTS`, use `fsGroup`/`defaultMode` so the non-root API
can read mounted secrets, and review secret management and load limits.

> Investment results are simulations, not financial advice. Past performance
> does not guarantee future returns.
