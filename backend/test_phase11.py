#!/usr/bin/env python3
"""
Phase 11 Evidence Collection Script
Tests all dashboard components against actual database state
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
TENANT_ID = "00000000-0000-0000-0000-000000000001"

def test_endpoint(name: str, endpoint: str, params: dict = None):
    """Test an API endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        return {
            "name": name,
            "endpoint": endpoint,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "data": data,
            "error": data.get('error', {}) if isinstance(data, dict) else None
        }
    except Exception as e:
        return {
            "name": name,
            "endpoint": endpoint,
            "status_code": 0,
            "success": False,
            "error": str(e)
        }

def main():
    print("=" * 80)
    print("PHASE 11 EVIDENCE COLLECTION")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    print()
    
    tests = []
    
    # Test 1: Business Intelligence Overview
    print("Testing: Business Intelligence Overview...")
    result = test_endpoint(
        "BI Overview",
        "/business-intelligence/intelligence/overview",
        {"tenant_id": TENANT_ID}
    )
    tests.append(result)
    print(f"  Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print()
    
    # Test 2: Campaigns List
    print("Testing: Campaigns List...")
    result = test_endpoint(
        "Campaigns",
        "/campaigns/list",
        {"tenant_id": TENANT_ID}
    )
    tests.append(result)
    print(f"  Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print()
    
    # Test 3: Approvals List
    print("Testing: Approvals List...")
    result = test_endpoint(
        "Approvals",
        "/approvals/list",
        {"tenant_id": TENANT_ID}
    )
    tests.append(result)
    print(f"  Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print()
    
    # Test 4: Communications
    print("Testing: Communications...")
    result = test_endpoint(
        "Communications",
        "/communications/list",
        {"tenant_id": TENANT_ID}
    )
    tests.append(result)
    print(f"  Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print()
    
    # Test 5: Campaign Timeline
    print("Testing: Campaign Timeline...")
    result = test_endpoint(
        "Campaign Timeline",
        "/campaigns/timeline",
        {"tenant_id": TENANT_ID}
    )
    tests.append(result)
    print(f"  Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")
    if result.get('error'):
        print(f"  Error: {result['error']}")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for t in tests if t['success'])
    total = len(tests)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    print()
    
    if passed < total:
        print("Failed Tests:")
        for t in tests:
            if not t['success']:
                print(f"  - {t['name']}: {t.get('error', 'Unknown error')}")
    
    # Save full results
    with open('/tmp/phase11_test_results.json', 'w') as f:
        json.dump(tests, f, indent=2, default=str)
    print("\nFull results saved to: /tmp/phase11_test_results.json")

if __name__ == "__main__":
    main()
