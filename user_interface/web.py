
import os
import json
import tempfile
import boto3
from typing import Optional
from aiohttp import web
from aiohttp.web_request import Request
import dotenv

dotenv.load_dotenv()

        
def routes():
    """Define the web routes for the ComfyUI extension"""
    return [
        web.post("/api/obobo/save_workflow", save_workflow),
    ]

# Legacy endpoint removed - workflow context now passed via URL parameters

async def save_workflow(request: Request) -> web.Response:
    """Save workflow JSONs directly to S3 and update workflow node"""
    try:
        data = await request.json()
        workflow_dict = data.get("workflow")
        workflow_node_id = data.get("workflow_node_id")
        movie_id = data.get("movie_id")
        
        if not workflow_dict or "nonapi" not in workflow_dict or "api" not in workflow_dict:
            return web.json_response({
                "success": False,
                "message": "Invalid workflow format. Expected workflow: {nonapi: ..., api: ...}"
            }, status=400)
        
        if not workflow_node_id or not movie_id:
            return web.json_response({
                "success": False,
                "message": "Missing required parameters: workflow_node_id and movie_id"
            }, status=400)
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        s3_bucket = "obobo-media-production"
        s3_prefix = "workflows"
        
        # Create temporary files for both workflows
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as nonapi_file:
            json.dump(workflow_dict["nonapi"], nonapi_file, indent=2)
            nonapi_temp_path = nonapi_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as api_file:
            json.dump(workflow_dict["api"], api_file, indent=2)
            api_temp_path = api_file.name
        
        try:
            # Generate unique filenames
            import uuid
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            
            nonapi_filename = f"workflow_{timestamp}_{unique_id}.json"
            api_filename = f"workflow_api_{timestamp}_{unique_id}.json"
            
            
            # Upload both files to S3
            s3_client.upload_file(
                nonapi_temp_path,
                s3_bucket,
                f"{s3_prefix}/{movie_id}/{nonapi_filename}",
            )
            nonapi_s3_url = f"https://media.obobo.net/{s3_prefix}/{movie_id}/{nonapi_filename}"
            
            s3_client.upload_file(
                api_temp_path,
                s3_bucket,
                f"{s3_prefix}/{movie_id}/{api_filename}",
            )
            api_s3_url = f"https://media.obobo.net/{s3_prefix}/{movie_id}/{api_filename}"
            
            # Update the workflow node with new URLs via inference API
            import aiohttp
            # inference_api_url = os.getenv('LOCAL_INFERENCE_API_URL', 'http://inference.obobo.net')
            inference_api_url = "http://inference.obobo.net"
            update_url = f"{inference_api_url}/v1/worker/workflow-node/{workflow_node_id}/update-workflow"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(update_url, json={
                    "workflow": {
                        "link": nonapi_s3_url,
                        "api_link": api_s3_url,
                    }
                }) as response:
                    if response.status == 200:
                        return web.json_response({
                            "success": True,
                            "message": "Workflows saved successfully",
                            "url": nonapi_s3_url,
                            "api_url": api_s3_url
                        })
                    else:
                        error_text = await response.text()
                        return web.json_response({
                            "success": False,
                            "message": f"Failed to update workflow node: {error_text}"
                        }, status=response.status)
        
        finally:
            # Clean up temporary files
            os.unlink(nonapi_temp_path)
            os.unlink(api_temp_path)
                    
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

@PromptServer.instance.routes.post("/api/obobo/save_workflow")
async def save_workflow_route(request):
    return await save_workflow(request)

# Export the routes function for ComfyUI
__all__ = ['routes'] 