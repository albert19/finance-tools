# Backend follow-ups (not implemented in the webapp)

`GET /api/investments` aliases `start_date` to `startDate`, but
`GET /api/investments/{id}` returns the raw `start_date` column. The webapp does
not read either field today; alias the detail field for a consistent API.

`api/src/Controller/FinanceController.php::saveTransaction()` returns an unjoined
`transactions` row after POST/PUT (snake-case `category_id`, no category kind/name);
the GET collection returns a JOIN with `categoryId`, `categoryName`, and `kind`.
The UI refetches the collection after writes. For a uniform API, return the joined
row after POST/PUT as well.

The refresh cookie is Secure/SameSite=Strict and `/api/auth`-scoped. The browser
must access the webapp over HTTPS (except localhost browser exceptions) on the
same origin as the API proxy. Login/refresh/logout requests require the browser
Origin to match the request host exactly and `X-Requested-With: XMLHttpRequest`;
the client sends the header and includes credentials. If a local browser
preview rewrites Host, the API supports an explicit loopback-only
`LOCAL_PREVIEW_ORIGIN`. Configure correct public HTTPS origin forwarding at
the proxy in production; do not use cross-origin API URLs.

Shared legacy golden vectors live outside the `webapp/` Docker build context.
Run `npm test` with `../contracts/simulation-vectors/legacy-python.json` mounted
or available; missing vectors are a hard test failure, not a skip. The production
Dockerfile builds the frontend only and does not run these tests.
