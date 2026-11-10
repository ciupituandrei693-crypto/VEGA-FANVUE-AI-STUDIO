"""CPU-only composition of user-owned local media. No AI image/video models or network calls."""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

SIZES = {"story": (720, 1280), "square": (1080, 1080), "landscape": (1280, 720)}
MAX_PIXELS = 28_000_000
MAX_OUTPUT_BYTES = 50 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def inspect_image(path: Path) -> None:
    """Require a decodable raster before it can be used in media studio."""
    try:
        with Image.open(path) as im:
            if im.format not in {"JPEG", "PNG", "WEBP"} or im.width * im.height > MAX_PIXELS:
                raise ValueError("Imaginea are formatul sau rezoluția neacceptată")
            im.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as ex:
        raise ValueError("Imagine invalidă sau coruptă") from ex


def _font(size: int, bold: bool = False):
    names = (["DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"] if bold else
             ["DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"])
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    result: list[str] = []
    for paragraph in text.splitlines():
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if line and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
                result.append(line)
                line = word
            else:
                line = candidate
        if line:
            result.append(line)
    return result[:10]


def compose(source: Path, output: Path, *, name: str, headline: str,
            subtitle: str = "", format: str = "story") -> tuple[int, int]:
    """Resize a *supplied* photo and overlay captions. Never changes the original."""
    inspect_image(source)
    w, h = SIZES[format]
    with Image.open(source) as raw:
        base = ImageOps.fit(ImageOps.exif_transpose(raw).convert('RGB'), (w, h), method=Image.Resampling.LANCZOS)
    # Semi-transparent gradient under the text (actual photo remains visible).
    veil = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(veil)
    for y in range(h):
        strength = max(0.0, (y / h - 0.45) / 0.55)
        alpha = int(210 * min(1, strength ** 1.2))
        if alpha:
            g.line((0, y, w, y), fill=(12, 6, 30, alpha))
    canvas = Image.alpha_composite(base.convert('RGBA'), veil)
    draw = ImageDraw.Draw(canvas)
    pad = max(36, int(w * .065))
    head_font = _font(max(30, w // 18), True)
    sub_font = _font(max(22, w // 31))
    small_font = _font(max(16, w // 48), True)
    draw.text((pad, pad), 'VEGA  /  AI STUDIO', font=small_font, fill=(250, 230, 255, 245))
    headline_lines = _wrap(draw, headline, head_font, w - 2 * pad)
    subtitle_lines = _wrap(draw, subtitle, sub_font, w - 2 * pad)
    head_step = max(42, int(w / 15))
    sub_step = max(30, int(w / 24))
    y = h - pad - (len(headline_lines) * head_step + len(subtitle_lines) * sub_step + 60)
    y = max(int(h * .49), y)
    for text in headline_lines:
        draw.text((pad, y), text, font=head_font, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(20, 14, 30, 255))
        y += head_step
    y += 12
    for text in subtitle_lines:
        draw.text((pad, y), text, font=sub_font, fill=(237, 215, 250, 255))
        y += sub_step
    draw.text((pad, h - pad + 2), f'{name.upper()} · PERSONAJ AI', font=small_font, fill=(245, 219, 255, 255), anchor='ls')
    canvas.convert('RGB').save(output, format='PNG', optimize=True)
    if output.stat().st_size > MAX_OUTPUT_BYTES:
        output.unlink(missing_ok=True)
        raise ValueError('Graficul rezultat depășește 50 MB')
    return w, h


def ffmpeg_status() -> dict:
    executable = os.environ.get('VEGA_FFMPEG_PATH') or shutil.which('ffmpeg')
    return {'available': bool(executable and Path(executable).is_file()),
            'path': executable or None}


def montage(sources: list[Path], target: Path, *, format: str,
            seconds_per_image: int = 2) -> tuple[int, int, int]:
    if not 1 <= len(sources) <= 6 or seconds_per_image not in (2, 3, 4):
        raise ValueError('1–6 imagini, câte 2–4 secunde')
    status = ffmpeg_status()
    if not status['available']:
        raise RuntimeError('FFmpeg nu este instalat. Instalează FFmpeg local și repornește VEGA.')
    w, h = SIZES[format]
    # 720p-style output reduces CPU usage on modest local machines.
    if max(w, h) > 1280:
        w, h = (720, 1280) if h > w else (1280, 720)
    with tempfile.TemporaryDirectory(prefix='vega-montage-') as td:
        tempdir = Path(td)
        for i, p in enumerate(sources):
            inspect_image(p)
            with Image.open(p) as im:
                frame = ImageOps.fit(ImageOps.exif_transpose(im).convert('RGB'), (w, h), Image.Resampling.LANCZOS)
                frame.save(tempdir / f'frame_{i:03d}.png')
        cmd = [status['path'], '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
               '-framerate', f'1/{seconds_per_image}', '-i', str(tempdir / 'frame_%03d.png'),
               '-vf', 'fps=24,format=yuv420p', '-an', '-c:v', 'libx264',
               '-preset', 'veryfast', '-crf', '28', '-movflags', '+faststart',
               '-t', str(len(sources) * seconds_per_image), str(target)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=150, check=False)
        except (subprocess.TimeoutExpired, OSError) as ex:
            target.unlink(missing_ok=True)
            raise RuntimeError('FFmpeg nu a finalizat procesarea locală') from ex
        if result.returncode != 0 or not target.is_file():
            target.unlink(missing_ok=True)
            raise RuntimeError('FFmpeg: ' + (result.stderr.strip() or 'eroare necunoscută')[:350])
        if target.stat().st_size > MAX_OUTPUT_BYTES:
            target.unlink(missing_ok=True)
            raise ValueError('Video-ul depășește limita de 50 MB')
    return w, h, len(sources) * seconds_per_image
