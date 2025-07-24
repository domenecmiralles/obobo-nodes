
import os
from typing import Optional
from aiohttp import web
from aiohttp.web_request import Request


class WorkerManager:
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url
        
wm = WorkerManager()
        
def routes():
    """Define the web routes for the worker manager"""
    return [
        web.get("/obobo/current_workflow", get_current_workflow),
        web.post("/obobo/save_workflow", save_workflow),
    ]

async def get_current_workflow(request: Request) -> web.Response:
    """Get the current workflow URL for the worker"""
    try:
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
        
        api_url = wm.api_url or "https://inference.obobo.net"
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

@PromptServer.instance.routes.get("/obobo/current_workflow")
async def get_current_workflow_route(request):
    return await get_current_workflow(request)

@PromptServer.instance.routes.post("/obobo/save_workflow")
async def save_workflow_route(request):
    return await save_workflow(request)

# Export the routes function for ComfyUI
__all__ = ['routes'] 