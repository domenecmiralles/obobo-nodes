import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputText:
    def __init__(self):
        self.text = ""
        self.name = ""
        logger.info("OboboInputText node initialized")

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
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
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "process_text"
    CATEGORY = "obobo/input"
    DESCRIPTION = "A simple text input node for Obobo workflows"

    def process_text(self, text, name):
        """Process and return the text input"""
        try:
            self.text = text
            logger.info(f"Text input processed: {text[:50]}..." if len(text) > 50 else f"Text input processed: {text}")
            return (text,)
        except Exception as e:
            logger.error(f"Error in process_text: {str(e)}")
            raise 