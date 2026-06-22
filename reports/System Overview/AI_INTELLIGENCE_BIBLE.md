# PROJECT 31A — AI & INTELLIGENCE ARCHITECTURE BIBLE (DOCUMENT 10)
## Version 1.0.0
## Classification: CONFIDENTIAL — FOR INTERNAL DEVELOPMENT AND DUE DILIGENCE ONLY

---

## 1. AI CORE PRINCIPLE & ARCHITECTURE AXIOM

Project 31A utilizes a hybrid architectural model combining generative artificial intelligence with deterministic workflow state machines. The system is designed to prevent AI model hallucinations from causing operational defects. This paradigm is summarized in the platform's core axiom:

> **"AI proposes. Deterministic systems execute. Reliability is the product."**

```
                    ┌────────────────────────┐
                    │      AI Proposes       │
                    │   (LLM Output JSON)    │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │      Verification      │
                    │   (Pydantic / Regex)   │
                    └───────────┬────────────┘
                                │ Validated
                                ▼
                    ┌────────────────────────┐
                    │  Deterministic Exec    │
                    │  (Temporal / Postgres) │
                    └────────────────────────┘
```

1. **AI Proposes:** The LLM receives instructions, scraped web content, and client guidelines. It outputs suggestions in structured JSON format (e.g. prospect scores, email templates, keyword tags).
2. **Verification:** The API / Worker parsing layer validates the JSON structure against strict schemas (Pydantic, regex boundaries).
3. **Execution:** The validated payload is processed by deterministic workflows (Temporal, PostgreSQL) which handle database writes, api calls, and email dispatch. The AI has no direct access to write to database tables or execute external mutations without passing through these deterministic validation gates.

---

## 2. LLM GATEWAY PIPELINE

The core gateway managing LLM interactions is defined in `backend/src/seo_platform/llm/gateway.py`. The gateway wraps all NVIDIA NIM model calls and processes them through an 11-step execution pipeline.

```
Request ──► Task Classify ──► Kill Switch Check ──► Governance Interceptor ──► Rate Limiter
                                                                                    │
                                                                                    ▼
Confidence Score ◄── Governance Validate ◄── Structured Validate ◄── Model Router / Call
   │
   ▼
Approval Gate ──► Deterministic Execution
```

### 2.1 Pipeline Lifecycle Steps
1. **Request Ingestion:** Accepts task input payload, system instructions, and target output schema definition.
2. **Task Classification:** Identifies the type of task (e.g. `SEO_ANALYSIS`, `KEYWORD_CLUSTERING`, `INFRASTRUCTURE_DIAGNOSTICS`) to determine model routing.
3. **Kill Switch Check:** Queries Redis to verify `llm_inference` has not been administratively blocked.
4. **Governance Interceptor:** Scrubs the input payload of sensitive tenant identification variables or client PII data.
5. **Rate Limiter:** Checks the tenant-level Redis token bucket to prevent model cost exhaustion.
6. **Model Router:** Selects the optimal model from the active NIM matrix based on task type.
7. **NIM Model Execution:** Submits requests via gRPC/REST endpoints to the local NVIDIA NIM instance.
8. **Structured Validation:** Parses the raw text output into JSON format and validates it against the designated Pydantic schema class.
9. **Governance Validation:** Evaluates content against safety filters (e.g. checking for generic templates, empty tags, or forbidden words).
10. **Confidence Scoring:** Calculates an output validity rating (0.0 to 1.0) based on validation errors and fallback attempts.
11. **Orchestrator Return:** Returns the validated object to the calling activity or service.

---

## 3. MODEL MATRIX & ROUTING MATRIX

The platform leverages specialized open-source models deployed via **NVIDIA NIM** to optimize cost, latency, and capability matching.

### 3.1 Model Key Registry
- **`ORCHESTRATION`:** `DeepSeek-V4-Pro` (managed by `settings.nvidia.orchestration_model`).
- **`OPERATIONAL_UTILITY`:** `Gemma 4 31B IT` (managed by `settings.nvidia.seo_model`).
- **`LONG_CONTEXT_MEMORY`:** `MiniMax M2.7` (managed by `settings.nvidia.memory_model`).
- **`INFRASTRUCTURE_INTELLIGENCE`:** `NVIDIA-Nemotron-3-Super-120B-A12B` (managed by `settings.nvidia.infra_model`).
- **`EMBEDDING`:** `nvidia/nv-embedqa-e5-v5` (managed by `settings.nvidia.embedding_model`).

### 3.2 Task-to-Model Routing Matrix
Tasks are automatically routed based on their classification:
- **`WORKFLOW_ORCHESTRATION` / `ENTERPRISE_REPORTING` / `OPERATIONAL_GOVERNANCE`:** Defer to `ORCHESTRATION` (DeepSeek).
- **`SEO_ANALYSIS` / `KEYWORD_CLUSTERING` / `FRONTEND_UI_REASONING` / `APPROVAL_SUMMARIES`:** Defer to `OPERATIONAL_UTILITY` (Gemma).
- **`WORKFLOW_REPLAY` / `HISTORICAL_ANALYSIS`:** Defer to `LONG_CONTEXT_MEMORY` (MiniMax).
- **`INFRASTRUCTURE_DIAGNOSTICS` / `ANOMALY_REASONING` / `SYSTEMS_OPTIMIZATION`:** Defer to `INFRASTRUCTURE_INTELLIGENCE` (Nemotron).
- **`EMBEDDING_GENERATION`:** Defer to `EMBEDDING` (nv-embedqa-e5-v5).
- **`ENTERPRISE_ECOSYSTEM_ANALYSIS` / `CROSS_TENANT_ANALYTICS`:** Defer to `ORCHESTRATION` (DeepSeek).

---

## 4. LLM FALLBACK STRATEGY

To maintain high platform availability, the LLM gateway implements a structured model fallback loop.

```
       ┌────────────────────────┐
       │   Selected NIM Model   │
       └───────────┬────────────┘
                   │
                   ├─► Success ──────────────────► Output
                   │
                   └─► Failure / 503 / 429
                               │
                               ▼
                   ┌────────────────────────┐
                   │   Primary Fallback     │
                   └───────────┬────────────┘
                               │
                               ├─► Success ──────► Output
                               │
                               └─► Failure / 503 / 429
                                           │
                                           ▼
                               ┌────────────────────────┐
                               │   Secondary Fallback   │
                               │  (NIM General Model)   │
                               └────────────────────────┘
```

1. **Selected Model:** The gateway attempts to contact the optimal NIM model.
2. **Primary Fallback:** If the selected model returns an HTTP 503, 429, or network timeout, the request falls back:
   - `ORCHESTRATION` falls back to `INFRASTRUCTURE_INTELLIGENCE`.
   - `OPERATIONAL_UTILITY` falls back to `ORCHESTRATION`.
   - `LONG_CONTEXT_MEMORY` falls back to `INFRASTRUCTURE_INTELLIGENCE`.
   - `INFRASTRUCTURE_INTELLIGENCE` falls back to `ORCHESTRATION`.
3. **Secondary Fallback:** If both fail, the request falls back to a general instance (e.g. DeepSeek base model).
4. **Final Fail-Loud:** If all fallbacks fail, the gateway raises `LlmGatewayFailureException` to halt execution.

---

## 5. STRUCTURED VALIDATION & SCHEMAS

All LLM calls enforce structured outputs using Pydantic validation schemas.

### 5.1 Outreach Email Validation Schema
```python
class OutreachEmailSchema(BaseModel):
    subject: str = Field(..., max_length=500)
    body_html: str = Field(...)
    personalization_variables: dict[str, str]
    grounding_ratio: float = Field(..., description="Ratio of scraped page facts utilized")
    
    @field_validator("body_html")
    @classmethod
    def check_boilerplate(cls, v: str) -> str:
        forbidden_phrases = [
            "hope this email finds you well",
            "just checking in",
            "dear webmaster",
            "advertise on your site"
        ]
        for phrase in forbidden_phrases:
            if phrase in v.lower():
                raise ValueError(f"Boilerplate phrase detected: '{phrase}'")
        return v
```

### 5.2 Confidence Scoring Matrix
The gateway evaluates the validity of LLM-generated output by calculating a confidence score:
- **`Structured Parse Success`:** +0.5
- **`Validation Schema Match (No Warnings)`:** +0.3
- **`Grounding Ratio >= 0.20`:** +0.2
- **`Fallback Model Used`:** -0.25
- **`Boilerplate Phrase Match`:** -0.5

If the calculated score is `< 0.60`, the output is rejected and the gateway triggers a retry.
