from .obobo_base_node import OboboBaseNode  # Base class - not instantiable
from .obobo_input_text import OboboInputText
from .obobo_input_number import OboboInputNumber
from .obobo_input_image import OboboInputImage
from .obobo_input_video import OboboInputVideo
from .obobo_input_audio import OboboInputAudio

from .obobo_input_lora import OboboInputLora
from .obobo_input_vector2 import OboboInputVector2
from .obobo_output import OboboOutput


NODE_CLASS_MAPPINGS = {
    "OboboInputText": OboboInputText,
    "OboboInputNumber": OboboInputNumber,
    "OboboInputImage": OboboInputImage,
    "OboboInputVideo": OboboInputVideo,
    "OboboInputAudio": OboboInputAudio,
    "OboboInputLora": OboboInputLora,
    "OboboInputVector2": OboboInputVector2,
    "OboboOutput":  OboboOutput,
    # "OboboPathLoader": OboboPathLoader,
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
    "OboboOutput": "Obobo Output",
    # "OboboPathLoader": "Obobo Path Loader",
    # "OboboInput": "Obobo Input",  # Uncomment if you're keeping the original node
} 