import os
import logging
import folder_paths
from .obobo_base_node import OboboBaseNode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboOutput(OboboBaseNode):
    def __init__(self):
        super().__init__()
        self.output_path = None
        self.name = ""
        logger.info("OboboOutput node initialized")

    @classmethod
    def INPUT_TYPES(s):
        base_inputs = s.get_base_input_types()
        node_inputs = {
            "file_path": ("STRING", {
                "default": "", 
                "placeholder": "Path to output file",
                "tooltip": "Full path to where the output should be saved"
            }),
            "name": ("STRING", {
                "default": "Output",
                "placeholder": "Optional custom name",
                "tooltip": "Custom name to identify this output"
            }),
        }
        
        return {
            "required": {**node_inputs, **base_inputs.get("required", {})},
            "optional": base_inputs.get("optional", {})
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "process_output"
    CATEGORY = "obobo/output"
    DESCRIPTION = "Specify an output file path for Obobo workflows"
    OUTPUT_NODE = True

    def process_output(self, file_path, name, tooltip=""):
        """Process the output path input"""
        try:
            if not file_path:
                logger.warning("No output path provided")
                return (None)
            
            self.set_tooltip(tooltip)
            logger.info(f"Output path processed: {file_path}")
            self.output_path = file_path
            return (file_path,)
        except Exception as e:
            logger.error(f"Error processing output path: {str(e)}")
            raise 