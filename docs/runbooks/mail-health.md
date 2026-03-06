# Mail Health Runbook (Pilot)

Goal: avoid silent failures in email intake. This runbook gives quick “is it alive?” checks and a deterministic smoke test.

## What “healthy” looks like

- Scheduled Job Type exists and is enabled for the site: `pull_pilot_inboxes.run`
- Recent successful runs (no repeated exceptions)
- Redis / breadcrumbs (if used) show progress (UIDNEXT / last run markers)
- A test email produces either:
  - a new HD Ticket, or
  - a logged Communication with clear failure reason

## Quick UI checks

1. **Scheduled Job Type**
   - Search: `Scheduled Job Type`
   - Find: `pull_pilot_inboxes.run`
   - Confirm:
     - Enabled
     - Frequency is correct (whatever you set for pilot)
2. **Error Log**
   - Check for repeated errors around the expected run times
3. **Email Account**
   - Ensure the inbox account is enabled and credentials are valid

## Deterministic smoke test (preferred)

Run the proof script in bench:

```python
from telephony.scripts.proof_mail_health import run
run(site="frontend")
```

