from .obobo_input_media import OboboInputMedia

class OboboInputAudio(OboboInputMedia):
    @classmethod
    def INPUT_TYPES(cls):
        base_inputs = cls.get_base_input_types()
        node_inputs = {
            "audio_path": ("STRING", {
                "default": "",
                "placeholder": "Path to audio file",
                "tooltip": "Full path to the audio file or relative path from ComfyUI root"
            }),
            "name": ("STRING", {
                "default": "Audio",
                "placeholder": "Optional custom name",
                "tooltip": "Custom name to identify this audio input"
            }),
        }
        
        return {
            "required": {**node_inputs, **base_inputs.get("required", {})},
            "optional": base_inputs.get("optional", {})
        }

    RETURN_TYPES = OboboInputMedia.RETURN_TYPES
    RETURN_NAMES = OboboInputMedia.RETURN_NAMES
    OUTPUT_IS_LIST = OboboInputMedia.OUTPUT_IS_LIST
    FUNCTION = "process_audio"
    CATEGORY = "obobo/input"
    DESCRIPTION = "Specify an audio file path for Obobo workflows"

    def process_audio(self, audio_path, name, tooltip=""):
        self.set_tooltip(tooltip)
        return self.process_media(audio_path, name, tooltip)