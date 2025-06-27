from .obobo_input_media import OboboInputMedia

class OboboInputAudio(OboboInputMedia):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
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
        }

    RETURN_TYPES = OboboInputMedia.RETURN_TYPES
    RETURN_NAMES = OboboInputMedia.RETURN_NAMES
    OUTPUT_IS_LIST = OboboInputMedia.OUTPUT_IS_LIST
    FUNCTION = "process_audio"
    CATEGORY = "obobo/input"
    DESCRIPTION = "Specify an audio file path for Obobo workflows"

    def process_audio(self, audio_path, name):
        return self.process_media(audio_path, name)