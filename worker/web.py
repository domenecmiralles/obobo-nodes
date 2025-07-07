"""
Web API endpoints for Obobo Worker Manager
"""

import logging
import os
from typing import Dict, Any, Optional
from aiohttp import web
from aiohttp.web_request import Request
from .worker_manager import WorkerManager

logger = logging.getLogger(__name__)

# Global worker manager instance
worker_manager = None

def get_worker_manager(api_url: Optional[str] = None):
    """Get or create worker manager instance"""
    global worker_manager
    if worker_manager is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        worker_manager = WorkerManager(current_dir, api_url)
    elif api_url and worker_manager.api_url != api_url:
        # Update API URL if different
        worker_manager.api_url = api_url
    return worker_manager

def routes():
    """Define the web routes for the worker manager"""
    return [
        web.post("/obobo/start_worker", start_worker),
        web.post("/obobo/stop_worker", stop_worker),
        web.post("/obobo/resume_worker", resume_worker),
        web.get("/obobo/worker_status", get_worker_status),
        web.get("/obobo/worker_logs/{worker_id}", get_worker_logs),
        web.get("/obobo/current_workflow", get_current_workflow),
        web.post("/obobo/save_workflow", save_workflow),
    ]

async def start_worker(request: Request) -> web.Response:
    """Start the worker process"""
    try:
        data = await request.json()
        api_url = data.get("api_url", "http://127.0.0.1:8001")
        
        # Use worker manager to start the worker
        wm = get_worker_manager(api_url)
        result = wm.start_worker(api_url)
        
        if result["success"]:
            return web.json_response({
                "success": True,
                "message": result["message"],
                "worker_id": result["worker_id"],
                "pid": result["pid"],
                "api_registered": result.get("api_registered", False)
            })
        else:
            return web.json_response({
                "success": False,
                "message": result["message"],
                "worker_id": result.get("worker_id")
            }, status=400)
        
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        return web.json_response({
            "success": False,
            "message": str(e)
        }, status=500)

async def stop_worker(request: Request) -> web.Response:
    """Set worker to inactive state"""
    try:
        # Use worker manager to stop worker
        wm = get_worker_manager()
        result = wm.stop_worker()
        
        if result["success"]:
            return web.json_response({
                "success": True,
                "message": result["message"],
                "worker_id": result.get("worker_id")
            })
        else:
            return web.json_response({
                "success": False,
                "message": result["message"],
                "worker_id": result.get("worker_id")
            }, status=400)
        
    except Exception as e:
        logger.error(f"Failed to stop worker: {e}")
        return web.json_response({
            "success": False,
            "message": str(e)
        }, status=500)

async def resume_worker(request: Request) -> web.Response:
    """Set worker to active state"""
    try:
        # Use worker manager to resume worker
        wm = get_worker_manager()
        result = wm._register_worker_in_api(wm.worker_id, wm.api_url)
        
        if result:
            return web.json_response({
                "success": True,
                "message": "Worker set to active",
                "worker_id": wm.worker_id
            })
        else:
            return web.json_response({
                "success": False,
                "message": "Failed to set worker active",
                "worker_id": wm.worker_id
            }, status=400)
        
    except Exception as e:
        logger.error(f"Failed to resume worker: {e}")
        return web.json_response({
            "success": False,
            "message": str(e)
        }, status=500)

async def get_worker_status(request: Request) -> web.Response:
    """Get the current status of the worker"""
    try:
        # Use worker manager to get status
        wm = get_worker_manager()
        status = wm.get_worker_status()
        
        if status.get("success", True):
            return web.json_response({
                "success": True,
                "total_workers": status["total_workers"],
                "active_workers": status["active_workers"],
                "running_workers": status["active_workers"],  # For JS compatibility
                "workers": status["workers"]
            })
        else:
            return web.json_response({
                "success": False,
                "message": status.get("message", "Unknown error"),
                "total_workers": status.get("total_workers", 0),
                "active_workers": status.get("active_workers", 0),
                "running_workers": status.get("active_workers", 0),
                "workers": status.get("workers", {})
            }, status=500)
        
    except Exception as e:
        logger.error(f"Failed to get worker status: {e}")
        return web.json_response({
            "success": False,
            "message": str(e)
        }, status=500)

async def get_worker_logs(request: Request) -> web.Response:
    """Get logs for a specific worker"""
    try:
        worker_id = request.match_info['worker_id']
        lines = int(request.query.get('lines', 50))
        
        # Use worker manager to get logs
        wm = get_worker_manager()
        result = wm.get_worker_logs(worker_id, lines)
        
        if result["success"]:
            return web.json_response({
                "success": True,
                "worker_id": result["worker_id"],
                "logs": result["logs"]
            })
        else:
            return web.json_response({
                "success": False,
                "message": result["message"]
            }, status=404)
        
    except Exception as e:
        logger.error(f"Failed to get worker logs: {e}")
        return web.json_response({
            "success": False,
            "message": str(e)
        }, status=500)

async def get_current_workflow(request: Request) -> web.Response:
    """Get the current workflow URL for the worker"""
    try:
        wm = get_worker_manager()
        result = wm.get_worker_status()
        
        if result["success"] and result["workers"]:
            worker_info = next(iter(result["workers"].values()))
            editable_workflow = worker_info.get("editable_workflow", {})
            workflow_url = editable_workflow.get("link") if editable_workflow else None
            
            if workflow_url:
                return web.json_response({
                    "success": True,
                    "workflow_url": workflow_url
                })
            else:
                return web.json_response({
                    "success": False,
                    "message": "No workflow currently assigned"
                }, status=404)
        else:
            return web.json_response({
                "success": False,
                "message": "No active worker found"
            }, status=404)
            
    except Exception as e:
        logger.error(f"Failed to get current workflow: {e}")
        return web.json_response({
            "success": False,
            "message": str(e)
        }, status=500)

async def save_workflow(request: Request) -> web.Response:
    """Save workflow JSON to S3 through the API"""
    try:
        data = await request.json()
        workflow_dict = data.get("workflow")
        
        if not workflow_dict or "nonapi" not in workflow_dict or "api" not in workflow_dict:
            return web.json_response({
                "success": False,
                "message": "Invalid workflow format. Expected workflow: {nonapi: ..., api: ...}"
            }, status=400)
        
        # Get worker status to find the workflow URL and node ID
        wm = get_worker_manager()
        result = wm.get_worker_status()
        
        if not result["success"] or not result["workers"]:
            return web.json_response({
                "success": False,
                "message": "No active worker found"
            }, status=404)
        
        worker_info = next(iter(result["workers"].values()))
        workflow_node_id = worker_info.get("current_workflow_node_id")

        
        if not workflow_node_id:
            return web.json_response({
                "success": False,
                "message": "Missing required worker information (workflow node ID)"
            }, status=404)
        
        # Make API request to save both workflows
        import aiohttp
        import json
        
        api_url = wm.api_url or "http://127.0.0.1:8001"
        save_url = f"{api_url}/v1/upload/save-workflow"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(save_url, json={
                #"workflow_url": workflow_url,
                "workflow": workflow_dict,
                "workflow_node_id": workflow_node_id
            }) as response:
                if response.status == 200:
                    api_result = await response.json()
                    return web.json_response({
                        "success": True,
                        "message": "Workflows saved successfully",
                        "url": api_result.get("url"),
                        "api_url": api_result.get("api_url")
                    })
                else:
                    error_text = await response.text()
                    return web.json_response({
                        "success": False,
                        "message": f"API request failed: {error_text}"
                    }, status=response.status)
                    
    except Exception as e:
        logger.error(f"Failed to save workflow: {e}")
        return web.json_response({
            "success": False,
            "message": str(e)
        }, status=500)

# Required by ComfyUI
@web.middleware
async def cors_handler(request, handler):
    """Handle CORS for API requests"""
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# ComfyUI web extension setup
from server import PromptServer

# Register routes with ComfyUI
@PromptServer.instance.routes.post("/obobo/start_worker")
async def start_worker_route(request):
    return await start_worker(request)

@PromptServer.instance.routes.post("/obobo/stop_worker")  
async def stop_worker_route(request):
    return await stop_worker(request)

@PromptServer.instance.routes.post("/obobo/resume_worker")
async def resume_worker_route(request):
    return await resume_worker(request)

@PromptServer.instance.routes.get("/obobo/worker_status")
async def get_worker_status_route(request):
    return await get_worker_status(request)

@PromptServer.instance.routes.get("/obobo/worker_logs/{worker_id}")
async def get_worker_logs_route(request):
    return await get_worker_logs(request)

@PromptServer.instance.routes.get("/obobo/current_workflow")
async def get_current_workflow_route(request):
    return await get_current_workflow(request)

@PromptServer.instance.routes.post("/obobo/save_workflow")
async def save_workflow_route(request):
    return await save_workflow(request)

# Export the routes function for ComfyUI
__all__ = ['routes'] 