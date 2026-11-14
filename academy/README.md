# OES Academy — LMS frontend

This directory contains the first OES Academy learning portal interface, deployed as a separate static section of OES-1000.

## Current capabilities
- Academy landing page and course catalogue
- Search and level filtering
- Six specialist courses plus a 12-week flagship curriculum
- Module and lesson syllabus previews
- Links to the OES browser laboratory
- Explicit demonstration-only sign-in dialog

## Important deployment boundary
GitHub Pages serves static assets. This frontend is a UI and curriculum prototype, not a production LMS. It does not create accounts, securely authenticate learners, process payments, persist enrollment or grades, store video, or issue authoritative certificates. The sign-in interaction is intentionally a no-op demonstration and must not be represented as a working account system.

## Production LMS integration
Use this interface as the Academy public site and integrate a full LMS backend (recommended: self-hosted Moodle) at a dedicated subdomain such as `academy-lms.openeconometrics.org`, or replace this frontend with a backend-backed application. Moodle should own:
- Identity, roles and access control
- Courses, cohorts, enrollment and course completion
- Assignments, question banks, quizzes and gradebook
- Payment enrollment integration
- Certificates and audit records

The OES-1000 static site remains the econometric software distribution and browser estimation environment. Link practical lessons to `../web/index.html`; do not move or rewrite the estimator engine for LMS work.

## Deployment
The site is available at `/academy/` after GitHub Pages deploys the repository root.
