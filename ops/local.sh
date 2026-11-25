#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
umask 077

get_env() {
    local key="$1" line value=""
    [[ -f .env ]] || return 0
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" == "$key="* ]] && value="${line#*=}"
    done < .env
    printf '%s' "$value"
}

set_env() {
    local key="$1" value="$2" line found=0
    local tmp
    tmp="$(mktemp .env.XXXXXX)"
    trap 'rm -f -- "$tmp"' RETURN
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" == "$key="* ]]; then
            if (( ! found )); then
                printf '%s=%s\n' "$key" "$value" >> "$tmp"
                found=1
            fi
        else
            printf '%s\n' "$line" >> "$tmp"
        fi
    done < .env
    if (( ! found )); then
        printf '%s=%s\n' "$key" "$value" >> "$tmp"
    fi
    mv -- "$tmp" .env
    trap - RETURN
}

ensure_secrets() {
    install -d -m 700 secrets
    chmod 700 secrets
    local name path
    for name in app_secret mysql_password mysql_root_password elastic_password kibana_password logstash_password seed_admin_password; do
        path="secrets/$name"
        if [[ ! -e "$path" && ! -L "$path" ]]; then
            openssl rand -hex 32 > "$path"
        fi
    done
    echo "Local secret files ready."
}

generate_jwt_keys() {
    install -d -m 700 secrets
    if [[ -e secrets/jwt-private.pem || -L secrets/jwt-private.pem
        || -e secrets/jwt-public.pem || -L secrets/jwt-public.pem ]]; then
        echo "JWT key(s) already exist; refusing to overwrite." >&2
        return 1
    fi
    local private public
    private="$(mktemp secrets/.jwt-private.XXXXXX)"
    public="$(mktemp secrets/.jwt-public.XXXXXX)"
    if openssl ecparam -name prime256v1 -genkey -noout -out "$private" &&
        openssl ec -in "$private" -pubout -out "$public"; then
        mv -- "$private" secrets/jwt-private.pem
        mv -- "$public" secrets/jwt-public.pem
        chmod 600 secrets/jwt-private.pem secrets/jwt-public.pem
    else
        rm -f -- "$private" "$public"
        return 1
    fi
}

setup() {
    if [[ ! -f .env ]]; then
        cp .env.example .env
        chmod 600 .env
    fi
    local profiles
    profiles="$(get_env COMPOSE_PROFILES)"
    if [[ ",$profiles," != *",localdb,"* ]]; then
        echo "Local setup requires COMPOSE_PROFILES=localdb; external database settings were left unchanged." >&2
        return 1
    fi

    local admin="${EMAIL:-}" configured
    configured="$(get_env SEED_ADMIN_EMAIL)"
    if [[ -z "$configured" ]]; then
        if [[ -z "$admin" && -t 0 ]]; then
            read -r -p "Finance manager admin email: " admin
        fi
        if [[ ! "$admin" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
            echo "Provide an admin email: make local-start EMAIL=you@example.com" >&2
            return 1
        fi
        set_env SEED_ADMIN_EMAIL "${admin,,}"
    elif [[ -n "$admin" && "${admin,,}" != "${configured,,}" ]]; then
        echo "SEED_ADMIN_EMAIL is already set. Existing accounts are never replaced by local setup." >&2
        return 1
    fi

    ensure_secrets
    # Compose file secrets keep host ownership (mode 600); the non-root API
    # container must run as their owner.
    local uid
    uid="$(get_env APP_UID)"
    if [[ "$(id -u)" != 0 && ( -z "$uid" || "$uid" == 1000 ) ]]; then
        set_env APP_UID "$(id -u)"
    fi
    if [[ ! -e secrets/jwt-private.pem && ! -e secrets/jwt-public.pem ]]; then
        generate_jwt_keys
    elif [[ ! -f secrets/jwt-private.pem || ! -f secrets/jwt-public.pem ]]; then
        echo "Only one JWT key exists. Restore its matching key; refusing to overwrite either." >&2
        return 1
    fi

    local url password
    url="$(get_env DATABASE_URL)"
    if [[ "$url" == *REPLACE_WITH_PASSWORD* ]]; then
        password="$(< secrets/mysql_password)"
        if [[ ! "$password" =~ ^[a-fA-F0-9]{64}$ ]]; then
            echo "Custom MySQL password: set an encoded DATABASE_URL manually; no URL was changed." >&2
            return 1
        fi
        set_env DATABASE_URL "${url/REPLACE_WITH_PASSWORD/$password}"
        unset password
    elif [[ -z "$url" ]]; then
        echo "DATABASE_URL is missing; no URL was changed." >&2
        return 1
    fi

    if [[ "${OBSERVABILITY:-0}" == 1 && ",$profiles," != *",observability,"* ]]; then
        set_env COMPOSE_PROFILES "$profiles,observability"
        # Use Elastic's same-version Docker Hub images if its registry is unavailable.
        [[ -n "$(get_env ELASTICSEARCH_IMAGE)" ]] || set_env ELASTICSEARCH_IMAGE elastic/elasticsearch:9.5.6
        [[ -n "$(get_env LOGSTASH_IMAGE)" ]] || set_env LOGSTASH_IMAGE elastic/logstash:9.5.6
        [[ -n "$(get_env KIBANA_IMAGE)" ]] || set_env KIBANA_IMAGE elastic/kibana:9.5.6
        [[ -n "$(get_env FILEBEAT_IMAGE)" ]] || set_env FILEBEAT_IMAGE elastic/filebeat:9.5.6
    fi

    docker compose -f compose.yaml config --quiet
    echo "Local configuration ready; existing secrets, accounts, and database rows were not reset."
}

access_info() {
    [[ -f .env ]] || { echo "Run make local-start EMAIL=you@example.com first." >&2; return 1; }
    local email web_port kibana_port preview
    email="$(get_env SEED_ADMIN_EMAIL)"
    web_port="$(get_env WEBAPP_PORT)"
    kibana_port="$(get_env KIBANA_PORT)"
    preview="$(get_env LOCAL_PREVIEW_ORIGIN)"
    printf '\nFinance manager: http://127.0.0.1:%s/\n' "${web_port:-8080}"
    printf '  Email: %s\n  Password file: %s\n' "${email:-not configured}" "$(get_env SEED_ADMIN_PASSWORD_FILE)"
    [[ -z "$preview" ]] || printf '  Local browser preview (if running): %s/\n' "${preview%/}"
    printf 'Kibana (optional): http://127.0.0.1:%s/\n' "${kibana_port:-5601}"
    printf '  Username: elastic\n  Password file: %s\n' "$(get_env ELASTIC_PASSWORD_FILE)"
    echo "  If not running, enable it with make local-start OBSERVABILITY=1."
    echo "MySQL: no web UI; use make db-shell (the local finance database)."
    echo "API: use Finance manager; Elasticsearch is REST-only (same elastic login)."
    echo "Logstash and Filebeat: background services; no interactive login."
    echo "Password files are private. If the admin password was changed outside this setup,"
    echo "use make admin-reset-password; local setup never resets an existing account."
}

reset_password() {
    local admin target
    admin="$(get_env SEED_ADMIN_EMAIL)"
    target="${EMAIL:-}"
    [[ -n "$target" ]] || { echo "Usage: make user-reset-password EMAIL=user@example.com" >&2; return 1; }
    [[ -t 0 ]] || { echo "Run this from an interactive terminal." >&2; return 1; }
    local APP_USER_PASSWORD
    read -r -s -p "New password (12+ characters): " APP_USER_PASSWORD
    printf '\n'
    export APP_USER_PASSWORD
    docker compose -f compose.yaml exec -T -e APP_USER_PASSWORD api php bin/console app:user:reset-password "$target"
    if [[ "${target,,}" == "${admin,,}" && -n "$admin" ]]; then
        local path
        path="$(get_env SEED_ADMIN_PASSWORD_FILE)"
        [[ "$path" == ./secrets/* || "$path" == secrets/* ]] || {
            echo "Admin password changed, but custom secret path was not updated: $path" >&2
            return 1
        }
        printf '%s\n' "$APP_USER_PASSWORD" > "$path"
        chmod 600 "$path"
        echo "Admin password file updated."
    fi
    unset APP_USER_PASSWORD
}

case "${1:-}" in
    setup) setup ;;
    start) setup; docker compose -f compose.yaml up -d --build --wait; access_info ;;
    access) access_info ;;
    secrets) ensure_secrets ;;
    jwt-keys) generate_jwt_keys ;;
    reset-password) reset_password ;;
    reset-admin-password)
        EMAIL="$(get_env SEED_ADMIN_EMAIL)"
        [[ -n "$EMAIL" ]] || { echo "SEED_ADMIN_EMAIL is not configured." >&2; exit 1; }
        reset_password ;;
    *) echo "Usage: bash ops/local.sh {start|setup|access|secrets|jwt-keys|reset-password|reset-admin-password}" >&2; exit 2 ;;
esac
