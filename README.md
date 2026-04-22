# EMGS Visa Tracker

EMGS Visa Tracker is a self-hosted Python application that automatically monitors the EMGS visa application status page for one or more passport numbers and sends email notifications when something changes.

This project was created to solve a practical real-world problem:

> The EMGS website provides a way to track visa applications, but in many cases important updates are effectively communicated to the institution first, while the passport owner or student may not be notified directly or immediately.

This tracker allows the passport owner, student, friend, or trusted person to monitor the application independently and receive updates directly by email without manually checking the website over and over again.

---

# Table of Contents

1. [What this project is](#what-this-project-is)
2. [Why this project exists](#why-this-project-exists)
3. [What the tracker does](#what-the-tracker-does)
4. [How it works internally](#how-it-works-internally)
5. [Main features](#main-features)
6. [Project structure](#project-structure)
7. [File overview](#file-overview)
8. [How change detection works](#how-change-detection-works)
9. [How status colors work](#how-status-colors-work)
10. [Email behavior](#email-behavior)
11. [Temporary error handling](#temporary-error-handling)
12. [Requirements](#requirements)
13. [Quick start with Docker Compose](#quick-start-with-docker-compose)
14. [Run with Python directly](#run-with-python-directly)
15. [Run with GitHub Actions](#run-with-github-actions)
16. [Environment variables](#environment-variables)
17. [Complete `.env` example](#complete-env-example)
18. [Docker setup details](#docker-setup-details)
19. [GitHub Actions setup details](#github-actions-setup-details)
20. [State file and persistence](#state-file-and-persistence)
21. [Making the repository public safely](#making-the-repository-public-safely)
22. [How to clean sensitive files from git history](#how-to-clean-sensitive-files-from-git-history)
23. [How to install `git-filter-repo` on Windows](#how-to-install-git-filter-repo-on-windows)
24. [Recommended public release process](#recommended-public-release-process)
25. [Troubleshooting](#troubleshooting)
26. [How anyone can use or fork this project](#how-anyone-can-use-or-fork-this-project)
27. [Contribution ideas](#contribution-ideas)
28. [Security notes](#security-notes)
29. [Disclaimer](#disclaimer)
30. [License](#license)

---

# What this project is

EMGS Visa Tracker is a lightweight automation tool for the EMGS application tracking page.

It does **not** modify anything on EMGS. It only automates the same action a normal user would do manually in a browser:

1. open the tracking page
2. enter the passport number
3. choose the nationality
4. submit the form
5. read the result page
6. extract the useful information
7. compare it with the previous saved result
8. send an email when needed

In other words, it is a monitoring and notification tool.

---

# Why this project exists

Many applicants check the EMGS website manually every day, sometimes several times a day, because:

- they are waiting urgently for progress
- the institution may be the one receiving updates first
- they want direct visibility into their own application
- multiple people may be waiting on several applications
- manual checking is repetitive and tiring

This project was built to remove that manual effort. Instead of opening the EMGS page repeatedly, the tracker does the checking for you and sends the result by email directly to the configured recipient.

This is especially useful for:

- students waiting for visa progress
- friends tracking applications together
- a person helping family or friends monitor their applications
- anyone who wants a self-hosted independent tracker

---

# What the tracker does

For each configured passport number, the tracker:

- visits the EMGS search form page
- extracts the hidden `form_key`
- submits the passport number and nationality
- receives the application status page
- parses structured information from the HTML
- compares the current parsed result with the previously saved result
- decides whether to send an email
- updates the saved state

The tracker can monitor:

- one passport
- multiple passports
- one email per passport
- different recipients for different passports

---

# How it works internally

The full flow is:

## Step 1 — load configuration

The application reads all settings from environment variables.

This includes:

- passport numbers
- destination emails
- SMTP server settings
- nationality
- logging settings
- interval settings
- daily summary settings
- issue notification settings
- state file path

## Step 2 — load saved state

The tracker reads a JSON file containing the last known result.

This file is used for:

- detecting changes
- remembering whether a daily summary was already sent for the day
- remembering temporary issue counters

## Step 3 — fetch EMGS form page

The tracker requests the EMGS form page and extracts the hidden `form_key`.

This is required because the website expects that field when the form is submitted.

## Step 4 — submit the lookup request

The tracker sends a POST request containing:

- `form_key`
- passport number
- nationality
- agreement flag

## Step 5 — parse the result page

The tracker parses the returned HTML and extracts:

- full name
- travel document number
- application number
- application type
- application status
- percentage
- percentage color
- percentage color meaning
- explanation text
- application history

## Step 6 — compare with previous state

The tracker does not compare raw HTML.

Instead, it compares a stable subset of meaningful fields to avoid false change alerts.

## Step 7 — decide whether to send an email

Depending on configuration, it may:

- send only when changed
- send on every successful check
- send a daily summary
- send calm issue notifications after repeated failures

## Step 8 — save the latest state

The tracker writes the new parsed result into the JSON state file.

## Step 9 — repeat

If running in loop mode, it sleeps for the configured interval and checks again later.

---

# Main features

- Track multiple passports at once
- Send one email per passport recipient
- Detect meaningful changes
- Support always-email mode for testing
- Support daily summary emails
- Parse and include percentage color and meaning
- Gracefully handle temporary EMGS/provider failures
- Use inline HTML email templates
- Run locally with Docker Compose
- Run periodically with GitHub Actions
- Configure everything with environment variables
- Keep state in a JSON file for change detection

---

# Project structure

```text
app/
├── main.py
├── config.py
├── models.py
├── state_store.py
├── emailer.py
├── email_templates.py
├── emgs_client.py
└── runner.py

# File Overview

## `app/main.py`

The main entrypoint.

Responsible for:

- loading configuration
- initializing logging
- running once or running forever in a loop

## `app/config.py`

Responsible for:

- reading environment variables
- validating required settings
- parsing booleans and integers
- splitting comma-separated passports and emails

## `app/models.py`

Contains:

- dataclasses
- custom exceptions
- structured internal objects

## `app/state_store.py`

Responsible for:

- reading JSON state
- writing JSON state
- daily summary tracking
- repeated issue tracking

## `app/emailer.py`

Responsible for:

- connecting to SMTP
- sending text + HTML emails

## `app/email_templates.py`

Responsible for building:

- regular status emails
- daily summary emails
- temporary issue emails

## `app/emgs_client.py`

Responsible for:

- loading the form page
- submitting the status form
- parsing EMGS HTML
- extracting structured application data

## `app/runner.py`

Core orchestration layer.

Responsible for:

- checking each configured passport
- calling the EMGS client
- comparing state
- sending emails
- updating saved state

# How Change Detection Works

The tracker compares a stable fingerprint of the current result with the last saved result.

Typical fields used for comparison are:

- percentage
- percentage color
- application status
- application number
- latest history row

This is better than comparing raw HTML because the webpage may contain irrelevant changes that do not reflect application progress.

# Important First-Run Behavior

On the very first successful run, there is no previous saved state.

That means:

- the tracker treats the first valid result as new
- it may send an email even when `ALWAYS_EMAIL=false`

This is expected and normal.

# How Status Colors Work

The EMGS page includes not only a percentage but also a color that gives meaning to that percentage.

The tracker extracts the active color from the result page and maps it to a meaning.

Typical meanings:

- **Green** means the application is progressing normally
- **Amber / Yellow** means additional documents or corrections may be required
- **Red** means rejection, expiration, or a serious issue at the current stage

This matters because the same percentage can mean very different things depending on the color.

For example:

- `35% + Green = normal progress`
- `35% + Amber = something may be missing`
- `35% + Red = not progressing normally`

The tracker includes this color and meaning in email notifications.

# Email Behavior

The tracker supports multiple email modes.

## 1. Change-based email mode

If:

```env
ALWAYS_EMAIL=false
```

then the tracker sends an email only when the tracked state changes.

This is the recommended production mode.

## 2. Always-email mode

If:

```env
ALWAYS_EMAIL=true
```

then the tracker sends an email after every successful check.

This is useful for:

- testing email sending
- confirming the app is running
- confirming SMTP settings
- debugging during setup

## 3. Daily summary email

If enabled, the tracker can send a daily summary when:

- the configured summary time has passed
- `ALWAYS_EMAIL=false`
- no percentage change happened during that day
- a summary has not already been sent that day

This reassures the user that:

- the tracker is working
- the application was checked
- no visible percentage change happened that day

## 4. Temporary issue notifications

These are optional.

If enabled, the tracker can send a calm operational email after repeated temporary failures such as:

- EMGS timeout
- backend outage
- provider connectivity problem
- temporary SSL/connectivity issue

These are not treated as application status changes.

# Temporary Error Handling

The tracker handles temporary external failures cleanly.

Examples include:

- request timeout
- connection failure
- HTTP 5xx server error
- EMGS/provider backend outage
- SSL/connectivity issue inside EMGS backend flow

When these happen, the tracker:

- does not crash the whole app
- does not overwrite the last valid saved state
- does not treat the issue as a visa progress change
- logs the issue
- optionally sends a calm issue email only after repeated failures

This makes the tool more reliable and less alarming for recipients.

# Requirements

You need:

- Python 3.11 or newer
- Docker and Docker Compose if using containers
- an SMTP account for sending email
- internet access

# Quick Start with Docker Compose

This is the easiest and most recommended way to start.

## Step 1 — clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

## Step 2 — copy the example environment file

### Linux/macOS

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

## Step 3 — edit `.env`

Open `.env` and replace fake values with your real values.

## Step 4 — start the application

```bash
docker compose up -d --build
```

## Step 5 — view logs

```bash
docker compose logs -f
```

## Step 6 — stop the application

```bash
docker compose down
```

# Run with Python Directly

If you do not want Docker, you can run it directly with Python.

## Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

## Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.main
```

# Run with GitHub Actions

This project can also run using GitHub Actions.

This is useful when you want:

- scheduled checks
- no always-on machine
- periodic execution in GitHub’s infrastructure

## Important note

GitHub Actions should be used in one-shot mode, not infinite loop mode.

That means:

```env
RUN_ONCE=true
```

The workflow should run once, perform the check, save state, and exit.

# Environment Variables

All configuration is done through environment variables.

## Core settings

### `RUN_ONCE`

Controls whether the app runs once or continuously.

Use:

```env
RUN_ONCE=true
```

for GitHub Actions or one-time testing.

Use:

```env
RUN_ONCE=false
```

for Docker Compose or long-running local/server usage.

### `CHECK_INTERVAL_MINUTES`

The interval between checks when running continuously.

Example:

```env
CHECK_INTERVAL_MINUTES=30
```

### `STATE_FILE`

Path to the JSON state file used for change detection.

Example for Docker Compose:

```env
STATE_FILE=/app/data/visa_tracker_state.json
```

### `ALWAYS_EMAIL`

If true, send email on every successful check.  
If false, send email only when there is a change.

Example:

```env
ALWAYS_EMAIL=false
```

### `REQUEST_TIMEOUT`

HTTP request timeout in seconds.

Example:

```env
REQUEST_TIMEOUT=30
```

### `TIMEZONE`

Timezone used for daily summary logic.

Example:

```env
TIMEZONE=Africa/Tripoli
```

## SMTP settings

### `SMTP_HOST`

SMTP server hostname.

Example:

```env
SMTP_HOST=smtp.gmail.com
```

### `SMTP_PORT`

SMTP server port.

Example:

```env
SMTP_PORT=587
```

### `SMTP_USER`

SMTP username or sender email address.

Example:

```env
SMTP_USER=your-email@gmail.com
```

### `SMTP_PASSWORD`

SMTP password or app password.

Example:

```env
SMTP_PASSWORD=your-app-password
```

### `SMTP_USE_TLS`

Whether to use STARTTLS.

Example:

```env
SMTP_USE_TLS=true
```

### `EMAIL_SUBJECT_PREFIX`

Prefix used in outgoing email subjects.

Example:

```env
EMAIL_SUBJECT_PREFIX=EMGS Tracker
```

## Tracking targets

### `PASSPORTS`

Comma-separated passport numbers.

Example:

```env
PASSPORTS=AF000001,AF000002
```

### `EMAILS`

Comma-separated destination emails.  
Must match the number of passport numbers.

Example:

```env
EMAILS=first@example.com,second@example.com
```

### `NATIONALITY`

Nationality code used in the EMGS form.

Example:

```env
NATIONALITY=LY
```

## Logging settings

### `LOG_LEVEL`

Logging level.

Example:

```env
LOG_LEVEL=INFO
```

Typical values:

- `DEBUG`
- `INFO`
- `WARNING`
- `ERROR`

### `LOG_REQUEST_RESPONSE`

Whether to log request/response details.

Example:

```env
LOG_REQUEST_RESPONSE=false
```

Recommended:

- `false` by default for public/shared setups
- `true` only when debugging

## Daily summary settings

### `DAILY_SUMMARY_ENABLED`

Enable or disable daily summary emails.

Example:

```env
DAILY_SUMMARY_ENABLED=true
```

### `DAILY_SUMMARY_HOUR`

Hour threshold for sending daily summary.

Example:

```env
DAILY_SUMMARY_HOUR=23
```

### `DAILY_SUMMARY_MINUTE`

Minute threshold for sending daily summary.

Example:

```env
DAILY_SUMMARY_MINUTE=55
```

## Temporary issue notification settings

### `ERROR_NOTIFY_ENABLED`

Enable or disable calm issue notification emails.

Example:

```env
ERROR_NOTIFY_ENABLED=false
```

### `ERROR_NOTIFY_AFTER_CONSECUTIVE_FAILURES`

How many temporary failures must happen in a row before sending an issue notification.

Example:

```env
ERROR_NOTIFY_AFTER_CONSECUTIVE_FAILURES=3
```

### `ERROR_NOTIFY_COOLDOWN_HOURS`

How long to wait before sending another issue notification for the same passport.

Example:

```env
ERROR_NOTIFY_COOLDOWN_HOURS=12
```

# Complete `.env` Example

Here is a complete example configuration.

```env
RUN_ONCE=false

CHECK_INTERVAL_MINUTES=30
STATE_FILE=/app/data/visa_tracker_state.json
ALWAYS_EMAIL=false
REQUEST_TIMEOUT=30
TIMEZONE=Africa/Tripoli

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
EMAIL_SUBJECT_PREFIX=EMGS Tracker

PASSPORTS=AF000001,AF000002
EMAILS=first@example.com,second@example.com
NATIONALITY=LY

LOG_LEVEL=INFO
LOG_REQUEST_RESPONSE=false

DAILY_SUMMARY_ENABLED=true
DAILY_SUMMARY_HOUR=23
DAILY_SUMMARY_MINUTE=55

ERROR_NOTIFY_ENABLED=false
ERROR_NOTIFY_AFTER_CONSECUTIVE_FAILURES=3
ERROR_NOTIFY_COOLDOWN_HOURS=12
```

# Docker Setup Details

## `Dockerfile`

A typical Dockerfile for this project should look like this:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app.main"]
```

## `docker-compose.yml`

A typical `docker-compose.yml` should look like this:

```yaml
version: "3.9"

services:
  emgs-tracker:
    build: .
    container_name: emgs-tracker
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    command: ["python", "-m", "app.main"]
```

### Why mount `./data:/app/data`?

Because the state file must survive container restarts.

Without that volume, the JSON state file inside the container may disappear when the container is recreated.

# GitHub Actions Setup Details

If you want to run the project using GitHub Actions, follow these steps.

## Step 1 — create the workflow file

Create:

```text
.github/workflows/emgs-tracker.yml
```

Use your workflow file from the repository.

## Step 2 — add repository secrets

Go to:

- GitHub repository
- Settings
- Secrets and variables
- Actions

Add these secrets:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `EMAIL_SUBJECT_PREFIX`
- `PASSPORTS`
- `EMAILS`
- `NATIONALITY`
- `ALWAYS_EMAIL`
- `REQUEST_TIMEOUT`
- `LOG_LEVEL`
- `LOG_REQUEST_RESPONSE`
- `DAILY_SUMMARY_ENABLED`
- `DAILY_SUMMARY_HOUR`
- `DAILY_SUMMARY_MINUTE`
- `TIMEZONE`
- `ERROR_NOTIFY_ENABLED`
- `ERROR_NOTIFY_AFTER_CONSECUTIVE_FAILURES`
- `ERROR_NOTIFY_COOLDOWN_HOURS`

## Step 3 — set `RUN_ONCE=true`

In GitHub Actions mode, the app should run once per workflow execution.

## Step 4 — trigger manually or on schedule

You can:

- run manually from the Actions tab
- let cron schedule run it

Example cron:

```yaml
on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:
```

## Step 5 — state persistence in GitHub Actions

Because GitHub Actions runners are ephemeral, the workflow should commit the updated state file back into the repository after the run.

That is why your workflow includes a step that commits `data/visa_tracker_state.json`.

# State File and Persistence

The tracker uses a JSON state file to remember the last known result.

This file is important for:

- change detection
- daily summary tracking
- temporary issue tracking

Typical path:

```env
STATE_FILE=/app/data/visa_tracker_state.json
```

## Important note

If the state file is lost, the next successful run may be treated as a first run.

That can cause:

- an email to be sent even though nothing changed since the user’s perspective

This is why persistence matters.

# Making the Repository Public Safely

If you want to make the repository public, do not do it immediately without cleanup.

You should first:

- disable GitHub Actions temporarily
- rotate any exposed secrets
- remove `.env` from git
- remove `data/visa_tracker_state.json` from git
- clean git history if real personal data was ever committed
- verify `.env.example` contains only fake values
- verify README contains no real emails, passports, or secrets
- make repo public
- re-enable Actions only if needed

# How to Clean Sensitive Files from Git History

Deleting a file from the current branch is not enough if it was committed before.

Sensitive files remain in git history unless you rewrite history.

Typical files to remove:

- `.env`
- `data/visa_tracker_state.json`
- any sample files with real names/passports/emails
- any logs containing sensitive information

## Remove tracked copies from the current repo

```bash
git rm --cached .env
git rm --cached data/visa_tracker_state.json
```

## Add them to `.gitignore`

```gitignore
.env
data/visa_tracker_state.json
__pycache__/
*.pyc
```

## Rewrite history using `git-filter-repo`

If the files were ever committed before:

```bash
git filter-repo --path .env --invert-paths
git filter-repo --path data/visa_tracker_state.json --invert-paths
```

Then force-push:

```bash
git push --force --all
git push --force --tags
```

## Easier alternative

If you do not care about preserving old private history publicly, the easiest and safest option is:

- create a brand new clean public repository
- copy only the sanitized project files into it
- commit once from a clean state

# How to Install `git-filter-repo` on Windows

You saw this error:

```text
git: 'filter-repo' is not a git command.
```

That means `git-filter-repo` is not installed.

## Easiest way with pip

Open PowerShell and run:

```powershell
python -m pip install git-filter-repo
```

Then close and reopen PowerShell and check:

```powershell
git filter-repo --help
```

If it works, you can then run:

```powershell
git filter-repo --path .env --invert-paths
git filter-repo --path data/visa_tracker_state.json --invert-paths
```

## If pip install still does not make it available

You can use Python directly:

```powershell
python -m git_filter_repo --help
```

Or use the official standalone script installation method.

# Recommended Public Release Process

This is the recommended order for publishing safely.

## Option A — safest route: create a new clean public repo

- disable Actions in the old/private repo
- rotate SMTP/app password
- make sure `.env` and state files are ignored
- create a new empty GitHub repository
- copy only sanitized files into the new folder
- initialize git
- push clean history

Commands:

```bash
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_NEW_REPO.git
git push -u origin main
```

This avoids any old leaked history.

## Option B — keep same repo and rewrite history

- disable Actions
- rotate secrets
- install `git-filter-repo`
- remove sensitive files from history
- force-push
- verify clean history
- make repo public

# Troubleshooting

## First run sends an email even when `ALWAYS_EMAIL=false`

This is expected.

Reason:

- there is no previous state yet
- the first valid successful result is treated as a change

## The tracker keeps emailing changes even when nothing changed

Usually means the state file is not being persisted correctly.

Check:

- volume mapping in Docker Compose
- `STATE_FILE` path
- whether `data/visa_tracker_state.json` exists and is updated

## Daily summary did not send

Check:

- `DAILY_SUMMARY_ENABLED=true`
- `ALWAYS_EMAIL=false`
- the application actually ran after the configured summary time
- no percentage change happened that day

## Emails are not sent

Check:

- SMTP host
- SMTP port
- SMTP username
- SMTP password
- app password validity
- `SMTP_USE_TLS`
- provider restrictions

## GitHub Actions fails with config parsing errors

Usually means one of the secrets is empty.

Check especially numeric values:

- `SMTP_PORT`
- `REQUEST_TIMEOUT`
- `DAILY_SUMMARY_HOUR`
- `DAILY_SUMMARY_MINUTE`
- `ERROR_NOTIFY_AFTER_CONSECUTIVE_FAILURES`
- `ERROR_NOTIFY_COOLDOWN_HOURS`

## Temporary EMGS/provider errors appear

This usually means the EMGS site or one of its backend providers is temporarily unavailable.

The tracker should:

- not crash
- keep previous state
- log the issue
- optionally notify only after repeated failures

# How Anyone Can Use or Fork This Project

A new user can start in two common ways.

## Option 1 — use Docker Compose

- fork the repository or clone it
- copy `.env.example` to `.env`
- fill in real values
- run:

```bash
docker compose up -d --build
```

## Option 2 — use GitHub Actions

- fork the repository
- add all required GitHub Actions secrets
- make sure workflow file exists
- run the workflow manually
- optionally enable schedule

# Step-by-Step for a New User Using Docker

## Linux/macOS

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f
```

## Windows PowerShell

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
Copy-Item .env.example .env
notepad .env
docker compose up -d --build
docker compose logs -f
```

# Step-by-Step for a New User Using GitHub Actions

1. Fork the repository.
2. Go to the forked repo.
3. Open **Settings**.
4. Open **Secrets and variables**.
5. Open **Actions**.
6. Add all required secrets.
7. Open **Actions**.
8. Select **EMGS Tracker**.
9. Click **Run workflow**.

If they want periodic runs, they keep the cron schedule enabled.

# Contribution Ideas

Possible future improvements:

- unit tests for HTML parsing
- integration tests using sanitized sample HTML
- retry/backoff strategy for temporary outages
- pluggable storage backends beyond JSON
- support for other notification channels
- CI checks for linting and tests
- cleaner CLI mode
- dashboard or admin UI
- export status to a database
- package publishing

# Security Notes

This project may handle sensitive personal data.

Recommendations:

- never commit `.env`
- never commit real state files
- never commit real logs
- rotate any exposed credentials immediately
- use SMTP app passwords instead of main account passwords
- avoid verbose request/response logging in public environments
- sanitize demo data in `.env.example`

If you make the repository public, make sure:

- your git history is clean
- workflow logs are safe
- no real passport numbers remain in the repo

# Disclaimer

This is an unofficial tracker for the EMGS application status page.

It depends on:

- third-party HTML structure
- EMGS availability
- backend/provider availability

If the EMGS website changes its page structure or backend behavior, the parser may need updates.

This project is provided as a convenience tool and should be used responsibly.

## License

This project is licensed under the MIT License.

```text
MIT License

Copyright (c) 2026 Muhanad Balam

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
