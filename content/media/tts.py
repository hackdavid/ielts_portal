"""Light local TTS: Piper (CPU, one ~77 MB multi-speaker voice), espeak-ng fallback.

Dialogue turns get different VCTK speakers so a two-person IELTS Part 1 sounds
like two people. Output is MP3 via ffmpeg when available, WAV otherwise.
"""

import io
import shutil
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

from django.conf import settings

VOICE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/vctk/"
    "medium/en_GB-vctk-medium.onnx"
)
# VCTK speaker ids alternating high / low pitch (measured median F0 ≈ 233, 90,
# 248, 94, 235, 103, 223, 91 Hz) so dialogue roles are easy to tell apart.
SPEAKERS = [1, 13, 6, 10, 27, 7, 11, 20]
PAUSE_SEC = 0.6


def voice_path():
    return Path(settings.CONTENT_TTS_DIR) / f"{settings.CONTENT_TTS_VOICE}.onnx"


def piper_ready():
    path = voice_path()
    return (
        settings.CONTENT_TTS_ENABLED
        and path.exists()
        and Path(f"{path}.json").exists()
    )


def download_voice():
    """Fetch the Piper voice + config into CONTENT_TTS_DIR (≈77 MB, once)."""
    import urllib.request

    path = voice_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    base = VOICE_URL.rsplit("/", 1)[0] + "/" + settings.CONTENT_TTS_VOICE
    for suffix in (".onnx", ".onnx.json"):
        target = Path(f"{path.with_suffix('')}{suffix}")
        if not target.exists():
            urllib.request.urlretrieve(base + suffix, target)  # noqa: S310
    return path


@lru_cache(maxsize=1)
def _voice():
    from piper import PiperVoice

    return PiperVoice.load(str(voice_path()))


def _piper_turn(text, speaker):
    from piper import SynthesisConfig

    voice = _voice()
    n_speakers = voice.config.num_speakers or 1
    cfg = SynthesisConfig(speaker_id=speaker % n_speakers if n_speakers > 1 else None)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        voice.synthesize_wav(text, wav, syn_config=cfg)
    return buf.getvalue()


def _espeak_turn(text, speaker):
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if not binary:
        raise RuntimeError("No TTS available: install Piper voice or espeak-ng.")
    variant = ["en-gb", "en-gb+f3", "en-gb+m3", "en-gb+f4"][speaker % 4]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "t.wav"
        subprocess.run(
            [binary, "-v", variant, "-s", "150", "-w", str(out), text],
            check=True,
            capture_output=True,
        )
        return out.read_bytes()


def _join(clips):
    """Concatenate WAV clips (same format) with a short pause between them."""
    params, frames = None, []
    for clip in clips:
        with wave.open(io.BytesIO(clip)) as w:
            if params is None:
                params = w.getparams()
            elif w.getframerate() != params.framerate:
                raise RuntimeError("Mixed sample rates in one recording.")
            frames.append(w.readframes(w.getnframes()))
    silence = b"\0" * int(params.framerate * PAUSE_SEC) * params.sampwidth
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(params.nchannels)
        w.setsampwidth(params.sampwidth)
        w.setframerate(params.framerate)
        w.writeframes(silence.join(frames))
    seconds = sum(len(f) for f in frames) / (params.framerate * params.sampwidth)
    seconds += PAUSE_SEC * (len(frames) - 1)
    return out.getvalue(), int(seconds * 1000)


def _to_mp3(wav_bytes):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    proc = subprocess.run(
        [ffmpeg, "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-b:a", "64k"]
        + ["-f", "mp3", "pipe:1"],
        input=wav_bytes,
        capture_output=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 and proc.stdout else None


def synthesize(turns):
    """[{speaker, text}] → (bytes, content_type, ext, duration_ms, provider, model)."""
    cast = {}
    for turn in turns:
        cast.setdefault(turn["speaker"], SPEAKERS[len(cast) % len(SPEAKERS)])
    use_piper = piper_ready()
    clips = []
    for turn in turns:
        speaker = cast[turn["speaker"]]
        if use_piper:
            clips.append(_piper_turn(turn["text"], speaker))
        else:
            clips.append(_espeak_turn(turn["text"], list(cast).index(turn["speaker"])))
    wav_bytes, duration = _join(clips)
    provider, model = (
        ("piper", settings.CONTENT_TTS_VOICE) if use_piper else ("espeak-ng", "en-gb")
    )
    mp3 = _to_mp3(wav_bytes)
    if mp3:
        return mp3, "audio/mpeg", "mp3", duration, provider, model, cast
    return wav_bytes, "audio/wav", "wav", duration, provider, model, cast
