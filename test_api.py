#!/usr/bin/env python3
"""
Test script for Obobo Worker API endpoints
This tests the actual API endpoints that ComfyUI will call
"""

import json
import requests
import time
import sys

def test_api_endpoints():
    """Test the API endpoints"""
    base_url = "http://127.0.0.1:8188"
    
    print("🧪 Testing Obobo Worker API endpoints with ComfyUI...")
    
    # Test 1: Worker Status
    print("\n1. Testing worker status endpoint...")
    try:
        response = requests.get(f"{base_url}/obobo/worker_status", timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status endpoint working: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Status endpoint failed with status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Status endpoint error: {e}")
    
    # Test 2: Start Worker
    print("\n2. Testing start worker endpoint...")
    try:
        payload = {"api_url": "https://inference.obobo.net"}
        response = requests.post(
            f"{base_url}/obobo/start_worker", 
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Start endpoint working: {json.dumps(data, indent=2)}")
            
            if data.get("success"):
                secret_id = data.get("secret_id")
                print(f"   🔑 Secret ID: {secret_id}")
                print(f"   🔗 Dashboard Link: https://obobo.net/start_worker/{secret_id}")
                
                # Test status after start
                print("\n2a. Testing status after start...")
                time.sleep(1)
                status_response = requests.get(f"{base_url}/obobo/worker_status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   ✅ Status after start: {json.dumps(status_data, indent=2)}")
        else:
            print(f"   ❌ Start endpoint failed with status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Start endpoint error: {e}")
    
    # Test 3: Stop Worker
    print("\n3. Testing stop worker endpoint...")
    try:
        response = requests.post(
            f"{base_url}/obobo/stop_worker",
            json={},
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Stop endpoint working: {json.dumps(data, indent=2)}")
        else:
            print(f"   ❌ Stop endpoint failed with status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Stop endpoint error: {e}")
    
    # Final status check
    print("\n4. Final status check...")
    try:
        response = requests.get(f"{base_url}/obobo/worker_status")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Final status: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"   ❌ Final status error: {e}")

def test_comfyui_connection():
    """Test basic ComfyUI connection"""
    print("🧪 Testing ComfyUI connection...")
    
    try:
        response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
        if response.status_code == 200:
            print("✅ ComfyUI is running and accessible")
            return True
        else:
            print(f"❌ ComfyUI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to ComfyUI: {e}")
        print("   Make sure ComfyUI is running on http://127.0.0.1:8188")
        return False

if __name__ == "__main__":
    print("🎬 Obobo Worker API Integration Test\n")
    
    # First test ComfyUI connection
    if not test_comfyui_connection():
        print("\n❌ ComfyUI is not running. Please start ComfyUI first.")
        sys.exit(1)
    
    print("\n" + "="*50)
    
    # Test API endpoints
    test_api_endpoints()
    
    print("\n" + "="*50)
    print("🎬 API Integration Test Complete!")
    print("\nIf all tests passed, the worker manager should work in ComfyUI.")
    print("If there were errors, check the ComfyUI console for more details.")
    print("\n💡 Note: The worker skips ComfyUI connection checks when running as an extension")
    print("   to avoid timeout issues with self-connections.") 