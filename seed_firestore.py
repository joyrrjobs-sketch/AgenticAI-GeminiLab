import datetime
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-8c8bb2ee499a"

def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    tickets_ref = db.collection("tickets")

    sample_tickets = [
        {
            "ticket_id": "TICK-101",
            "title": "VPN Connection Timeout",
            "description": "Unable to connect to corporate VPN from remote network on macOS",
            "category": "Network",
            "status": "open",
            "priority": "high",
            "created_by": "alex.dev@company.com",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "ticket_id": "TICK-102",
            "title": "Docker permission denied",
            "description": "docker.sock permission denied when running docker compose without sudo",
            "category": "Dev Environment",
            "status": "in_progress",
            "priority": "medium",
            "created_by": "sam.eng@company.com",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "ticket_id": "TICK-103",
            "title": "GCP Service Account Key Expired",
            "description": "CI/CD deployment pipeline failing due to expired service account credentials",
            "category": "Cloud & IAM",
            "status": "open",
            "priority": "high",
            "created_by": "devops-bot@company.com",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "ticket_id": "TICK-104",
            "title": "Request Python 3.12 installation on dev VM",
            "description": "Need Python 3.12 installed on Linux workstation for new service testing",
            "category": "Software Request",
            "status": "resolved",
            "priority": "low",
            "created_by": "jordan.qa@company.com",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    print(f"Seeding tickets to Firestore project: {PROJECT_ID}...")
    for ticket in sample_tickets:
        doc_ref = tickets_ref.document(ticket["ticket_id"])
        doc_ref.set(ticket)
        print(f"  - Seeded ticket: {ticket['ticket_id']} ({ticket['title']})")

    print("Firestore seeding complete!")

if __name__ == "__main__":
    seed_database()
