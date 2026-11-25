#!/bin/bash
set -euo pipefail
password="$(cat /run/secrets/elastic_password)"
curl --fail --silent --show-error --retry 8 --retry-delay 3 \
  -u "elastic:${password}" \
  -H "kbn-xsrf: finance-setup" -H "Content-Type: application/json" \
  -X POST http://kibana:5601/api/data_views/data_view \
  -d '{"data_view":{"id":"logs-finance","title":"logs-finance-*","name":"Finance logs","timeFieldName":"@timestamp"},"override":true}' >/dev/null
echo "Kibana data view configured"
