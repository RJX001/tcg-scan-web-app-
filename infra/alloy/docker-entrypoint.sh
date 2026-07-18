#!/bin/sh
set -eu

# Railway injects PORT for healthchecks; OTLP stays on 4317/4318.
exec alloy run /etc/alloy/config.alloy \
  --server.http.listen-addr="0.0.0.0:${PORT:-12345}" \
  --storage.path=/var/lib/alloy/data \
  "$@"
