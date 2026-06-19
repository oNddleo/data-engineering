#!/usr/bin/env bash
# Create POC topics on the running KRaft broker. Idempotent.
set -euo pipefail

BOOTSTRAP=${BOOTSTRAP:-kafka:9092}
PARTITIONS=${PARTITIONS:-3}
REPLICATION=${REPLICATION:-1}

create_if_missing() {
  local topic=$1
  local extra_config=${2:-}
  if /opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP}" --list | grep -qx "${topic}"; then
    echo "[topics] ${topic} exists"
  else
    echo "[topics] creating ${topic}"
    # shellcheck disable=SC2086
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP}" \
        --create --topic "${topic}" \
        --partitions "${PARTITIONS}" \
        --replication-factor "${REPLICATION}" \
        ${extra_config}
  fi
}

# Wait until broker accepts metadata calls (compose healthcheck already gates
# on api-versions, but we keep a defensive retry in case of slow startup).
for i in $(seq 1 30); do
  if /opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP}" --list >/dev/null 2>&1; then
    break
  fi
  echo "[topics] waiting for broker ${BOOTSTRAP}... (${i}/30)"
  sleep 2
done

create_if_missing iot.sensors     "--config retention.ms=604800000 --config compression.type=zstd"
create_if_missing iot.sensors.dlq "--config retention.ms=1209600000"

echo "[topics] done"
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP}" --describe
