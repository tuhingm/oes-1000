#!/usr/bin/env bash
set -Eeuo pipefail

# OES Academy Moodle 5.2 installer for a fresh Ubuntu 24.04 LTS VPS.
# Run as root. No credentials are committed to this repository.

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash install-ubuntu-24.04.sh"
  exit 1
fi
if [[ ! -f /etc/os-release ]] || ! grep -q 'VERSION_ID="24.04"' /etc/os-release; then
  echo "This installer targets Ubuntu 24.04 LTS only."
  exit 1
fi
if [[ -d /var/www/moodle ]]; then
  echo "/var/www/moodle already exists. Refusing to overwrite an existing Moodle installation."
  exit 1
fi

read -r -p "Academy hostname (e.g. academy-lms.openeconometrics.org): " DOMAIN
read -r -p "Moodle administrator username [oesadmin]: " ADMIN_USER
ADMIN_USER="${ADMIN_USER:-oesadmin}"
read -r -p "Moodle administrator email: " ADMIN_EMAIL
read -r -s -p "Moodle administrator password (12+ characters): " ADMIN_PASS
echo
if [[ "${#ADMIN_PASS}" -lt 12 ]]; then echo "Password must contain at least 12 characters."; exit 1; fi
read -r -p "Moodle site full name [OES Academy]: " SITE_FULL
SITE_FULL="${SITE_FULL:-OES Academy}"

if [[ ! "${DOMAIN}" =~ ^[A-Za-z0-9.-]+$ ]]; then echo "Invalid hostname."; exit 1; fi
if [[ ! "${ADMIN_EMAIL}" =~ ^[^@]+@[^@]+\.[^@]+$ ]]; then echo "Invalid email address."; exit 1; fi
if [[ ! "${ADMIN_USER}" =~ ^[A-Za-z0-9._-]+$ ]]; then echo "Invalid admin username."; exit 1; fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y apache2 mariadb-server git curl ca-certificates unzip certbot python3-certbot-apache \
  php8.3 php8.3-cli php8.3-common php8.3-curl php8.3-gd php8.3-intl php8.3-mbstring \
  php8.3-mysql php8.3-soap php8.3-xml php8.3-zip php8.3-opcache

PHP_INI=/etc/php/8.3/apache2/conf.d/99-oes-academy.ini
cat > "${PHP_INI}" <<'EOF'
memory_limit = 512M
max_execution_time = 300
max_input_time = 300
max_input_vars = 5000
upload_max_filesize = 128M
post_max_size = 128M
opcache.enable = 1
opcache.memory_consumption = 128
opcache.max_accelerated_files = 10000
EOF

systemctl enable --now mariadb apache2
mariadb-secure-installation || true

DB_PASS="$(openssl rand -hex 32)"
install -m 600 /dev/null /root/oes-academy-secrets.env
cat > /root/oes-academy-secrets.env <<EOF
MOODLE_DOMAIN='${DOMAIN}'
MOODLE_DB_NAME='moodle'
MOODLE_DB_USER='moodleuser'
MOODLE_DB_PASS='${DB_PASS}'
MOODLE_ADMIN_USER='${ADMIN_USER}'
MOODLE_ADMIN_EMAIL='${ADMIN_EMAIL}'
EOF
chmod 600 /root/oes-academy-secrets.env

mariadb <<SQL
CREATE DATABASE moodle DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'moodleuser'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,CREATE TEMPORARY TABLES,DROP,INDEX,ALTER ON moodle.* TO 'moodleuser'@'localhost';
FLUSH PRIVILEGES;
SQL

git clone --depth 1 --branch MOODLE_502_STABLE https://github.com/moodle/moodle.git /var/www/moodle
install -d -o www-data -g www-data -m 770 /var/moodledata
chown -R root:root /var/www/moodle
find /var/www/moodle -type d -exec chmod 755 {} \;
find /var/www/moodle -type f -exec chmod 644 {} \;

cat > /etc/apache2/sites-available/oes-academy.conf <<EOF
<VirtualHost *:80>
    ServerName ${DOMAIN}
    DocumentRoot /var/www/moodle/public
    <Directory /var/www/moodle/public>
        Options FollowSymLinks
        AllowOverride All
        Require all granted
        DirectoryIndex index.php
    </Directory>
    ErrorLog ${APACHE_LOG_DIR}/oes-academy-error.log
    CustomLog ${APACHE_LOG_DIR}/oes-academy-access.log combined
</VirtualHost>
EOF
a2dissite 000-default.conf
a2enmod rewrite headers
a2ensite oes-academy.conf
systemctl reload apache2

# Run Moodle's official CLI installer. Password is passed only to the local process.
php /var/www/moodle/admin/cli/install.php \
  --lang=en \
  --wwwroot="https://${DOMAIN}" \
  --dataroot=/var/moodledata \
  --dbtype=mariadb \
  --dbhost=localhost \
  --dbname=moodle \
  --dbuser=moodleuser \
  --dbpass="${DB_PASS}" \
  --fullname="${SITE_FULL}" \
  --shortname="OES Academy" \
  --adminuser="${ADMIN_USER}" \
  --adminpass="${ADMIN_PASS}" \
  --adminemail="${ADMIN_EMAIL}" \
  --non-interactive \
  --agree-license

unset ADMIN_PASS
chown root:root /var/www/moodle/config.php
chmod 640 /var/www/moodle/config.php

# Add a persistent top-level link back to the OES browser laboratory.
cat >> /var/www/moodle/config.php <<'EOF'

$CFG->custommenuitems = 'OES Laboratory|https://tuhingm.github.io/oes-1000/web/index.html';
EOF

# Moodle scheduled tasks must run every minute.
cat > /etc/cron.d/oes-academy-moodle <<'EOF'
* * * * * www-data /usr/bin/php /var/www/moodle/admin/cli/cron.php >/dev/null 2>&1
EOF
chmod 644 /etc/cron.d/oes-academy-moodle

# Obtain TLS only after DNS for the hostname points to this VPS.
echo
echo "Moodle has been installed. Next, verify DNS and enable HTTPS:"
echo "  certbot --apache -d ${DOMAIN}"
echo "Then open https://${DOMAIN} and verify the site."
echo
echo "Secrets are stored in /root/oes-academy-secrets.env (root-only)."
echo "Do not copy this file into Git or share it in chat."
