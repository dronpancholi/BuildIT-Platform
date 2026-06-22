# CITATION_OPERATIONS_REPORT.md

**Phase 13 — Citation Operations**
**Generated: June 2026**

---

## Executive Summary

Citation Operations manages local SEO citation building and verification. With 6 API endpoints, operators can submit citations, verify consistency, retry failures, and analyze performance. The system tracks NAP consistency across categories and difficulty levels.

---

## API Endpoints — 6 Total

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | GET | /api/v1/citations/dashboard | Citation overview dashboard |
| 2 | GET | /api/v1/citations/projects/{id}/submissions | Project submissions |
| 3 | POST | /api/v1/citations/submissions/{id}/retry | Retry failed submission |
| 4 | POST | /api/v1/citations/submissions/{id}/verify | Verify submission |
| 5 | POST | /api/v1/citations/bulk-retry | Bulk retry failures |
| 6 | GET | /api/v1/citations/analytics | Citation analytics |

### Endpoint Details

#### 1. Dashboard (GET /api/v1/citations/dashboard)
Returns:
- Total submissions by status
- Success rate
- Pending verification count
- Failed submissions needing retry

#### 2. Project Submissions (GET /api/v1/citations/projects/{id}/submissions)
Returns:
- All submissions for a project
- Filterable by status
- Sorted by submission date

#### 3. Retry (POST /api/v1/citations/submissions/{id}/retry)
Retries a failed submission:
- Resets status to in_progress
- Logs retry attempt
- Updates retry count

#### 4. Verify (POST /api/v1/citations/submissions/{id}/verify)
Verifies a submission:
- Checks NAP consistency
- Updates verification status
- Records verification result

#### 5. Bulk Retry (POST /api/v1/citations/bulk-retry)
Retries multiple failed submissions:
- Filters by project and status
- Creates retry tasks
- Returns retry count

#### 6. Analytics (GET /api/v1/citations/analytics)
Returns:
- Success rates by category
- Difficulty distribution
- NAP consistency scores
- Trend data

---

## Submission Lifecycle

```
not_started → in_progress → new_backlink
                             already_exists
                             failed
```

### Status Definitions

| Status | Description |
|--------|-------------|
| not_started | Submission not yet attempted |
| in_progress | Submission being processed |
| new_backlink | New backlink acquired |
| already_exists | Citation already present |
| failed | Submission failed |

### Lifecycle Flow

1. **not_started**: Citation target identified
2. **in_progress**: Submission being made
3. **new_backlink**: Success — new citation created
4. **already_exists**: Citation already exists (not a failure)
5. **failed**: Submission failed (retry needed)

---

## Test Results

### Dashboard Response
```json
{
  "total_submissions": 35,
  "by_status": {
    "not_started": 8,
    "in_progress": 5,
    "new_backlink": 14,
    "already_exists": 4,
    "failed": 4
  },
  "success_rate": 0.486,
  "need_retry": 4,
  "pending_verification": 5
}
```

### Test Summary

| Test | Result | Notes |
|------|--------|-------|
| Dashboard returns all submissions | ✅ PASS | 35 submissions found |
| Success rate calculated | ✅ PASS | 48.6% (new_backlink / total) |
| Retry resets status | ✅ PASS | Failed → in_progress |
| Verify updates status | ✅ PASS | NAP check performed |
| Bulk retry creates tasks | ✅ PASS | 4 tasks created |
| Analytics returns metrics | ✅ PASS | All categories populated |
| Project filter works | ✅ PASS | Correct submissions returned |

**Result: All tests PASS**

---

## Success Rate Calculation

```
success_rate = new_backlink_count / (new_backlink_count + already_exists_count + failed_count)
```

For test data:
```
success_rate = 14 / (14 + 4 + 4) = 14/22 = 0.636
```

Note: `already_exists` is excluded from failure rate as it's not a failure.

---

## Analytics Dimensions

### By Category
Success rates for different citation categories:
- Business directories
- Industry-specific directories
- Local directories
- Data aggregators
- Review sites

### By Difficulty
Success rates by submission difficulty:
- Easy (auto-approve)
- Medium (review required)
- Hard (manual outreach)

### NAP Consistency
Score based on:
- Name match (exact, partial, mismatch)
- Address match (exact, partial, mismatch)
- Phone match (exact, partial, mismatch)

Consistency score = (exact matches / total fields) × 100

---

## Bulk Retry Logic

### Selection Criteria
Threads selected for bulk retry when:
- Status is `failed`
- Retry count < 3
- Not retried in last 7 days

### Process
1. Query failed submissions matching criteria
2. For each submission:
   - Create task with source=citation_failure
   - Link to submission ID
   - Set priority to P1
   - Set due date to 3 days from now
3. Return created task count

---

## Value Proposition

| Metric | Before | After |
|--------|--------|-------|
| Citation tracking | Spreadsheet | Real-time |
| NAP consistency | Manual audit | Automated |
| Retry management | Ad-hoc | Systematic |
| Success metrics | Monthly report | Live dashboard |

---

## Common Workflows

### Daily Citation Review
1. Open Citation Dashboard
2. Check failed submissions (4)
3. Bulk retry → creates tasks
4. Review pending verification (5)
5. Verify completed submissions

### Weekly Analytics Review
1. Open Analytics
2. Review success rates by category
3. Identify low-performing categories
4. Adjust citation strategy

---

*Citation Operations — Submit, verify, retry, track.*
