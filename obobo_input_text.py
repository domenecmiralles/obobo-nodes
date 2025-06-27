import logging
from .obobo_base_node import OboboBaseNode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputText(OboboBaseNode):
    def __init__(self):
        super().__init__()
        self.text = ""
        self.name = ""
        logger.info("OboboInputText node initialized")

    @classmethod
    def INPUT_TYPES(s):
        base_inputs = s.get_base_input_types()
        node_inputs = {
            "text": ("STRING", {
                "default": "", 
                "multiline": True, 
                "placeholder": "Enter text here...",
                "tooltip": "Text input that will be passed to other nodes"
            }),
            "name": ("STRING", {
                "default": "Prompt",
                "placeholder": "Optional custom name",
                "tooltip": "Custom name to identify this text input"
            }),
        }
        
        return {
            "required": {**node_inputs, **base_inputs.get("required", {})},
            "optional": base_inputs.get("optional", {})
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "process_text"
    CATEGORY = "obobo/input"
    DESCRIPTION = "A simple text input node for Obobo workflows"

    def process_text(self, text, name, tooltip=""):
        """Process and return the text input"""
        try:
            self.text = text
            self.set_tooltip(tooltip)
            logger.info(f"Text input processed: {text[:50]}..." if len(text) > 50 else f"Text input processed: {text}")
            return (text,)
        except Exception as e:
            logger.error(f"Error in process_text: {str(e)}")
            raise 