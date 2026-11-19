# --- Imports ---
from pathlib import Path
from kivy.core.audio import SoundLoader

# --- Audio Feedback ---
class AudioFeedback:
    def __init__(self, root, configuration):
        self.enabled = configuration["enabled"]
        self.volume = configuration["volume"]
        self.clips = {}
        for name in configuration["effects"]:
            sound = SoundLoader.load(str(Path(root) / "data" / "audio" /
                                         (name + "." + configuration["file_extension"])))
            if sound:
                sound.volume = self.volume
                self.clips[name] = sound

    def play(self, name):
        if self.enabled and name in self.clips:
            sound = self.clips[name]
            sound.stop()
            sound.play()
