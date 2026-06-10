"""
ShotTaker — export & share helpers: zip bundles, contact sheets, animated GIFs.
"""

import os
import time
import zipfile

import config

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


def _export_dir():
    d = config.data_path("Exports")
    os.makedirs(d, exist_ok=True)
    return d


def export_zip(paths, name=None):
    """Zip the given screenshots into Exports/. Returns the zip path."""
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return None
    name = name or f"shottaker_export_{time.strftime('%Y%m%d_%H%M%S')}"
    out = os.path.join(_export_dir(), f"{name}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, arcname=os.path.basename(p))
    return out


def contact_sheet(paths, cols=4, thumb=(480, 270), pad=12, name=None):
    """Build a montage grid of the given screenshots. Returns the image path."""
    if not PIL_AVAILABLE:
        return None
    paths = [p for p in paths if os.path.exists(p)][:60]
    if not paths:
        return None

    rows = (len(paths) + cols - 1) // cols
    tw, th = thumb
    W = cols * tw + (cols + 1) * pad
    H = rows * th + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (13, 14, 19))  # brand bg

    for i, p in enumerate(paths):
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail((tw, th), Image.LANCZOS)
            r, c = divmod(i, cols)
            x = pad + c * (tw + pad) + (tw - im.width) // 2
            y = pad + r * (th + pad) + (th - im.height) // 2
            sheet.paste(im, (x, y))
        except Exception:
            continue

    name = name or f"shottaker_contactsheet_{time.strftime('%Y%m%d_%H%M%S')}"
    out = os.path.join(_export_dir(), f"{name}.jpg")
    sheet.save(out, "JPEG", quality=88, optimize=True)
    return out


def make_gif(paths, fps=2, max_size=(960, 540), name=None):
    """Stitch screenshots into an animated GIF. Returns the gif path."""
    if not PIL_AVAILABLE:
        return None
    paths = [p for p in paths if os.path.exists(p)][:120]
    if len(paths) < 2:
        return None
    frames = []
    for p in paths:
        try:
            im = Image.open(p).convert("RGB")
            im.thumbnail(max_size, Image.LANCZOS)
            frames.append(im)
        except Exception:
            continue
    if len(frames) < 2:
        return None
    name = name or f"shottaker_clip_{time.strftime('%Y%m%d_%H%M%S')}"
    out = os.path.join(_export_dir(), f"{name}.gif")
    duration = int(1000 / max(1, fps))
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=duration, loop=0, optimize=True)
    return out
