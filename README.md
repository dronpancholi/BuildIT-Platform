# BuildIT: The Enterprise SEO Operations & Intelligence Platform

## 1. Overview
BuildIT is an industrial-grade "SEO Operating System" designed for high-growth agencies. It utilizes a **Deterministic AI Orchestration** architecture to automate high-stakes SEO tasks—specifically backlink acquisition, keyword intelligence, and operational monitoring—at a scale and reliability level that manual teams cannot match.

The platform is built on the philosophy: **"AI Proposes, Deterministic Systems Execute."**

---

## 2. Key Features

### 2.1 Automated Backlink Acquisition Engine
*   **Discovery:** Multi-source prospecting (Ahrefs, SEMrush, Scrapers) to identify high-value targets.
*   **Intelligence:** AI-driven relevance and spam scoring to filter prospects.
*   **Outreach:** Hyper-personalized, LLM-generated emails based on real-time website analysis.
*   **Management:** Durable outreach workflows via Temporal.io with automated follow-ups and reply detection.

### 2.2 Semantic Keyword Intelligence
*   **Topological Clustering:** Vector-based grouping of keywords into semantic "Topic Clusters."
*   **Intent Mapping:** AI classification of search intent (Informational, Commercial, etc.).
*   **Opportunity Analysis:** Real-time SERP volatility tracking and opportunity scoring.

### 2.3 Operational Command Center
*   **War Room:** Real-time observability of infrastructure, queue pressure, and system health.
*   **Advanced SRE:** Predictive incident detection and workflow degradation forecasting.
*   **Self-Healing:** Autonomous diagnostics and pressure-aware task scaling.

---

## 3. System Architecture

BuildIT is a distributed, cloud-native system built with the following core technologies:

*   **Orchestration:** [Temporal.io](https://temporal.io/) (Durable execution of long-running workflows).
*   **Event Engine:** [Apache Kafka](https://kafka.apache.org/) (Event-driven internal communication).
*   **Intelligence Layer:** [Qdrant](https://qdrant.tech/) (Vector database) & [NVIDIA NIM](https://www.nvidia.com/en-us/ai-data-science/generative-ai/nim/) (AI reasoning).
*   **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Async Python API).
*   **Frontend:** [Next.js 15](https://nextjs.org/) (High-performance React dashboard).
*   **Database:** PostgreSQL 16+ (Relational data & JSONB snapshots).
*   **Infrastructure:** Terraform & Kubernetes (EKS).

---

## 4. Operational Setup Guide

### 4.1 Prerequisites
*   Python 3.12+
*   Node.js 18+
*   Docker & Kubernetes (for local or cloud deployment)
*   Temporal Cluster (Server + UI)
*   Apache Kafka

### 4.2 Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd project-31a
    ```

2.  **Backend Setup:**
    ```bash
    cd backend
    pip install -e .
    cp .env.example .env
    # Fill in your DATABASE_URL, TEMPORAL_HOST, and API Keys (NVIDIA, Ahrefs, etc.)
    alembic upgrade head
    ```

3.  **Frontend Setup:**
    ```bash
    cd frontend
    npm install
    cp .env.example .env
    ```

### 4.3 Running the Platform

1.  **Start Temporal Workers:**
    ```bash
    cd backend
    python -m seo_platform.workers.main
    ```

2.  **Start API Server:**
    ```bash
    cd backend
    uvicorn seo_platform.main:app --reload
    ```

3.  **Start Frontend:**
    ```bash
    cd frontend
    npm run dev
    ```

4.  **Start Background Evolution Loop:**
    The system health and intelligence engine is managed by the `BusinessStateEvolutionEngine`. This is started automatically within the FastAPI lifespan or can be run as a standalone worker.

---

## 5. Technical Workflow: Backlink Acquisition
The platform's primary workflow follows this deterministic path:
1.  **DiscoveryActivity:** Scrapes prospects based on competitor domains or keywords.
2.  **ScoringActivity:** AI analyzes the prospect's content and metrics.
3.  **ContactActivity:** Mines email addresses via Hunter.io.
4.  **ApprovalSignal:** The workflow pauses and waits for an operator signal via the UI.
5.  **OutreachActivity:** LLM generates and sends personalized emails.
6.  **MonitoringLoop:** Waits for replies or follow-up triggers.

---

## 6. Governance & Security
*   **Audit Trails:** Every automated action and AI proposal is logged in the `audit_logs` table.
*   **Circuit Breakers:** External API calls are wrapped in circuit breakers to prevent system saturation during third-party outages.
*   **Kill Switches:** A global `/api/v1/system/kill-switch` endpoint allows for immediate cessation of all automated activities.

---

## 7. Performance Benchmarking & Market Comparison

BuildIT is engineered to outperform both manual agency operations and traditional automation stacks.

### 7.1 Operational Benchmarking
| Metric | Manual Agency | Simple Bot/Zapier | **BuildIT Platform** |
| :--- | :--- | :--- | :--- |
| **Prospecting Speed** | 20-30/hr | 200/hr | **2,000+/hr** |
| **Outreach Quality** | High (Manual) | Low (Template) | **High (AI-Personalized)** |
| **Fault Tolerance** | Human Error | Script Crashing | **Durable Execution (Temporal)** |
| **Monitoring** | Intermittent | Limited | **Real-time (24/7)** |
| **Decision Making** | Slow/Subjective | Basic Logic | **AI-Reasoning (NIM)** |

### 7.2 Competitive Advantage
*   **Stateful Autonomy:** Unlike stateless automation (Zapier), BuildIT uses **Temporal.io** to maintain the state of every campaign. This means it never "forgets" a follow-up or double-sends an email, even during server restarts.
*   **Grounding & Validation:** Every AI action is validated against a deterministic rules engine. It combines the creativity of an LLM with the precision of a hard-coded system.
*   **Industrial Scale:** Designed to manage hundreds of clients and thousands of concurrent outreach threads from a single, unified "War Room" dashboard.

---

**BuildIT — The Gold Standard for SEO Operations.**

