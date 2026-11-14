# OES Academy — Static LMS

OES Academy is a self-contained, browser-based learning management interface served as static files from GitHub Pages. It does not require Moodle, a VPS, a database server, Supabase, or another hosted backend.

## Included learner pages

- Academy overview and learner dashboard
- Course catalogue with search and level filtering
- Course overview and module/lesson navigation
- Lesson reading pages with learning objectives and applied workflow
- Knowledge-check quizzes with automatic scoring and explanations
- My Learning and per-course progress
- Assignments and local submission notes
- Grades and assessment history
- Completion certificate view with browser print / Save as PDF
- Learner profile with local data export/import
- Instructor studio for local course drafts and announcements
- Direct links to the existing OES browser laboratory

## Run it

Open `index.html` through GitHub Pages at `/academy/`. For local development, serve the repository directory using any static file server, or open `index.html` directly in a modern browser.

## Storage and limitations

The application stores profile details, enrolments, lesson completion, quiz attempts, assignment notes, course drafts and announcements in the browser's `localStorage` under `oes-academy-static-v1`.

This is deliberately a no-backend implementation:
- No passwords are collected.
- There is no secure authentication or role-based access control.
- Data is specific to one browser/device and is not synchronized between learners.
- Browser storage can be cleared by the user or browser.
- Assignment notes are not file uploads and are not visible to an instructor.
- Course drafts and announcements are local to the browser. Learners can export and import a JSON backup to move their own records between browsers manually.
- Completion certificates are locally generated print views, not signed or independently verifiable credentials.
- There is no payment processing, email delivery, or remote student administration.

Do not treat the local profile, gradebook or certificate as a secure institutional record. A shared, secure multi-user LMS necessarily requires a backend or hosted identity/data service. This edition intentionally avoids that dependency.

## Preserve OES

The Academy lives in its own `academy/` directory. The existing OES estimator engine and `web/` interface are not modified. Practical lessons link directly to `../web/index.html`.

## Data reset

Use My Profile → Reset local learning data. This removes only the Academy data stored in the current browser.
