#!/usr/bin/env bash
# Restore a downloaded custom-format backup into a NEW verification database.
set -euo pipefail

archive=${1:?Usage: restore-postgres.sh BACKUP.dump [NEW_DATABASE] [NAMESPACE]}
restore_db=${2:-taskflow_restore_$(date -u +%Y%m%d%H%M%S)}
namespace=${3:-taskflow}
[[ -s "$archive" ]] || { echo 'Backup file is missing or empty.' >&2; exit 1; }
[[ "$restore_db" =~ ^taskflow_restore_[a-zA-Z0-9_]+$ ]] || {
  echo 'Target must start with taskflow_restore_ and contain only letters, digits, underscores.' >&2
  exit 1
}

# createdb fails if the target already exists; the live taskflow database is never replaced.
kubectl -n "$namespace" exec -i postgres-0 -- sh -eu -c '
  createdb -U "$POSTGRES_USER" "$1"
  pg_restore -U "$POSTGRES_USER" --no-owner --exit-on-error --dbname="$1"
' sh "$restore_db" < "$archive"

kubectl -n "$namespace" exec postgres-0 -- sh -eu -c '
  psql -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1 -c "SELECT count(*) AS restored_tasks FROM tasks;"
' sh "$restore_db"
printf 'Restored into verification database: %s\n' "$restore_db"
