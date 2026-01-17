import os
import json
import requests
import base64
import torch
import numpy as np
from PIL import Image
import io
import logging
from dotenv import load_dotenv
from .obobo_base_node import OboboBaseNode

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboCallModel(OboboBaseNode):
    def __init__(self):
        super().__init__()
        logger.info("OboboCallModel node initialized")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Enter your prompt here...",
                    "tooltip": "Text prompt - if no images connected, calls text model; if images connected, calls vision model"
                }),
            },
            "optional": {
                "image1": ("IMAGE", {
                    "tooltip": "First image to analyze (optional)"
                }),
                "image2": ("IMAGE", {
                    "tooltip": "Second image to analyze (optional)"
                }),
                "image3": ("IMAGE", {
                    "tooltip": "Third image to analyze (optional)"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "call_model"
    CATEGORY = "obobo/models"
    DESCRIPTION = "Unified model caller - text model if no images, vision model if images provided"

    def call_model(self, prompt, image1=None, image2=None, image3=None):
        """
        Call either text or vision model based on whether images are provided.
        
        Args:
            prompt (str): Text prompt
            image1 (torch.Tensor, optional): First image tensor
            image2 (torch.Tensor, optional): Second image tensor  
            image3 (torch.Tensor, optional): Third image tensor
            
        Returns:
            tuple: (model_response,)
        """
        
        if not prompt.strip():
            logger.warning("Empty prompt provided to model")
            return ("Error: Empty prompt provided",)
        
        # Check if any images are provided
        images = [img for img in [image1, image2, image3] if img is not None]
        
        if not images:
            # No images provided - call text model
            return self._call_text_model(prompt)
        else:
            # Images provided - call vision model
            return self._call_vision_model(prompt, images)
    
    def _call_text_model(self, prompt):
        """Call Together.ai Mistral text model"""
        try:
            # Get Together API key
            together_api_key = os.getenv('TOGETHER_API_KEY')
            if not together_api_key:
                error_msg = "TOGETHER_API_KEY not found in environment variables"
                logger.error(error_msg)
                return (error_msg,)
            
            # Format the prompt for Mistral
            formatted_prompt = f"<s>[INST] {prompt} [/INST]"
            
            # Create the request payload for Together.ai
            payload = {
                "model": "mistralai/Mistral-7B-Instruct-v0.2",
                "prompt": formatted_prompt,
                "max_tokens": 2000,
                "temperature": 0.8
            }
            
            # Set up headers
            headers = {
                "Authorization": f"Bearer {together_api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Calling Together.ai text model with prompt: {prompt[:100]}...")
            
            # Call the Together.ai API
            response = requests.post(
                "https://api.together.xyz/v1/completions",
                headers=headers,
                json=payload
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            
            # Extract response text
            model_response = response_data["choices"][0]["text"]
            
            logger.info(f"Text model response received: {model_response[:100]}...")
            return (model_response,)
            
        except Exception as e:
            error_msg = f"Text model API call failed: {str(e)}"
            logger.error(error_msg)
            return (error_msg,)
    
    def _call_vision_model(self, prompt, images):
        """Call Together.ai Qwen vision model with multiple images"""
        try:
            # Get Together API key
            together_api_key = os.getenv('TOGETHER_API_KEY')
            if not together_api_key:
                error_msg = "TOGETHER_API_KEY not found in environment variables"
                logger.error(error_msg)
                return (error_msg,)
            
            logger.info(f"Calling Together.ai vision model with {len(images)} image(s) and prompt: {prompt[:100]}...")
            
            # Process the first image
            image = images[0]  # Take the first image
            logger.info(f"Processing image with shape: {image.shape}")
            
            # Convert tensor to PIL Image
            # ComfyUI images are in format [batch, height, width, channels] with values 0-1
            # Take the first image from the batch
            if len(image.shape) == 4:
                image_tensor = image[0]  # Take first image from batch
            else:
                image_tensor = image
            
            # Convert from tensor to numpy array and scale to 0-255
            image_np = (image_tensor.cpu().numpy() * 255).astype(np.uint8)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image_np, mode='RGB')
            
            # Convert PIL image to bytes
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Encode to base64
            image_bytes = img_buffer.getvalue()
            image_data = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create the request payload for Together.ai Qwen model using chat completions API
            payload = {
                "model": "Qwen/Qwen3-VL-32B-Instruct",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ]
                }],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            # Set up headers
            headers = {
                "Authorization": f"Bearer {together_api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info("Calling Together.ai vision model with chat completions API...")
            
            # Call the Together.ai API using chat completions endpoint
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            
            # Extract response text
            model_response = response_data["choices"][0]["message"]["content"]
            
            logger.info(f"Vision model response received: {model_response[:100]}...")
            return (model_response,)
            
        except Exception as e:
            error_msg = f"Vision model API call failed: {str(e)}"
            logger.error(error_msg)
            return (error_msg,)
