#!/bin/bash
set -euo pipefail
export ELASTICSEARCH_PASSWORD
ELASTICSEARCH_PASSWORD="$(cat /run/secrets/kibana_password)"
# The Docker wrapper translates ELASTICSEARCH_* variables into Kibana settings.
exec /usr/local/bin/kibana-docker
