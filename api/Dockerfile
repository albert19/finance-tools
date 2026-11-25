FROM php:8.5-cli AS build
RUN apt-get update && apt-get install -y --no-install-recommends unzip libzip-dev && docker-php-ext-install zip pdo_mysql && rm -rf /var/lib/apt/lists/*
COPY --from=composer:2.9.5 /usr/bin/composer /usr/local/bin/composer
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-interaction --prefer-dist --no-scripts --no-progress
COPY . .
RUN composer dump-autoload --optimize

# Production dependencies only; the build stage above keeps dev tools for tests.
FROM build AS vendor
RUN composer install --no-dev --no-interaction --prefer-dist --no-scripts --no-progress --optimize-autoloader \
    && rm -rf /app/tests /app/composer.phar /app/docker

FROM dunglas/frankenphp:1.13.6-php8.5-trixie
ARG APP_UID=1000
RUN install-php-extensions pdo_mysql \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
COPY docker/php/zz-security.ini $PHP_INI_DIR/conf.d/zz-security.ini
WORKDIR /app
COPY --from=vendor /app /app
# Run unprivileged; the UID must own the mounted secret files (mode 600).
RUN useradd --uid "${APP_UID}" --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/var /config/caddy /data/caddy \
    && chown -R app:app /app/var /config/caddy /data/caddy
USER app
ENV APP_ENV=prod APP_DEBUG=0 SERVER_NAME=:8000
EXPOSE 8000
CMD ["frankenphp", "run", "--config", "/app/Caddyfile"]
