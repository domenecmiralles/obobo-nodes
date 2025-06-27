import logging
from .obobo_base_node import OboboBaseNode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputVector2(OboboBaseNode):
    def __init__(self):
        super().__init__()
        self.x = 0
        self.y = 0
        self.name = ""
        logger.info("OboboInputVector2 node initialized")

    @classmethod
    def INPUT_TYPES(s):
        base_inputs = s.get_base_input_types()
        node_inputs = {
            "x": ("INT", {
                "default": 1024, 
                "min": 0, 
                "max": 8192, 
                "step": 1,
                "tooltip": "X component (width, horizontal dimension)"
            }),
            "y": ("INT", {
                "default": 1024, 
                "min": 0, 
                "max": 8192, 
                "step": 1,
                "tooltip": "Y component (height, vertical dimension)"
            }),
            "name": ("STRING", {
                "default": "Resolution",
                "placeholder": "Optional custom name",
                "tooltip": "Custom name to identify this vector input"
            }),
        }
        
        return {
            "required": {**node_inputs, **base_inputs.get("required", {})},
            "optional": base_inputs.get("optional", {})
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("x", "y")
    FUNCTION = "process_vector2"
    CATEGORY = "obobo/input"
    DESCRIPTION = "Input node for 2D vectors (width and height) for Obobo workflows"

    def process_vector2(self, x, y, name, tooltip=""):
        """Process and return the vector components"""
        try:
            self.x = x
            self.y = y
            self.set_tooltip(tooltip)
            
            logger.info(f"Vector2 input processed: ({x}, {y})")
            
            return (x, y)
        except Exception as e:
            logger.error(f"Error processing vector2: {str(e)}")
            raise 