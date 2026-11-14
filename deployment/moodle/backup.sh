#!/usr/bin/env bash
set -Eeuo pipefail

# Run as root. Configure off-site encrypted backup transport separately.
if [[ "${EUID}" -ne 0 ]]; then echo "Run as root."; exit 1; fi
source /root/oes-academy-secrets.env
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="/var/backups/oes-academy"
install -d -m 700 "${DEST}"
mariadb-dump --single-transaction --routines --triggers \
  -u"${MOODLE_DB_USER}" -p"${MOODLE_DB_PASS}" "${MOODLE_DB_NAME}" \
  | gzip -9 > "${DEST}/moodle-db-${STAMP}.sql.gz"
tar -czf "${DEST}/moodledata-${STAMP}.tar.gz" -C /var moodledata
tar -czf "${DEST}/moodle-config-${STAMP}.tar.gz" -C /var/www/moodle config.php
chmod 600 "${DEST}"/*
find "${DEST}" -type f -mtime +14 -delete
echo "Backup created in ${DEST}. Copy encrypted backups off-site and test restoration."
