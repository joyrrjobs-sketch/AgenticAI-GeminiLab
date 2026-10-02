# IT & Developer Support Assistant

An intelligent, conversational AI assistant designed to help developers and IT teams troubleshoot technical issues, monitor system health, search knowledge base articles, manage Firestore support tickets, and generate visual diagnostic assets. Built with the **Google Agent Development Kit (ADK)** and powered by **Gemini 2.5 Flash**.

![IT Helpdesk Agent Demo](./demo.gif)

---

## 🚀 Actual Implemented Capabilities & Tools

This codebase implements the following capabilities and Google Cloud integrations:

### 1. 🗄️ Firestore Support Ticket Management
* **Database**: Google Cloud Firestore (`qwiklabs-gcp-03-8c8bb2ee499a`)
* **Tools**:
  * `list_tickets`: Search and list IT support tickets with optional status (`open`, `in_progress`, `resolved`) and category filtering (`Network`, `Dev Environment`, `Cloud & IAM`, `Software Request`).
  * `create_ticket`: Create new IT support tickets with auto-generated ticket IDs (`TICK-xxxxxx`), category, priority, and requester details.
  * `update_ticket_status`: Update ticket resolution status in real-time.

### 2. 🧠 Vertex AI Memory Bank (Long-Term Memory)
* **Service**: `VertexAiMemoryBankService` on Google Cloud Vertex AI
* **Tools & Callbacks**:
  * `PreloadMemoryTool`: Preloads user preferences, tech stack details, and past ticket context across sessions.
  * `generate_memories_callback`: Automatically persists conversation sessions to Vertex AI Memory Bank upon response completion.

### 3. 🎨 Visual Asset Generation & Public Cloud Storage
* **Service**: Google Cloud Storage (`it-helpdesk-assets-qwiklabs-gcp-03-8c8bb2ee499a`) & Google GenAI SDK
* **Tools**:
  * `generate_architecture_diagram`: Uses `gemini-3.1-flash-lite-image` to generate technical network topology diagrams and health dashboard images. Uploads bytes directly to GCS and returns public HTTPS URLs.
  * `generate_support_video`: Uses Google's Omni model (`gemini-omni-flash-preview`) in the `global` region to generate animated IT support videos (e.g., server reboot sequence, database pool health diagnostic). Saves artifacts to ADK ToolContext and uploads bytes directly to public GCS.

### 4. 🎛️ Agent-to-User Interface (A2UI) Rendering
* **Library**: `A2uiSchemaManager` (v0.8 Basic Catalog)
* **Callback**: `a2ui_callback` converts structured model output into rich UI card layouts (`Card`, `Column`, `Row`, `Text`, `Image`) rendered directly in the custom web application.

### 5. 💻 Sandboxed Code Execution
* **Executor**: `AgentEngineSandboxCodeExecutor`
* **Capability**: Executes Python diagnostic scripts safely in an isolated Google Cloud Agent Platform runtime sandbox.

### 6. 🌐 External Integrations & Diagnostic Tools
* **Tools**:
  * `fetch_github_status`: Fetches live operational status and component health (Actions, Copilot, Git Operations, API) from the official GitHub Status API.
  * `search_kb`: Searches the internal IT & Developer Knowledge Base for VPN, Docker permissions, and GCP IAM key troubleshooting steps.
  * `check_service_health`: Checks real-time health, uptime, and latency metrics for infrastructure services (VPN, PostgreSQL, SSO, GKE).

---

## 📋 Implementation Status Matrix

| Capability | Status | Technology / Details |
| :--- | :--- | :--- |
| Core Agent Reasoning | **Implemented** | ADK Python, `gemini-2.5-flash` |
| Ticket Management | **Implemented** | Google Cloud Firestore |
| Long-Term Memory | **Implemented** | Vertex AI Memory Bank (`VertexAiMemoryBankService`) |
| Image Generation | **Implemented** | `gemini-3.1-flash-lite-image` |
| Omni Video Generation | **Implemented** | `gemini-omni-flash-preview` (Global Region) |
| Asset Storage | **Implemented** | Google Cloud Storage Bucket |
| Rich Card UI | **Implemented** | A2UI v0.8 Basic Catalog |
| Sandboxed Execution | **Implemented** | `AgentEngineSandboxCodeExecutor` |
| GitHub Health Check | **Implemented** | External REST API (`githubstatus.com`) |
| Observability Tracing | *Planned / Not yet implemented* | Cloud Trace custom OpenTelemetry spans |

---

## 🛠️ Local Development & Running Instructions

### Prerequisites
* Python 3.11+
* `uv` package manager (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
* Google Cloud SDK (`gcloud`) authenticated to your GCP project

### 1. Installation & Environment Setup
Clone the repository and install dependencies:
```bash
git clone <repository-url>
cd it-helpdesk-agent
uv sync
```

Set up local environment configuration in `.env`:
```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-east1
GOOGLE_GENAI_USE_VERTEXAI=true
```

### 2. Run Agent Engine Locally
To test agent prompts directly from the CLI:
```bash
uv run agents-cli run "Check database health and list open tickets"
```

To run interactive evaluation:
```bash
uv run agents-cli eval run
```

### 3. Run Web Frontend Locally
Navigate to the `frontend` folder, install dependencies, and start the FastAPI web proxy server:
```bash
cd frontend
uv pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/us-east1/reasoningEngines/<engine-id>"
export AGENT_DIRECTORY="app"
uv run python main.py
```
Open your browser to the local server port printed by FastAPI (default: port 8080).

### 4. Deploying to Agent Platform
Deploy the updated agent to Google Cloud Agent Platform:
```bash
uv run agents-cli deploy --no-confirm-project
```

Deploy the web frontend to Cloud Run:
```bash
gcloud run deploy it-helpdesk-frontend \
  --source ./frontend \
  --region us-east1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/us-east1/reasoningEngines/<engine-id>",AGENT_DIRECTORY="app" \
  --allow-unauthenticated
```
