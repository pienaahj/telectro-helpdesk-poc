#!/usr/bin/env bash
set -euo pipefail

git restore \
  apps/telephony/telephony/fixtures/hd_team.json \
  apps/telephony/telephony/fixtures/hd_ticket_type.json \
  apps/telephony/telephony/fixtures/scheduled_job_type.json \
  apps/telephony/telephony/fixtures/report.json \
  apps/telephony/telephony/fixtures/role_profile.json
