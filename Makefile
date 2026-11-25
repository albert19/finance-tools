COMPOSE := docker compose -f compose.yaml
NODE := docker run --rm -v "$(CURDIR):/workspace" -w /workspace/webapp node:26.13.1-bookworm-slim

.PHONY: local-setup local-start access db-shell admin-reset-password up down logs migrate seed fixtures user-create user-reset-password prune-auth jwt-keys secrets test lint audit e2e config

# One-command local setup. OBSERVABILITY=1 also enables ELK.
local-setup:
	@bash ops/local.sh setup

local-start:
	@bash ops/local.sh start

access:
	@bash ops/local.sh access

db-shell:
	$(COMPOSE) exec dbapp sh -c 'MYSQL_PWD="$$(cat /run/secrets/mysql_password)" exec mysql -u finance finance'

admin-reset-password:
	@bash ops/local.sh reset-admin-password

# Start every service enabled by COMPOSE_PROFILES; wait for health checks and setup jobs.
# For an external MySQL server, configure DATABASE_URL in .env and use make up.
up:
	@test -f .env || (echo "Run make local-start EMAIL=you@example.com first" >&2; exit 1)
	$(COMPOSE) up -d --build --wait

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

config:
	$(COMPOSE) config

migrate:
	$(COMPOSE) run --rm migrate

seed:
	$(COMPOSE) run --rm --no-deps --entrypoint php api bin/console app:seed

fixtures:
	@test -n "$(DEMO_EMAIL)" && -f "$(DEMO_PASSWORD_FILE)" || (echo "Usage: make fixtures DEMO_EMAIL=demo@example.test DEMO_PASSWORD_FILE=/private/password-file" >&2; exit 1)
	$(COMPOSE) run --rm --no-deps --entrypoint php \
		-e APP_ENV=dev -e APP_DEMO_EMAIL="$(DEMO_EMAIL)" \
		-e APP_DEMO_PASSWORD_FILE=/run/secrets/demo_password \
		-v "$(abspath $(DEMO_PASSWORD_FILE)):/run/secrets/demo_password:ro" \
		api bin/console app:seed:demo

# Prompts for the password (hidden); never pass it on the command line.
user-create:
	@test -n "$(EMAIL)" || (echo "Usage: make user-create EMAIL=user@example.com [ADMIN=1]" >&2; exit 1)
	$(COMPOSE) run --rm --no-deps --entrypoint php api bin/console app:user:create "$(EMAIL)" $(if $(ADMIN),--admin,)

user-reset-password:
	@test -n "$(EMAIL)" || (echo "Usage: make user-reset-password EMAIL=admin@example.com" >&2; exit 1)
	@bash ops/local.sh reset-password

# Delete expired refresh tokens and ended login throttle windows (also run by migrate).
prune-auth:
	$(COMPOSE) run --rm --no-deps --entrypoint php api bin/console app:auth:prune

# Local development only: secrets/ is gitignored. Do not overwrite existing keys.
# Use make local-setup to wire the generated MySQL password into DATABASE_URL.
secrets:
	@bash ops/local.sh secrets

jwt-keys:
	@bash ops/local.sh jwt-keys

test:
	docker build --target build -t finance-api-test ./api
	docker run --rm -v "$(CURDIR)/contracts:/contracts:ro" finance-api-test vendor/bin/phpunit
	$(NODE) sh -ec 'npm ci && npm test'

lint:
	$(COMPOSE) exec -T api php bin/console lint:container
	$(NODE) sh -ec 'npm ci && npm run lint && npm run build'

# Known-vulnerability check for locked PHP and production npm dependencies.
audit:
	docker build --target build -t finance-api-test ./api
	docker run --rm finance-api-test composer audit --locked
	$(NODE) npm audit --package-lock-only --omit=dev

e2e:
	@test -n "$(E2E_EMAIL)" && -f "$(E2E_PASSWORD_FILE)" || (echo "Usage: make e2e E2E_EMAIL=admin@example.test E2E_PASSWORD_FILE=/private/password-file [E2E_BASE_URL=http://127.0.0.1:8080]" >&2; exit 1)
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace/webapp \
		-v "$(abspath $(E2E_PASSWORD_FILE)):/run/secrets/e2e_password:ro" \
		-e E2E_EMAIL="$(E2E_EMAIL)" -e E2E_PASSWORD_FILE=/run/secrets/e2e_password \
		-e E2E_BASE_URL="$(or $(E2E_BASE_URL),http://127.0.0.1:8080)" \
		mcr.microsoft.com/playwright:v1.65.1-noble sh -ec 'npm ci --no-audit --no-fund && npm run e2e'
