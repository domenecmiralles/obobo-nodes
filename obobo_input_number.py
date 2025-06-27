import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputNumber:
    def __init__(self):
        self.number = 0
        self.name = ""
        logger.info("OboboInputNumber node initialized")

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "number": ("FLOAT", {
                    "default": 0, 
                    "min": -1000000, 
                    "max": 1000000, 
                    "step": 0.01,
                    "tooltip": "Numeric input that will be passed to other nodes"
                }),
                "name": ("STRING", {
                    "default": "Duration",
                    "placeholder": "Optional custom name",
                    "tooltip": "Custom name to identify this number input"
                }),
            }
        }

    RETURN_TYPES = ("FLOAT", "INT")
    RETURN_NAMES = ("float", "int")
    FUNCTION = "process_number"
    CATEGORY = "obobo/input"
    DESCRIPTION = "A simple numeric input node for Obobo workflows, providing both float and integer outputs"

    def process_number(self, number, name):
        """Process and return the number input as both float and int"""
        try:
            self.number = number
            logger.info(f"Number input processed: {number}")
            return (float(number), int(number))
        except Exception as e:
            logger.error(f"Error in process_number: {str(e)}")
            raise 