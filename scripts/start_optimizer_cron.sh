#!/bin/sh
set -eu

CRON_SCHEDULE="${FSRS_OPTIMIZER_CRON_SCHEDULE:-0 3 * * *}"
CRON_FILE="/etc/cron.d/fsrs-optimizer"
ENV_FILE="/app/.cron_env"

printenv | sed 's/"/\\"/g; s/^/export "/; s/=/"="/; s/$/"/' > "$ENV_FILE"
chmod 600 "$ENV_FILE"

cat > "$CRON_FILE" <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
$CRON_SCHEDULE . $ENV_FILE; cd /app && python -m src.services.optimizer_service >> /proc/1/fd/1 2>> /proc/1/fd/2
EOF

chmod 0644 "$CRON_FILE"
crontab "$CRON_FILE"

echo "[optimizer-cron] schedule: $CRON_SCHEDULE"
exec cron -f