#!/bin/bash
set -euo pipefail
export ES_WRITER_PASSWORD
ES_WRITER_PASSWORD="$(cat /run/secrets/logstash_password)"
exec /usr/share/logstash/bin/logstash --path.settings /usr/share/logstash/config
