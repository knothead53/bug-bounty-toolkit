# Bug Bounty Toolkit — Passive Recon MVP

Purpose: safe, documented toolkit for passive reconnaissance and report generation.

Usage:
  python src/bbt/cli.py init-scope example.com -o output

Check live hosts:
  python -m bbt.cli check-live output/example.com_scope.json -o output -w 4

  Run UI: uvicorn bbt.webapp.app:app --reload

Safety: Passive-only (crt.sh). Do not run active scans without explicit written authorization.