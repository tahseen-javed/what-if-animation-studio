"""Shared helpers for the video factory (paths, JSON, audio via ffmpeg). Run every tool from the repo root."""
import json, pathlib, re, subprocess, wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
STUDIO = ROOT / 'what-if-studio'
LIB = json.loads((STUDIO / 'src' / 'compiler' / 'library.json').read_text(encoding='utf-8'))
SFX = STUDIO / 'library' / 'sfx'
SR, FPS = 44100, 30


def load(p, default=None):
    p = pathlib.Path(p)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default


def save(p, data):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def vdir(vid):
    return ROOT / 'videos' / vid


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def write_wav(path, x):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def clip(name):
    """A library sound by its name (library/sfx/<name>-<hash>.mp3), or None."""
    hits = sorted(SFX.glob(f'{name}-*.mp3'))
    return hits[0] if hits else None


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBTP)."""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    s = r.stderr[r.stderr.rfind('Summary:'):]
    i = re.search(r'I:\s+(-?[\d.]+) LUFS', s)
    p = re.search(r'Peak:\s+(-?[\d.]+) dBFS', s)
    return (float(i.group(1)) if i else float('-inf')), (float(p.group(1)) if p else float('-inf'))
