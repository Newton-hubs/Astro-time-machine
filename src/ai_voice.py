from gtts import gTTS
from pathlib import Path
import uuid

OUTPUT_DIR = Path("assets/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_voice_narration(text: str):
    """
    Converts AI sky description text into spoken narration
    and returns generated audio file path
    """

    file_id = uuid.uuid4().hex[:8]
    file_path = OUTPUT_DIR / f"sky_voice_{file_id}.mp3"

    tts = gTTS(
        text=text,
        lang="en",
        slow=False
    )

    tts.save(file_path)

    return str(file_path)
