# Engineering Onboarding

Welcome to the team. This document covers everything you need to get set up.

## Setup

### Environment Variables

You'll need to set the following environment variables before running the app locally:

- `DATABASE_URL` — connection string for the primary Postgres instance
- `REDIS_URL` — used for caching and session storage
- `API_SECRET_KEY` — used to sign internal service tokens, rotate every 90 days

Never commit these to version control. Use the `.env.local` file, which is gitignored.

### Local Development

Run `make setup` to install dependencies and spin up local services via Docker Compose.
This starts Postgres, Redis, and the API server on port 8000.

## Deployment

### Staging

Every merge to `main` auto-deploys to staging within about 5 minutes. Staging uses
a separate database from production and is safe to break.

### Production

Production deploys require a manual approval step in the CI pipeline. Only deploy
during business hours unless it's a hotfix, and always post in #deploys when you do.

## Incident Response

If you notice an outage, page the on-call engineer via PagerDuty first, then post
in #incidents with what you're seeing. Don't try to fix production issues solo if
you're new — pair with someone on-call.
