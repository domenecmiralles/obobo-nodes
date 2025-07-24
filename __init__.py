"""
Obobo Nodes for ComfyUI
Provides Obobo input/output nodes and worker management functionality
"""

import logging
import os
import sys
import traceback

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

logger = logging.getLogger(__name__)

# Import existing Obobo nodes
from .nodes.obobo_input_text import OboboInputText
from .nodes.obobo_input_number import OboboInputNumber
from .nodes.obobo_input_image import OboboInputImage
from .nodes.obobo_input_video import OboboInputVideo
from .nodes.obobo_input_audio import OboboInputAudio
from .nodes.obobo_input_lora import OboboInputLora
from .nodes.obobo_input_vector2 import OboboInputVector2
from .nodes.obobo_output import OboboOutput
from .nodes.obobo_conditional_bypass import OboboConditionalBypass

# Import worker web extension
try:
    from .user_interface import web as worker_web
    logger.info("🎬 Obobo Worker web extension loaded successfully")
except Exception as e:
    logger.error(f"🎬 Failed to load Obobo Worker web extension: {e}")
    logger.error(f"🎬 Error details: {traceback.format_exc()}")

# ComfyUI Node mappings (required by ComfyUI)
NODE_CLASS_MAPPINGS = {
    "OboboInputText": OboboInputText,
    "OboboInputNumber": OboboInputNumber,
    "OboboInputImage": OboboInputImage,
    "OboboInputVideo": OboboInputVideo,
    "OboboInputAudio": OboboInputAudio,
    "OboboInputLora": OboboInputLora,
    "OboboInputVector2": OboboInputVector2,
    "OboboOutput":  OboboOutput,
    "OboboConditionalBypass": OboboConditionalBypass,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OboboInputText": "Obobo Text Input",
    "OboboInputNumber": "Obobo Number Input",
    "OboboInputImage": "Obobo Image Input",
    "OboboInputVideo": "Obobo Video Input",
    "OboboInputAudio": "Obobo Audio Input",
    "OboboOutput": "Obobo Output",
    "OboboInputLora": "Obobo LoRA Input",
    "OboboInputVector2": "Obobo Vector2 Input",
    "OboboConditionalBypass": "Obobo Conditional Bypass",
}

# Web extension mappings (required by ComfyUI for JavaScript extensions)
WEB_DIRECTORY = "./user_interface/js"

# Register with ComfyUI
__all__ = [
    "NODE_CLASS_MAPPINGS", 
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY"
]

logger.info("🎬 Obobo Worker Manager loaded successfully")