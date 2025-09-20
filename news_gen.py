from pathlib import Path
from typing import Iterable
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import pyttsx3
import os

DEFAULT_DURATION = 3.0   # seconds per slide
W, H = 1280, 720         # output resolution

def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except Exception:
        return ImageFont.load_default()

def stylize_slide(img_path: Path, headline: str) -> Path:
    img = Image.open(img_path).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img)

    # bottom banner
    banner_h = int(H * 0.16)
    draw.rectangle([0, H - banner_h, W, H], fill=(18, 19, 24))          # dark bar
    draw.rectangle([0, H - banner_h, 300, H], fill=(231, 76, 60))       # red strip

    # texts
    live_font = _font(42)
    hl_font = _font(44)
    draw.text((24, H - banner_h + 22), "BREAKING", font=live_font, fill="white")
    draw.text((330, H - banner_h + 18), headline, font=hl_font, fill="white")

    out_path = img_path.with_suffix(".framed.jpg")
    img.save(out_path, quality=92)
    return out_path

def _narrate(text: str, out_audio: Path):
    """Generate a WAV using pyttsx3 and return the path."""
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.save_to_file(text, str(out_audio))
    engine.runAndWait()
    # Explicitly stop/cleanup engine so no handle remains.
    try:
        engine.stop()
    except Exception:
        pass
    return out_audio

def build_video(image_files: Iterable[Path], out_dir: Path, headline: str, narration: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_dir / "_tmp_audio"
    tmp_dir.mkdir(exist_ok=True)

    # Build slides
    slides = [stylize_slide(Path(p), headline) for p in image_files]
    clips = [ImageClip(str(p)).set_duration(DEFAULT_DURATION) for p in slides]
    video = concatenate_videoclips(clips, method="compose")

    out_mp4 = out_dir / "news_video.mp4"

    audio_clip = None
    wav_path = None
    try:
        if narration:
            wav_path = tmp_dir / "narration.wav"
            _narrate(narration, wav_path)
            audio_clip = AudioFileClip(str(wav_path))
            video = video.set_audio(audio_clip)

        # Write final video
        video.write_videofile(
            str(out_mp4), fps=30, codec="libx264",
            audio_codec="aac", verbose=False, logger=None
        )
    finally:
        # Close resources so Windows can release file locks
        try:
            if audio_clip:
                audio_clip.close()
        except Exception:
            pass
        try:
            video.close()
        except Exception:
            pass
        # Remove temp wav (ignore if busy)
        if wav_path and wav_path.exists():
            try:
                os.remove(wav_path)
            except Exception:
                pass

    return out_mp4
