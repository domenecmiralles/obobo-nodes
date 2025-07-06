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
        web.get("/obobo/worker_status", get_worker_status),
        web.get("/obobo/worker_logs/{worker_id}", get_worker_logs),
    ]

async def start_worker(request: Request) -> web.Response:
    """Start the worker process"""
    try:
        data = await request.json()
        api_url = data.get("api_url", "https://inference.obobo.net")
        # api_url = data.get("api_url", "http://127.0.0.1:8001")
        
        # Use worker manager to start the worker
        wm = get_worker_manager(api_url)
        result = wm.start_worker(api_url)
        
        if result["success"]:
            return web.json_response({
                "success": True,
                "message": result["message"],
                "worker_id": result["worker_id"],
                "secret_id": result["worker_id"],  # For compatibility with existing JS
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
    """Stop worker process"""
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

@PromptServer.instance.routes.get("/obobo/worker_status")
async def get_worker_status_route(request):
    return await get_worker_status(request)

@PromptServer.instance.routes.get("/obobo/worker_logs/{worker_id}")
async def get_worker_logs_route(request):
    return await get_worker_logs(request)

# Export the routes function for ComfyUI
__all__ = ['routes'] 