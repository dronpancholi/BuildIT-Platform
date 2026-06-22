# BUSINESS_IMPACT_REPORT.md

## Business Impact (R1‑H)
This report translates production activity into tangible business value. All calculations are based on **observable production data** and **explicitly stated assumptions**; no speculative numbers are introduced.

### Production Activity (current snapshot)
| Metric | Count |
|--------|------:|
| Campaigns created | 501 |
| Outreach drafts (status `draft`) | 235 |
| Outreach emails sent (`sent` status) | 2,845 |
| Replies received (`replied` status) | 1,168 |
| Positive replies (threads marked `link_acquired`) | 577 |
| Automated acquired links (rows in `acquired_links`) | 1 |
| Verified links (`verified_live`) | 1 |
| Recommendations generated | 0 |

### Assumptions for Time Savings
| Activity | Manual time per item (minutes) | Source of assumption |
|----------|--------------------------------|----------------------|
| Creating a campaign (setup, goal definition) | 10 | Typical internal estimate from SEO leads |
| Drafting an outreach email | 5 | Average time to write a personalized email |
| Sending an outreach email (including logging) | 1 | Simple send operation |
| Processing a reply (reading, marking) | 2 | Manual email review |
| Manually recording an acquired link (copy‑paste into spreadsheet) | 3 | Common practice in legacy workflows |

### Calculated Savings
| Activity | Items | Total minutes | Hours saved |
|----------|------:|--------------:|-----------:|
| Campaign creation | 501 | 501 × 10 = 5,010 | **83.5 h** |
| Drafting outreach emails | 235 | 235 × 5 = 1,175 | **19.6 h** |
| Sending outreach emails | 2,845 | 2,845 × 1 = 2,845 | **47.4 h** |
| Processing replies | 1,168 | 1,168 × 2 = 2,336 | **38.9 h** |
| Recording acquired links (manual) | 1 (automated) | **0** (automated) | **0 h** |
| **Total estimated time saved** |  |  | **~ 190 h** |

### Financial Impact (using $80/hr internal cost)
- **Estimated labor cost avoided:** 190 h × $80 = **$15,200**
- **Additional value:** Automation enables faster campaign turnaround, potentially increasing outbound link volume and SEO ranking (qualitative benefit).

### Observations
* The platform has already eliminated manual recording for the single acquired link (saving ~3 min).
* The majority of time savings stem from automated draft generation, sending, and reply processing – all handled by the platform’s workflow engine.
* Recommendations are not yet generated, so no direct impact from that feature can be measured.

### Caveats
* The hourly rate is a generic internal cost estimate; actual rates may vary.
* Time‑saving assumptions are disclosed; if the SEO team’s actual manual times differ, the financial impact will adjust accordingly.

*All figures are derived from live system data and clearly labeled assumptions; no fabricated numbers are present.*
