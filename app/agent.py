import datetime
import json
import os
import urllib.request
import uuid
from google import genai
from google.cloud import firestore
from google.cloud import storage

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

try:
    from .a2ui_utils import a2ui_callback
except ImportError:
    from a2ui_utils import a2ui_callback

# HARDCODED GCP Project ID and GCS Bucket Name
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-8c8bb2ee499a"
GCS_BUCKET_NAME = "it-helpdesk-assets-qwiklabs-gcp-03-8c8bb2ee499a"

# Load Agent Engine resource name from deployment_metadata.json
DEPLOYMENT_METADATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json"
)
AGENT_ENGINE_RESOURCE_NAME = "projects/375720028768/locations/us-east1/reasoningEngines/3617306393964445696"

if os.path.exists(DEPLOYMENT_METADATA_PATH):
    try:
        with open(DEPLOYMENT_METADATA_PATH, "r") as f:
            metadata = json.load(f)
            AGENT_ENGINE_RESOURCE_NAME = metadata.get(
                "remote_agent_runtime_id", AGENT_ENGINE_RESOURCE_NAME
            )
    except Exception:
        pass

# Initialize Agent Platform sandbox code executor
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME
)


def get_firestore_client():
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def list_tickets(status: str = "", category: str = "") -> list[dict]:
    """List or search IT support tickets stored in the Firestore database.

    Args:
        status: Optional filter by status ('open', 'in_progress', 'resolved').
        category: Optional filter by category ('Network', 'Dev Environment', 'Cloud & IAM', 'Software Request').

    Returns:
        List of matching ticket objects.
    """
    db = get_firestore_client()
    query_ref = db.collection("tickets")
    
    docs = query_ref.stream()
    tickets = []
    for doc in docs:
        data = doc.to_dict()
        if status and data.get("status", "").lower() != status.lower():
            continue
        if category and data.get("category", "").lower() != category.lower():
            continue
        tickets.append(data)
    return tickets


def create_ticket(
    title: str,
    description: str,
    category: str = "General IT",
    priority: str = "medium",
    created_by: str = "user@company.com",
) -> dict:
    """Create a new IT support ticket in the Firestore database.

    Args:
        title: Short summary of the technical issue or request.
        description: Detailed description of the problem or request.
        category: Category of the ticket (e.g. Network, Dev Environment, Cloud & IAM, Software Request).
        priority: Priority level ('low', 'medium', 'high').
        created_by: Email of the requester.

    Returns:
        The created ticket data dictionary including ticket_id.
    """
    db = get_firestore_client()
    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    ticket_data = {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "category": category,
        "status": "open",
        "priority": priority.lower(),
        "created_by": created_by,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    db.collection("tickets").document(ticket_id).set(ticket_data)
    return ticket_data


def update_ticket_status(ticket_id: str, status: str) -> dict:
    """Update the status of an existing IT support ticket in Firestore.

    Args:
        ticket_id: The ID of the ticket to update (e.g. TICK-101).
        status: New status ('open', 'in_progress', 'resolved').

    Returns:
        A status dictionary confirming the update.
    """
    db = get_firestore_client()
    doc_ref = db.collection("tickets").document(ticket_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Ticket {ticket_id} not found."}
    
    doc_ref.update({"status": status.lower()})
    return {"ticket_id": ticket_id, "status": status.lower(), "updated": True}


def search_kb(query: str) -> str:
    """Search the internal IT & Developer Knowledge Base for troubleshooting steps.

    Args:
        query: Search keywords or error message.

    Returns:
        Knowledge base snippet or troubleshooting guide.
    """
    q = query.lower()
    if "vpn" in q:
        return "VPN Troubleshooting: 1. Ensure GlobalProtect/Cisco AnyConnect is updated. 2. Clear DNS cache (`sudo killall -HUP mDNSResponder`). 3. Re-authenticate via SSO."
    elif "docker" in q or "permission denied" in q:
        return "Docker Permission Troubleshooting: Run `sudo usermod -aG docker $USER` and restart your shell session to run docker without sudo."
    elif "iam" in q or "service account" in q or "gcp" in q:
        return "GCP IAM Troubleshooting: Service account keys expire every 90 days. Run `gcloud auth application-default login` or request a new key via Cloud Console."
    return "Generic KB: Restart the service or application. For persistent issues, submit an IT support ticket."


def check_service_health(service_name: str) -> dict:
    """Check the operational health, status, and latency of core infrastructure services.

    Args:
        service_name: Name of the service (e.g. 'vpn', 'database', 'auth', 'kubernetes', 'gcp').

    Returns:
        A dictionary containing health status, uptime, and latency metrics.
    """
    s = service_name.lower()
    if "vpn" in s:
        return {"service": "VPN Gateway", "status": "Operational", "latency_ms": 14, "uptime": "99.98%"}
    elif "db" in s or "database" in s or "postgres" in s:
        return {"service": "PostgreSQL Primary", "status": "Degraded", "issue": "Connection pool near capacity (92%)", "latency_ms": 120, "uptime": "99.90%"}
    elif "auth" in s or "sso" in s:
        return {"service": "SSO Auth Provider", "status": "Operational", "latency_ms": 35, "uptime": "99.99%"}
    elif "k8s" in s or "kubernetes" in s or "cluster" in s:
        return {"service": "Production GKE Cluster", "status": "Operational", "latency_ms": 8, "uptime": "100.00%"}
    return {"service": service_name, "status": "Operational", "latency_ms": 22, "uptime": "99.95%"}


def fetch_github_status() -> dict:
    """Fetch real-time operational status of GitHub services (Actions, Copilot, Git Operations, Webhooks, API).

    Returns:
        A dictionary containing overall GitHub operational status and component health.
    """
    api_url = os.environ.get(
        "GITHUB_STATUS_API_URL", "https://www.githubstatus.com/api/v2/summary.json"
    )
    try:
        req = urllib.request.Request(
            api_url, headers={"User-Agent": "IT-Support-Agent/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            status_desc = data.get("status", {}).get("description", "Unknown")
            components = [
                {"name": c.get("name"), "status": c.get("status")}
                for c in data.get("components", [])[:8]
            ]
            return {
                "overall_status": status_desc,
                "components": components,
                "updated_at": data.get("page", {}).get("updated_at"),
            }
    except Exception as e:
        return {"error": f"Failed to fetch GitHub status: {str(e)}"}


def generate_architecture_diagram(
    description: str, tool_context: ToolContext = None
) -> dict:
    """Generate a technical architecture diagram, network topology, or health status snapshot/dashboard image for IT infrastructure issues and upload it.

    Args:
        description: Description of the architecture diagram or status snapshot to generate (e.g. 'PostgreSQL connection pool architecture', 'Database health status snapshot with 92% pool usage and 5 tickets').
        tool_context: ADK tool context for saving artifacts.

    Returns:
        A dictionary containing the public Cloud Storage image URL, image filename, and description.
    """
    client = genai.Client(
        vertexai=True, project=FIRESTORE_PROJECT_ID, location="global"
    )
    prompt = f"Technical IT status dashboard diagram, modern infographic UI showing: {description}"
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    part = response.candidates[0].content.parts[0]
    image_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "image/jpeg"

    filename = f"snapshot-{uuid.uuid4().hex[:8]}.jpg"

    # 1. Save artifact so it shows up in Playground's Artifacts panel
    if tool_context and hasattr(tool_context, "save_artifact"):
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    return {
        "description": description,
        "filename": filename,
        "public_url": public_url,
        "status": "Image generated and uploaded successfully",
    }


def generate_support_video(
    description: str, tool_context: ToolContext = None
) -> dict:
    """Generate a short video for an IT support or infrastructure item (e.g. server reboot sequence, database pool health diagnostic) using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Args:
        description: Description of the IT support video or animation to generate.
        tool_context: ADK tool context for saving artifacts.

    Returns:
        A dictionary containing the public Cloud Storage video URL, filename, and status message.
    """
    client = genai.Client(
        vertexai=True, project=FIRESTORE_PROJECT_ID, location="global"
    )
    prompt = f"Short animated video for IT support item: {description}"

    response = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
    )

    video_bytes = None
    mime_type = "video/mp4"

    if hasattr(response, "output_video") and response.output_video:
        video_bytes = getattr(response.output_video, "data", None) or getattr(
            response.output_video, "bytes", None
        )
        if getattr(response.output_video, "mime_type", None):
            mime_type = response.output_video.mime_type

    if not video_bytes and hasattr(response, "outputs") and response.outputs:
        for output in response.outputs:
            if hasattr(output, "parts") and output.parts:
                for part in output.parts:
                    if (
                        hasattr(part, "video")
                        and part.video
                        and getattr(part.video, "bytes", None)
                    ):
                        video_bytes = part.video.bytes
                        if getattr(part.video, "mime_type", None):
                            mime_type = part.video.mime_type
                        break

    if not video_bytes:
        return {"error": "Failed to generate video bytes from gemini-omni-flash-preview."}

    filename = f"video-{uuid.uuid4().hex[:8]}.mp4"

    # 1. Save artifact so it shows up in Playground's Artifacts panel
    if tool_context and hasattr(tool_context, "save_artifact"):
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload video bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    return {
        "description": description,
        "filename": filename,
        "public_url": public_url,
        "status": "Video generated and uploaded successfully",
    }


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


MEMORY_BANK_ID = "3617306393964445696"


def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT_ID,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the IT & Developer Support Assistant. You help users troubleshoot technical issues, "
        "execute Python code safely in the Agent Platform sandbox, generate architecture diagrams, health status snapshots, and diagnostic videos using gemini-omni-flash-preview, "
        "check infrastructure service health, check live external developer services like GitHub, search knowledge base solutions, view support tickets, and create or update tickets in the Firestore database. "
        "You remember user preferences and facts across sessions using Memory Bank."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    tools=[
        list_tickets,
        create_ticket,
        update_ticket_status,
        search_kb,
        check_service_health,
        fetch_github_status,
        generate_architecture_diagram,
        generate_support_video,
        PreloadMemoryTool(),
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

