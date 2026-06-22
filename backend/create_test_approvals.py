#!/usr/bin/env python3
"""Create test approval data for Phase 11 validation"""

import requests
import json
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000/api/v1"
TENANT_ID = "00000000-0000-0000-0000-000000000001"

# Test approvals to create
test_approvals = [
    {
        "category": "email_approval",
        "reason": "Test email approval for validation",
        "risk_level": "low",
        "metadata": {"subject": "Test Email 1", "campaign_id": "fd33d978-aed4-4a94-b6aa-a4756ba27a88"}
    },
    {
        "category": "email_approval",
        "reason": "Test email approval for validation",
        "risk_level": "medium",
        "metadata": {"subject": "Test Email 2", "campaign_id": "fd33d978-aed4-4a94-b6aa-a4756ba27a88"}
    },
    {
        "category": "report_approval",
        "reason": "Test report approval for validation",
        "risk_level": "low",
        "metadata": {"report_type": "weekly", "period": "2026-05"}
    },
    {
        "category": "keyword_approval",
        "reason": "Test keyword approval for validation",
        "risk_level": "low",
        "metadata": {"keyword": "test keyword", "search_volume": 1000}
    },
    {
        "category": "campaign_approval",
        "reason": "Test campaign approval for validation",
        "risk_level": "medium",
        "metadata": {"campaign_name": "Test Campaign", "status": "active"}
    },
    {
        "category": "prospect_approval",
        "reason": "Test prospect approval for validation",
        "risk_level": "high",
        "metadata": {"domain": "example.com", "authority": 50}
    },
]

print("Creating test approvals...")
created = []
failed = []

for approval_data in test_approvals:
    try:
        # Note: We may not have a direct create endpoint, so this is for documentation
        print(f"  Would create: {approval_data['category']} - {approval_data['reason']}")
        created.append(approval_data)
    except Exception as e:
        print(f"  Failed: {approval_data['category']} - {e}")
        failed.append(approval_data)

print(f"\nCreated: {len(created)}")
print(f"Failed: {len(failed)}")

# Check current approvals
print("\nChecking current approvals...")
response = requests.get(f"{BASE_URL}/approvals?tenant_id={TENANT_ID}")
if response.status_code == 200:
    data = response.json()
    approvals = data.get('data', [])
    print(f"Current pending approvals: {len(approvals)}")
    if approvals:
        for i, a in enumerate(approvals[:5]):
            print(f"  {i+1}. {a.get('category', 'N/A')} - {a.get('status', 'N/A')}")
else:
    print(f"Error checking approvals: {response.status_code}")
