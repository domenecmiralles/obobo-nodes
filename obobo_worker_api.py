import asyncio
import logging
import json
import traceback
from typing import Dict, Any
from aiohttp import web
import sys
import os

# Add utils to path
current_dir = os.path.dirname(os.path.abspath(__file__))
utils_path = os.path.join(current_dir, "utils")
sys.path.insert(0, utils_path)

try:
    from main import start_worker, stop_worker, get_worker_status
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

class OboboWorkerAPI:
    def __init__(self):
        self.routes = web.RouteTableDef()
        self.setup_routes()

    def setup_routes(self):
        @self.routes.post("/obobo/start_worker")
        async def start_worker_endpoint(request):
            """Start the Obobo worker"""
            try:
                data = await request.json()
                api_url = data.get("api_url", "https://inference.obobo.net")
                
                logger.info(f"Starting worker with API URL: {api_url}")
                result = start_worker(api_url)
                
                if result["success"]:
                    logger.info(f"Worker started successfully: {result}")
                else:
                    logger.error(f"Failed to start worker: {result}")
                
                return web.json_response(result)
                
            except Exception as e:
                logger.error(f"Error in start_worker_endpoint: {e}")
                logger.error(traceback.format_exc())
                return web.json_response({
                    "success": False,
                    "message": f"Internal error: {str(e)}"
                }, status=500)

        @self.routes.post("/obobo/stop_worker")
        async def stop_worker_endpoint(request):
            """Stop the Obobo worker"""
            try:
                logger.info("Stopping worker")
                result = stop_worker()
                
                if result["success"]:
                    logger.info(f"Worker stopped successfully: {result}")
                else:
                    logger.error(f"Failed to stop worker: {result}")
                
                return web.json_response(result)
                
            except Exception as e:
                logger.error(f"Error in stop_worker_endpoint: {e}")
                logger.error(traceback.format_exc())
                return web.json_response({
                    "success": False,
                    "message": f"Internal error: {str(e)}"
                }, status=500)

        @self.routes.get("/obobo/worker_status")
        async def worker_status_endpoint(request):
            """Get worker status"""
            try:
                result = get_worker_status()
                return web.json_response(result)
                
            except Exception as e:
                logger.error(f"Error in worker_status_endpoint: {e}")
                logger.error(traceback.format_exc())
                return web.json_response({
                    "success": False,
                    "message": f"Internal error: {str(e)}"
                }, status=500)

# Global API instance
_api_instance = None

def get_api_routes():
    """Get the API routes for ComfyUI"""
    global _api_instance
    if _api_instance is None:
        _api_instance = OboboWorkerAPI()
    return _api_instance.routes

async def start_worker_endpoint(request):
    """Start the Obobo worker"""
    try:
        data = await request.json()
        api_url = data.get("api_url", "https://inference.obobo.net")
        
        logger.info(f"Starting worker with API URL: {api_url}")
        result = start_worker(api_url)
        
        if result["success"]:
            logger.info(f"Worker started successfully: {result}")
        else:
            logger.error(f"Failed to start worker: {result}")
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Error in start_worker_endpoint: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            "success": False,
            "message": f"Internal error: {str(e)}"
        }, status=500)

async def stop_worker_endpoint(request):
    """Stop the Obobo worker"""
    try:
        logger.info("Stopping worker")
        result = stop_worker()
        
        if result["success"]:
            logger.info(f"Worker stopped successfully: {result}")
        else:
            logger.error(f"Failed to stop worker: {result}")
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Error in stop_worker_endpoint: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            "success": False,
            "message": f"Internal error: {str(e)}"
        }, status=500)

async def worker_status_endpoint(request):
    """Get worker status"""
    try:
        result = get_worker_status()
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Error in worker_status_endpoint: {e}")
        logger.error(traceback.format_exc())
        return web.json_response({
            "success": False,
            "message": f"Internal error: {str(e)}"
        }, status=500)

def setup_routes(routes):
    """Setup routes using ComfyUI's route table"""
    routes.post("/obobo/start_worker")(start_worker_endpoint)
    routes.post("/obobo/stop_worker")(stop_worker_endpoint)
    routes.get("/obobo/worker_status")(worker_status_endpoint)
    logger.info("🎬 Obobo worker API routes registered successfully") 