"""
ComfyUI Web Extension for Obobo Worker API
This follows ComfyUI's standard pattern for web extensions
"""

import json
import logging
import traceback
import sys
import os
from server import PromptServer
from aiohttp import web

# Add utils to path
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_path = os.path.join(current_dir, "utils")
sys.path.insert(0, utils_path)

try:
    from main import start_worker, stop_worker, get_worker_status
    logger = logging.getLogger(__name__)
    logger.info("🎬 Worker functions imported successfully")
except ImportError as e:
    logging.error(f"Failed to import worker functions: {e}")
    # Create dummy functions if import fails
    def start_worker(api_url):
        return {"success": False, "message": "Worker functions not available"}
    def stop_worker():
        return {"success": False, "message": "Worker functions not available"}
    def get_worker_status():
        return {"running": False, "message": "Worker functions not available"}

logger = logging.getLogger(__name__)

# Define route handlers
async def handle_start_worker(request):
    """Handle start worker request"""
    try:
        logger.info("🎬 Received start worker request")
        
        # Parse JSON data
        try:
            data = await request.json()
            api_url = data.get("api_url", "https://inference.obobo.net")
        except Exception as e:
            logger.error(f"🎬 Failed to parse JSON data: {e}")
            return web.json_response({
                "success": False,
                "message": f"Invalid JSON data: {str(e)}"
            }, status=400)
        
        logger.info(f"🎬 Starting worker with API URL: {api_url}")
        result = start_worker(api_url)
        
        logger.info(f"🎬 Worker start result: {result}")
        
        # Ensure result is JSON serializable
        if not isinstance(result, dict):
            result = {"success": False, "message": "Invalid response from worker"}
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"🎬 Error in handle_start_worker: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            "success": False,
            "message": f"Internal error: {str(e)}"
        }, status=500)

async def handle_stop_worker(request):
    """Handle stop worker request"""
    try:
        logger.info("🎬 Received stop worker request")
        result = stop_worker()
        
        logger.info(f"🎬 Worker stop result: {result}")
        
        # Ensure result is JSON serializable
        if not isinstance(result, dict):
            result = {"success": False, "message": "Invalid response from worker"}
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"🎬 Error in handle_stop_worker: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            "success": False,
            "message": f"Internal error: {str(e)}"
        }, status=500)

async def handle_worker_status(request):
    """Handle worker status request"""
    try:
        logger.info("🎬 Received worker status request")
        result = get_worker_status()
        
        logger.info(f"🎬 Worker status result: {result}")
        
        # Ensure result is JSON serializable
        if not isinstance(result, dict):
            result = {"running": False, "message": "Invalid response from worker"}
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"🎬 Error in handle_worker_status: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            "success": False,
            "message": f"Internal error: {str(e)}"
        }, status=500)

# Register routes with ComfyUI's PromptServer
def register_routes():
    """Register API routes with ComfyUI"""
    try:
        routes = PromptServer.instance.routes
        
        # Register the routes
        routes.post("/obobo/start_worker")(handle_start_worker)
        routes.post("/obobo/stop_worker")(handle_stop_worker)
        routes.get("/obobo/worker_status")(handle_worker_status)
        
        logger.info("🎬 Obobo worker API routes registered successfully")
        
    except Exception as e:
        logger.error(f"🎬 Failed to register routes: {e}")
        logger.error(traceback.format_exc())

# Auto-register routes when module is imported
register_routes() 