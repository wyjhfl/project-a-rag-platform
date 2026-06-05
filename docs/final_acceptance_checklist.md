# Final Acceptance Checklist

## Pre-flight Checks (MUST pass before any other step)

- [ ] Python executable available
- [ ] npm executable available
- [ ] Docker available (`docker --version`)
- [ ] Docker Compose available (`docker compose version`)

## Core Tests

- [ ] Backend core tests: `python -m pytest backend/tests/test_api.py backend/tests/test_auth.py backend/tests/test_health_readiness.py backend/tests/test_phase1_security.py backend/tests/test_phase2_observability_audit.py backend/tests/test_phase3_deployment_storage.py backend/tests/test_phase4_jobs.py backend/tests/test_production_landing.py -q`
- [ ] Full backend tests: `python -m pytest backend/tests -q`
- [ ] Ruff: `python -m ruff check backend`

## Frontend

- [ ] Build: `cd frontend && npm run build`
- [ ] OpenAPI types: `cd frontend && npm run api:types`
- [ ] E2E list: `cd frontend && npm run e2e -- --list`

## Docker

- [ ] Production config: `docker compose config`
- [ ] Demo config: `docker compose -f docker-compose.demo.yml config`

## Security

- [ ] Secret scan: `python scripts/secret_scan.py --dir .`

## Automated Script

Run: `powershell -ExecutionPolicy Bypass -File .\scripts\final_acceptance.ps1`

**Note**: Docker is a mandatory pre-flight check. If Docker is not available, the script exits with code 1.
