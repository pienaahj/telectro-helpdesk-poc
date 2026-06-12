#!/usr/bin/env bash
set -euo pipefail

# Production host preflight.
#
# Read-only diagnostics for AlmaLinux / Red Hat-style Docker host.
# This script should not mutate the host.

section() {
  printf "\n==> %s\n" "$*"
}

run_optional() {
  printf "\n$ %s\n" "$*"
  "$@" || true
}

section "User / host"
run_optional whoami
run_optional id
run_optional hostname
run_optional pwd

section "OS"
run_optional cat /etc/os-release
run_optional uname -a
run_optional hostnamectl

section "Package manager"
run_optional dnf --version
run_optional yum --version

section "Docker"
run_optional docker --version
run_optional docker compose version
run_optional systemctl status docker --no-pager
run_optional docker ps

section "Firewall"
run_optional systemctl status firewalld --no-pager
run_optional firewall-cmd --state
run_optional firewall-cmd --list-all

section "SELinux"
run_optional getenforce
run_optional sestatus

section "Storage"
run_optional df -h
run_optional lsblk
run_optional mount

section "Kernel / container runtime tuning"
run_optional sysctl vm.overcommit_memory

section "Network basics"
run_optional ip addr
run_optional ip route
run_optional getent hosts github.com
run_optional getent hosts registry-1.docker.io

section "Repository state"
if [[ -d .git ]]; then
  run_optional git status --short
  run_optional git branch --show-current
  run_optional git log --oneline -1
else
  echo "Not currently inside a git repository."
fi

section "Preflight complete"

cat <<'EOF'

Review notes:
- Any Docker failure is a host readiness blocker.
- Any firewalld/SELinux restriction should be handled by Telectro/infrastructure owner.
- Redis expects vm.overcommit_memory=1 for production-grade reliability.
- This script does not prove the app deploys.
- This script only proves basic host visibility.
EOF
