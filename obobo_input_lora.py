import logging
import folder_paths
from .obobo_utils import AlwaysEqualProxy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputLora:
    def __init__(self):
        self.lora_path = ""
        self.name = ""
        logger.info("OboboInputLora node initialized")

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "lora_path": ("STRING", {"multiline": True, "default": "text"}),
                "lora_strength": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.0001}),
                
                "name": ("STRING", {
                    "default": "LoRA",
                    "placeholder": "Optional custom name",
                    "tooltip": "Custom name to identify this text input"
                }),
            },
            "optional": {
                 "prev_model": ("MODEL", {
                      "tooltip": "Connect to a model loader if the lora loader requires a model."
                     }),
                 "clip": ("CLIP", {}),
            }
        }

    RETURN_TYPES = (AlwaysEqualProxy('*'), 
                    "CLIP",
                    AlwaysEqualProxy('*'),
                    "FLOAT")
    RETURN_NAMES = ("prev_model",
                    "clip",
                    "lora_path",
                    "lora_strength")
    OUTPUT_IS_LIST = (False, False, True, False)

    OUTPUT_NODE = True

    FUNCTION = "process_loras"
    CATEGORY = "obobo/input"
    DESCRIPTION = "Connect to a LoRa loader"

    def process_loras(self, lora_path, lora_strength, name, prev_model=None, clip=None):
        """Process and return the LoRA selections"""
        lines = lora_path.split('\n')
        rows = lines[0:1]
        prev_model = prev_model if prev_model is not None else None
        clip = clip if clip is not None else None
        return  prev_model, clip, rows, lora_strength