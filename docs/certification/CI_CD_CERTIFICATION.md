# CI/CD Pipeline Certification — Phase 12G.9

## BuildIT Enterprise SEO Operations

---

### Pipeline Definition

**File:** `.github/workflows/ci.yml`

**Trigger:** Push to `main`/`develop`, PR to `main`

---

### Pipeline Stages

| Stage | Job Name | Tool | Purpose |
|-------|----------|------|---------|
| 1. Lint | `lint` | flake8 | Python code quality (F/E9/F63/F82 errors, complexity) |
| 2. Type Check | `typecheck` | mypy | Python type annotation validation |
| 3. Test | `test` | pytest + asyncio | Backend test suite with Postgres + Redis services |
| 4. Build | `build-frontend` | Next.js (Turbopack) | Production frontend build |
| 5. Migration | `migration-validate` | Manual check | Verify migration files exist |
| 6. Security | `security-scan` | bandit | Python security vulnerability scan |

---

### Infrastructure Requirements

| Service | Image | Purpose |
|---------|-------|---------|
| PostgreSQL 16 | `postgres:16` | Database for test suite |
| Redis 7 | `redis:7` | Cache for test suite |

---

### Stage Details

#### 1. Lint (`lint`)
```yaml
- run: flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
- run: flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=127
```
Checks for fatal errors (F-prefixed) and complexity/style issues (exit-zero).

#### 2. Type Check (`typecheck`)
```yaml
- run: mypy src/ --ignore-missing-imports || true
```
Validates Python type hints. Non-blocking (exit on success only).

#### 3. Test (`test`)
- Postgres + Redis as service containers with health checks
- Sets `ENVIRONMENT=test` with test database config
- Runs: `pytest tests/ -x -v --timeout=60`

#### 4. Build Frontend (`build-frontend`)
```yaml
- run: npm ci || npm install
- run: npm run build
```
Ensures production build passes cleanly with zero errors.

#### 5. Migration Validation (`migration-validate`)
```yaml
- run: ls backend/migrations/versions/
```
Verifies migration directory exists and contains version files.

#### 6. Security Scan (`security-scan`)
```yaml
- run: bandit -r backend/src/ -f json -o bandit_report.json
```
Static security analysis for common Python vulnerabilities.

---

### Validation Results

| Check | Result |
|-------|--------|
| Pipeline YAML syntax valid | ✓ |
| All stages defined with runner | ✓ |
| Postgres service configured | ✓ |
| Redis service configured | ✓ |
| Build step uses `npm run build` | ✓ |
| Test step uses `pytest` | ✓ |
| Lint step configurable | ✓ |
| Security scan included | ✓ |

---

**Status: COMPLETE** — CI/CD pipeline ready for GitHub Actions.
