import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboBaseNode:
    """Base class for all Obobo nodes. Provides common functionality like tooltip input."""
    
    def __init__(self):
        self.tooltip = ""
        logger.info(f"{self.__class__.__name__} node initialized")

    @classmethod
    def get_base_input_types(cls):
        """Returns the base input types that all Obobo nodes should have"""
        return {
            "required": {
            },
            "optional": {
                "tooltip": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Enter tooltip text here...",
                    "tooltip": "Tooltip text for documentation/reference (not used in processing)"
                }),
                "optional_input": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "True = optional input, False = required input"
                }),
            }
        }

    @classmethod
    def INPUT_TYPES(cls):
        """This should be overridden by child classes to add their specific inputs"""
        raise NotImplementedError("Child classes must implement INPUT_TYPES")

    def get_tooltip(self):
        """Helper method to get the tooltip value"""
        return getattr(self, 'tooltip', '')

    def set_tooltip(self, tooltip):
        """Helper method to set the tooltip value"""
        self.tooltip = tooltip 
        
    def get_optional_input(self):
        """Helper method to get the optional_input value"""
        return getattr(self, 'optional_input', False)

    def set_optional_input(self, optional_input):
        """Helper method to set the optional_input value"""
        self.optional_input = optional_input