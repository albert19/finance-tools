# API implementation notes

## Local demo data (development/test only)

After applying the Doctrine migrations to a **disposable development/test
database**, configure `APP_ENV=dev` (or `test`), `APP_DEMO_EMAIL` and
`APP_DEMO_PASSWORD_FILE`. Create the password file outside the repository
(for example `umask 077; printf '%s\n' 'your-unique-long-password' > /tmp/finance-demo-password`);
use a unique password of at least 12 characters. Never commit or print it.
Run `php bin/console app:seed:demo` from the API directory with those
environment variables available to the PHP process. When using a container,
mount the password file and point `APP_DEMO_PASSWORD_FILE` at its *container*
path. This command does not run as part of migrations or `app:seed`.

The command **refuses production**, missing credentials, and existing accounts
by default. On a second run (or to add only missing records to an account you
explicitly own), pass `--allow-existing-user`; it will not change the password,
roles, or existing finance records. Do not use that option with a real user's
email. It creates sample categories, January/February 2024 budgets (including
multiple Food lines), transactions, and an investment with snapshots.
Existing budgets for those periods or investments with the demo name are
skipped rather than altered. Fixture IDs are stable per account for safe
reruns; existing records with those IDs are left untouched. Seed only into a
database where sample data is appropriate.

Doctrine ORM attribute mappings in `src/Entity` cover users, refresh tokens,
categories, budgets/lines, transactions, investments and snapshots, with
explicit owner/parent relations. HTTP controllers delegate to application
services under `src/Service`, which depend on interfaces in `src/Port`.
Doctrine adapters in `src/Repository` own owner-scoped SQL, transactions and
ORM access. Portfolio uses ORM; identity/session and budget/category/transaction
operations use DBAL. Budget versions and refresh rotation remain atomic DBAL
operations. This is an incremental migration, **not** a claim that every
finance route is ORM-backed. The current `/api/*` contract is in
`contracts/openapi.yaml`; URL versioning is not implemented yet.

Each table is created by one Doctrine migration (`00000` through `00008`) in
foreign-key order. The seven new versions inspect and adopt matching tables
created by the earlier combined `00000` migration, so an existing local
database can migrate forward without recreating or dropping user data.
Rollback is intentionally disabled; never use schema-update to mutate the
database.

Both paths were exercised locally: the existing `finance` database retained
its admin row and recorded all nine versions, and a separate fresh MySQL schema
created all nine application tables plus the migration tracking table. The
fresh-check schema is intentionally retained for inspection.

Schema validation on the local MySQL 9.7 database after all nine migrations
still reports **one ORM/DBAL type mismatch**. The read-only
`doctrine:schema:update --dump-sql` proposes only:

```sql
ALTER TABLE monthly_budgets CHANGE month month TINYINT NOT NULL;
```

The migration already creates `month` as `TINYINT NOT NULL`. DBAL introspects
MySQL `TINYINT` as a boolean, while the ORM deliberately maps the month as a
`smallint`/PHP integer (with a `TINYINT` SQL column definition) so values 1–12
remain integers. Re-mapping it as a boolean would corrupt month values on ORM
hydration. Do **not** apply this suggested ALTER; it does not resolve the
underlying type comparison. The DBAL-only `login_throttles` table is excluded
from schema comparison. Doctrine's migration tracking table must remain
visible to DBAL so applied versions are recognized; read-only ORM schema-update
may propose dropping it. Never run schema-update: use migrations and inspect
read-only validation output.

`GET /api/investments/{id}/comparison` returns `{projection, points,
expectedRate, actualXirr, status}`. Rates and deviation percentages are
fractions (e.g. `0.1` is 10%); status uses a 2% tolerance (overridable with
`PORTFOLIO_TOLERANCE_PCT`) and the same labels as the Python comparison. Snapshot dates cannot precede the investment's
start date or duplicate a date in the same investment. The snapshot insertion
locks the owner-scoped investment row in MySQL to serialize concurrent
inserts without changing existing migrations or rejecting legacy databases
that may already contain duplicate dates. No new unique index is present:
direct SQL writers must apply the same invariant.

The simulator accepts camelCase parameters. `withdrawalAmount` (default zero),
`withdrawalFrequency` (default monthly), and `withdrawalStartMonth` (default
zero) implement the Python retirement phase. Monthly and yearly rows include
`index`, `costBasis`, `gains`, and `realClosing`; summary includes `finalTax`,
`realFinalCapitalNet`, `totalReturnPct`, `irrPct`, `irrNetPct`, and
`depletionMonth`. `totalReturn` remains a fraction for compatibility.
The optional `applyTaxes` uses the Spanish savings-income brackets from the
Python domain; annual realized gains are charged in the monthly breakdown,
and `finalTax` estimates tax on remaining unrealized gains.

Reports: monthly response is `{year, month, budget, rows, totals}`; annual
response is `{year, rows, months, totals}` with `months` holding the twelve
full monthly reports. Both include `plannedNet` and `actualNet` in `totals`.
Each row's `variance` is **actual minus planned** regardless of kind, and
`variancePct` is null if planned is zero. Status uses a relative 2% tolerance
by default (overridable with `BUDGET_TOLERANCE_PCT`)
(income over / expense under = favourable).

Runtime env variables follow compose: `APP_SECRET_FILE`,
`SEED_ADMIN_PASSWORD_FILE`, `JWT_SECRET_KEY`, `JWT_PUBLIC_KEY`, `DATABASE_URL`.
Auth cookies require an exact same-origin `Origin` header and
`X-Requested-With: XMLHttpRequest`. The webapp nginx proxy now forwards
`$http_host`, preserving non-default ports for the local exact-origin check.
For a local browser preview that rewrites `Host`, set the exact loopback URL
in `LOCAL_PREVIEW_ORIGIN`; this opt-in does not enable credentialed CORS and
requires a loopback HTTP host on the API request. Leave it unset in production.
Only `X-Forwarded-For` is trusted, and only from `TRUSTED_PROXIES` (the
webapp nginx overwrites it with the peer address); scheme and host still come
from the connection. When TLS is terminated upstream in a future deployment,
configure trusted reverse-proxy scheme handling as well; do not weaken the
origin check to hostname-only. `TRUSTED_HOSTS` takes comma-separated host
regexes; untrusted hosts get 400 `bad_request`.
A wrong current password on `POST /api/me/password` returns 403 (not 401, so
clients do not refresh and retry). Create users with
`make user-create EMAIL=...` (hidden prompt) or `APP_USER_PASSWORD`; the
command has no `--password` option. All responses carry `Cache-Control:
no-store`, `nosniff`, `X-Frame-Options: DENY` and a `default-src 'none'` CSP.
