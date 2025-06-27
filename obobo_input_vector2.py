import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputVector2:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.name = ""
        logger.info("OboboInputVector2 node initialized")

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
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
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("x", "y")
    FUNCTION = "process_vector2"
    CATEGORY = "obobo/input"
    DESCRIPTION = "Input node for 2D vectors (width and height) for Obobo workflows"

    def process_vector2(self, x, y, name):
        """Process and return the vector components"""
        try:
            self.x = x
            self.y = y
            
            logger.info(f"Vector2 input processed: ({x}, {y})")
            
            return (x, y)
        except Exception as e:
            logger.error(f"Error processing vector2: {str(e)}")
            raise 