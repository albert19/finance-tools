#!/bin/sh
set -eu
# Restrict runtime URL to safe characters before injecting into JavaScript.
case "${API_BASE_URL:-/api}" in
  *[!a-zA-Z0-9_:/.\-]*|'') echo "Invalid API_BASE_URL" >&2; exit 1 ;;
esac
printf 'window.__FINANCE_CONFIG__ = { apiBaseUrl: "%s" };\n' "${API_BASE_URL:-/api}" > /usr/share/nginx/html/config.js
