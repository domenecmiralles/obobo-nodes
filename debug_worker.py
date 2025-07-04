#!/usr/bin/env python3
"""
Debug script for Obobo Worker batch processing
This helps diagnose why ComfyUI might not be processing jobs
"""

import sys
import os
import json
import time
import requests
import logging

# Add utils to path
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_path = os.path.join(current_dir, "utils")
sys.path.insert(0, utils_path)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_comfyui_connection():
    """Test ComfyUI connectivity and API endpoints"""
    print("🔧 Testing ComfyUI Connection...")
    
    base_url = "http://127.0.0.1:8188"
    
    # Test system stats
    try:
        response = requests.get(f"{base_url}/system_stats", timeout=10)
        print(f"   ✅ System Stats: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"   📊 GPU Memory: {stats.get('system', {}).get('gpu_memory_used', 'N/A')}")
    except Exception as e:
        print(f"   ❌ System Stats Failed: {e}")
        return False
    
    # Test queue endpoint
    try:
        response = requests.get(f"{base_url}/prompt", timeout=10)
        print(f"   ✅ Queue Endpoint: {response.status_code}")
        if response.status_code == 200:
            queue_data = response.json()
            running = len(queue_data.get("queue_running", []))
            pending = len(queue_data.get("queue_pending", []))
            print(f"   📋 Queue Status: {running} running, {pending} pending")
    except Exception as e:
        print(f"   ❌ Queue Endpoint Failed: {e}")
        return False
    
    # Test history endpoint
    try:
        response = requests.get(f"{base_url}/history", timeout=10)
        print(f"   ✅ History Endpoint: {response.status_code}")
    except Exception as e:
        print(f"   ❌ History Endpoint Failed: {e}")
    
    return True

def test_worker_utilities():
    """Test the ComfyUI utility functions"""
    print("\n🔧 Testing Worker Utilities...")
    
    try:
        from main import get_gpu_info, get_s3_client
        from comfyui import jobs_in_comfyui_queue, unload_models_and_empty_memory
        
        # Test GPU info
        gpus = get_gpu_info()
        print(f"   ✅ GPU Info: Found {len(gpus)} GPUs")
        for i, gpu in enumerate(gpus):
            print(f"      GPU {i}: {gpu.name} ({gpu.capacity_in_gb}GB)")
        
        # Test S3 client
        s3_client = get_s3_client()
        print(f"   ✅ S3 Client: {'Available' if s3_client else 'Not available'}")
        
        # Test ComfyUI queue check
        queue_count = jobs_in_comfyui_queue("http://127.0.0.1:8188")
        print(f"   ✅ ComfyUI Queue Check: {queue_count} jobs")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Utility Import Failed: {e}")
        return False

def test_workflow_download():
    """Test downloading and parsing a workflow"""
    print("\n🔧 Testing Workflow Download...")
    
    # Example workflow URL from the logs
    workflow_url = "https://media.obobo.net/user_uploads/6865ae53ad795366141ffd60/workflows/wan_t2v.json"
    
    try:
        response = requests.get(workflow_url, timeout=30)
        print(f"   ✅ Workflow Download: {response.status_code}")
        
        if response.status_code == 200:
            workflow = response.json()
            print(f"   📄 Workflow Nodes: {len(workflow)} nodes")
            
            # Check for Obobo nodes
            obobo_nodes = {k: v for k, v in workflow.items() if "Obobo" in v.get("class_type", "")}
            print(f"   🎬 Obobo Nodes: {len(obobo_nodes)} found")
            
            for node_id, node in obobo_nodes.items():
                print(f"      Node {node_id}: {node['class_type']}")
                
            return workflow
        else:
            print(f"   ❌ Failed to download workflow: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ Workflow Download Failed: {e}")
        return None

def simulate_batch_processing():
    """Simulate the batch processing that would happen"""
    print("\n🔧 Simulating Batch Processing...")
    
    try:
        from comfyui import queue_claimed_jobs, jobs_in_comfyui_queue, check_completed_jobs_and_get_outputs
        
        # Create a simplified test generation
        test_generation = {
            "_id": "test123",
            "movie_id": "movie123",
            "scene_id": "scene123", 
            "shot_id": "shot123",
            "workflow": {
                "link": "https://media.obobo.net/user_uploads/6865ae53ad795366141ffd60/workflows/wan_t2v.json",
                "name": "test_workflow"
            },
            "workflow_inputs": {
                "Prompt": {"type": "text", "value": "A simple test prompt"},
                "Resolution": {"type": "vector2", "value": [512, 512]},
                "Duration": {"type": "number", "value": 16},
                "Steps": {"type": "number", "value": 4}
            }
        }
        
        print("   🔄 Attempting to queue test job...")
        
        # Try to queue the job
        queued_jobs = queue_claimed_jobs(
            [test_generation],
            "http://127.0.0.1:8188",
            "https://inference.obobo.net"
        )
        
        print(f"   ✅ Queue Result: {len(queued_jobs)} jobs queued")
        
        if len(queued_jobs) > 0:
            for job in queued_jobs:
                print(f"      Job ID: {job.job['_id']}")
                print(f"      Prompt ID: {job.prompt_id}")
        else:
            print("   ❌ No jobs were queued - this is likely the issue!")
            
        # Check ComfyUI queue status
        queue_count = jobs_in_comfyui_queue("http://127.0.0.1:8188")
        print(f"   📋 ComfyUI Queue After: {queue_count} jobs")
        
        return len(queued_jobs) > 0
        
    except Exception as e:
        print(f"   ❌ Batch Processing Simulation Failed: {e}")
        import traceback
        print(f"   🔍 Details: {traceback.format_exc()}")
        return False

def main():
    """Run all diagnostic tests"""
    print("🎬 Obobo Worker Diagnostic Tool\n")
    
    tests = [
        ("ComfyUI Connection", test_comfyui_connection),
        ("Worker Utilities", test_worker_utilities),
        ("Workflow Download", test_workflow_download),
        ("Batch Processing Simulation", simulate_batch_processing),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            print(f"\n{test_name}: ❌ ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("🎬 DIAGNOSTIC SUMMARY")
    print('='*50)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    if passed == total:
        print(f"\n🎉 All {total} tests passed! Worker should be functional.")
    else:
        print(f"\n⚠️  {total - passed} of {total} tests failed.")
        print("The failed tests likely indicate why ComfyUI isn't processing jobs.")

if __name__ == "__main__":
    main() 