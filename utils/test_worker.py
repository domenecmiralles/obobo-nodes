#!/usr/bin/env python3
"""
Test script for Obobo Worker Manager
Verifies that the worker can start, register, and communicate with the API
"""

import sys
import json
import time
import asyncio
from main import ComfyUIWorker, start_worker, stop_worker, get_worker_status

def test_worker_basic_functionality():
    """Test basic worker creation and status"""
    print("🧪 Testing basic worker functionality...")
    
    # Test worker creation
    worker = ComfyUIWorker("https://inference.obobo.net")
    print(f"✅ Worker created with ID: {worker.worker_id}")
    print(f"✅ Secret ID: {worker.secret_id}")
    
    # Test status
    status = worker.get_status()
    print(f"✅ Worker status: {json.dumps(status, indent=2)}")
    
    return True

def test_worker_registration():
    """Test worker registration with API"""
    print("\n🧪 Testing worker registration...")
    
    worker = ComfyUIWorker("https://inference.obobo.net")
    
    # Test registration
    try:
        result = worker.register()
        if result:
            print("✅ Worker registration successful")
            
            # Test heartbeat
            heartbeat_result = worker.send_heartbeat()
            if heartbeat_result:
                print("✅ Heartbeat successful")
            else:
                print("❌ Heartbeat failed")
            
            # Test unregistration
            unreg_result = worker.unregister()
            if unreg_result:
                print("✅ Worker unregistration successful")
            else:
                print("❌ Worker unregistration failed")
                
        else:
            print("❌ Worker registration failed")
            return False
            
    except Exception as e:
        print(f"❌ Registration test failed: {e}")
        return False
    
    return True

def test_global_functions():
    """Test global start/stop functions"""
    print("\n🧪 Testing global worker functions...")
    
    # Test status when no worker exists
    status = get_worker_status()
    print(f"✅ Initial status: {json.dumps(status, indent=2)}")
    
    # Test start worker
    try:
        # For testing, skip ComfyUI check by default since ComfyUI might not be running
        result = start_worker("https://inference.obobo.net", skip_comfyui_check=True)
        print(f"✅ Start worker result: {json.dumps(result, indent=2)}")
        
        if result.get("success"):
            print(f"✅ Worker started with secret ID: {result.get('secret_id')}")
            
            # Get status after start
            status = get_worker_status()
            print(f"✅ Status after start: {json.dumps(status, indent=2)}")
            
            # Test stop worker
            stop_result = stop_worker()
            print(f"✅ Stop worker result: {json.dumps(stop_result, indent=2)}")
            
        else:
            print(f"❌ Worker start failed: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ Global functions test failed: {e}")
        return False
    
    return True

def test_comfyui_connection():
    """Test connection to local ComfyUI server"""
    print("\n🧪 Testing ComfyUI connection...")
    
    try:
        import requests
        response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
        if response.status_code == 200:
            print("✅ ComfyUI server is running and accessible")
            stats = response.json()
            print(f"✅ System stats: {json.dumps(stats, indent=2)}")
            return True
        else:
            print(f"❌ ComfyUI server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ComfyUI connection test failed: {e}")
        print("   Make sure ComfyUI is running on http://127.0.0.1:8188")
        return False

def run_all_tests():
    """Run all tests"""
    print("🎬 Starting Obobo Worker Manager Tests\n")
    
    tests = [
        ("Basic Functionality", test_worker_basic_functionality),
        ("ComfyUI Connection", test_comfyui_connection),
        ("Worker Registration", test_worker_registration),
        ("Global Functions", test_global_functions),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        print("-" * 50)
    
    # Summary
    print("\n📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Worker is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 