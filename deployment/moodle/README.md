# OES Academy — production Moodle deployment

This deployment kit installs a full Moodle LMS on a **fresh Ubuntu 24.04 LTS VPS**. Moodle owns student identities, course enrolment, content, assignments, quizzes, grades and completion records. GitHub Pages remains the public OES Academy catalogue and OES-1000 remains the browser econometrics laboratory.

## Architecture

- Public Academy catalogue: `https://tuhingm.github.io/oes-1000/academy/`
- Moodle LMS: a hostname you control, recommended `academy-lms.openeconometrics.org`
- Moodle release line: `MOODLE_502_STABLE` (Moodle 5.2)
- Web server: Apache 2.4
- Runtime: PHP 8.3
- Database: MariaDB 10.11 (Ubuntu 24.04 package line)
- Moodle data: `/var/moodledata`, outside the web root
- OES integration: Moodle top navigation includes a link to the existing OES browser laboratory

Moodle 5.2 is selected because its published requirements support PHP 8.3 and MariaDB 10.11. Moodle 5.3 requires MariaDB 11.4 / MySQL 8.4 or PostgreSQL 17, so do not deploy 5.3 on this baseline without upgrading the database stack first. Check current supported releases before every production installation.

## Before deployment

You need:
1. A VPS with Ubuntu 24.04 LTS and root SSH access.
2. A domain or subdomain you control.
3. DNS A record for that hostname pointing to the VPS public IPv4 address (and an AAAA record only if IPv6 is configured correctly).
4. Inbound TCP ports 80 and 443 open in the VPS firewall.
5. At least 2 vCPU, 4 GB RAM and 40–50 GB SSD for a small pilot; increase resources based on concurrent learners, uploaded media and backups.
6. An SMTP service for password resets, enrollment messages and course notifications. Configure this in Moodle after installation.

GitHub Pages alone cannot host Moodle: Moodle requires PHP execution, a relational database, persistent writable Moodle data and scheduled cron jobs.

## Install

From the repository root on the VPS:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/tuhingm/oes-1000.git
cd oes-1000/deployment/moodle
sudo bash install-ubuntu-24.04.sh
```

The installer prompts for the Moodle hostname, administrator username/email/password and site name. It generates a database password and stores deployment secrets in `/root/oes-academy-secrets.env` with root-only permissions. No secret is written to the repository.

After the installer finishes, confirm the hostname's DNS A record resolves to the VPS, then run:

```bash
sudo certbot --apache -d academy-lms.openeconometrics.org
```

Replace the example hostname with the exact hostname entered during installation. Open the HTTPS URL and complete the Moodle administration checks.

## Initial Moodle configuration

In Moodle Site administration:

1. Set the site name to **OES Academy** and upload the OES Academy logo.
2. Configure outbound SMTP and test password reset and notification email.
3. Set timezone and language defaults; allow learners to choose their own language.
4. Set self-registration policy deliberately; for a paid academy, disable unrestricted self-enrolment in paid courses.
5. Configure course categories: Econometric Foundations, Time-Series Econometrics, Panel Data Econometrics, Causal Inference, Bayesian Econometrics, Machine Learning, and Research Practice.
6. Create instructor and course-manager roles; keep site administrator accounts restricted.
7. Configure backups, retention and privacy/data deletion policies.
8. Install only Moodle plugins compatible with the exact Moodle 5.2 release, from trusted sources.
9. Configure a payment/enrolment gateway plugin or a supported external commerce integration. Do not collect card details in the OES static frontend.
10. Configure certificate issuance with a compatible certificate plugin and test verification.

## OES Academy course structure

Use Moodle as the source of truth for courses and learners. The public catalogue in `/academy/` is a marketing front end; Moodle course pages should be the authenticated learning destination.

Suggested first courses:
- Applied Econometrics: Theory, Estimation and Computational Practice (12 weeks)
- Advanced Time-Series Econometrics (6 weeks)
- Advanced Panel Data Econometrics (6 weeks)
- Modern Causal Inference and Policy Evaluation (6 weeks)
- Bayesian Econometrics and MCMC (5 weeks)
- Machine Learning for Economists (5 weeks)
- Econometric Foundations and Regression Analysis (4 weeks)

For practical lessons, add a Moodle URL activity pointing to `https://tuhingm.github.io/oes-1000/web/index.html`. The estimator runs in the learner's browser; Moodle should not receive the learner's dataset.

## Backups and operations

- Moodle code: `/var/www/moodle`
- Moodle data: `/var/moodledata`
- Database: `moodle`
- Secrets: `/root/oes-academy-secrets.env`
- Cron: `/etc/cron.d/oes-academy-moodle`

Back up both the database and `/var/moodledata` together, keep encrypted copies off the VPS, and test restores. Do not rely on a VPS snapshot as the only backup. Apply Moodle security updates promptly and test upgrades on a staging copy first.

## Security notes

- Never commit `config.php`, database credentials, SMTP credentials, payment secrets or backups.
- Keep `moodledata` outside the public web root.
- Use HTTPS before opening registration.
- Restrict SSH to key-based access and a trusted IP where practical.
- Enable a host firewall and unattended security updates.
- Use a dedicated non-root database account (the installer creates one).
- Configure outbound email before enabling account self-registration.
- Do not use this installer on a server that already hosts another site; it intentionally configures the default Apache virtual host.

## What this repository can and cannot do

This repository now contains the deployable installation recipe, not a running Moodle server. I cannot create a live Moodle instance from GitHub Pages or provision a VPS without access to a hosting account/server. Once a VPS and DNS are available, the script performs the server-side installation. The live Moodle setup, payment gateway, email service and administrator account must then be verified on the actual host.
