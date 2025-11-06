import os
import json
import boto3
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
        """Call AWS Mistral text model"""
        try:
            # Initialize Bedrock client
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name='eu-west-2',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            
            # Format the prompt in Mistral's instruction format
            formatted_prompt = f"<s>[INST] {prompt} [/INST]"
            
            # Create the native request payload for Mistral
            native_request = json.dumps({
                "prompt": formatted_prompt,
                "max_tokens": 2000,
                "temperature": 0.8
            })
            
            logger.info(f"Calling Mistral text model with prompt: {prompt[:100]}...")
            
            # Call the Mistral API using invoke_model
            response = bedrock_runtime.invoke_model(
                modelId='mistral.mistral-large-2402-v1:0',
                body=native_request,
                contentType='application/json'
            )
            
            # Parse the response body
            response_body = json.loads(response['body'].read())
            
            # Extract response text from Mistral's response format
            model_response = response_body["outputs"][0]["text"]
            
            logger.info(f"Text model response received: {model_response[:100]}...")
            return (model_response,)
            
        except Exception as e:
            error_msg = f"Text model API call failed: {str(e)}"
            logger.error(error_msg)
            return (error_msg,)
    
    def _call_vision_model(self, prompt, images):
        """Call AWS Nova vision model with multiple images"""
        try:
            # Initialize Bedrock client
            bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name='eu-west-2',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            
            logger.info(f"Calling Nova vision model with {len(images)} image(s) and prompt: {prompt[:100]}...")
            
            # Create message content starting with the text prompt
            message_content = [{"text": prompt}]
            
            # Process each image and add to message content
            for i, image in enumerate(images):
                logger.info(f"Processing image {i+1} with shape: {image.shape}")
                
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
                
                # Add image to message content
                message_content.append({
                    "image": {
                        "format": "png",
                        "source": {
                            "bytes": base64.b64decode(image_data)
                        }
                    }
                })
            
            # Create conversation format for Nova
            conversation = [{
                "role": "user",
                "content": message_content
            }]
            
            logger.info("Calling Nova vision model...")
            
            # Call the Nova API
            response = bedrock_runtime.converse(
                modelId='amazon.nova-pro-v1:0',
                messages=conversation,
                inferenceConfig={
                    "maxTokens": 2000,
                    "temperature": 0.7,
                    "topP": 0.9
                }
            )
            
            # Extract response text
            model_response = response["output"]["message"]["content"][0]["text"]
            
            logger.info(f"Vision model response received: {model_response[:100]}...")
            return (model_response,)
            
        except Exception as e:
            error_msg = f"Vision model API call failed: {str(e)}"
            logger.error(error_msg)
            return (error_msg,)
