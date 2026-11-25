#!/bin/bash
# One-shot, idempotent local ELK bootstrap. Production should provision via IaC.
set -euo pipefail
url="${ES_URL:-http://elasticsearch:9200}"
elastic_password="$(cat /run/secrets/elastic_password)"
kibana_password="$(cat /run/secrets/kibana_password)"
writer_password="$(cat /run/secrets/logstash_password)"
# Only allow values safe in a JSON string; `make secrets` creates hex values.
for password in "$kibana_password" "$writer_password"; do
  [[ "$password" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo "ELK passwords must be alphanumeric, hyphen or underscore" >&2; exit 1; }
done
request() {
  curl --fail --silent --show-error --retry 5 --retry-delay 3 \
    -u "elastic:${elastic_password}" -H "Content-Type: application/json" \
    -X "$1" "$url$2" -d "$3" >/dev/null
}
request POST /_security/user/kibana_system/_password \
  "{\"password\":\"${kibana_password}\"}"
request PUT /_security/role/logstash_writer \
  '{"cluster":["monitor"],"indices":[{"names":["logs-finance-*"],"privileges":["auto_configure","create_index","create_doc","write"]}]}'
request PUT /_security/user/logstash_writer \
  "{\"password\":\"${writer_password}\",\"roles\":[\"logstash_writer\"],\"full_name\":\"Finance Logstash writer\"}"
request PUT /_ilm/policy/finance-logs \
  '{"policy":{"phases":{"hot":{"actions":{}},"delete":{"min_age":"30d","actions":{"delete":{}}}}}}'
request PUT /_index_template/finance-logs \
  '{"index_patterns":["logs-finance-*"],"priority":200,"template":{"settings":{"index.lifecycle.name":"finance-logs","number_of_shards":1,"number_of_replicas":0},"mappings":{"dynamic":true}}}'
echo "Elasticsearch users, role, template and ILM policy configured"
