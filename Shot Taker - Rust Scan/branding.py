"""
ShotTaker — brand identity, design tokens, and logo generation.

Single source of truth for the brand. Backend (window/tray/icon) and front-end
(via /api/brand) both read from here so the look stays consistent.

Brand:  ShotTaker  ·  "Every moment worth keeping."
A focus-reticle mark over an electric violet → sky gradient.
"""

import os

# =========================
# BRAND CONSTANTS
# =========================
BRAND = {
    "name":    "ShotTaker",
    "tagline": "Every moment worth keeping.",
    "version": "1.3.0-r",
    "author":  "ShotTaker",
    "url":     "https://github.com/shottaker/shottaker",
    "colors": {
        "bg":       "#0d0e13",   # app background (near-black, slight blue)
        "surface":  "#161922",   # cards / panels
        "raised":   "#1f2330",   # raised controls, hover
        "border":   "#2a2f3d",
        "primary":  "#7c5cff",   # electric violet — brand accent
        "primary2": "#4ea8ff",   # sky blue — gradient partner
        "cyan":     "#22d3ee",   # secondary accent
        "text":     "#e8e9f0",
        "muted":    "#9aa0b4",
        "success":  "#34d399",
        "warn":     "#fbbf24",
        "danger":   "#f87171",
    },
}

# COLORREF (0x00BBGGRR) helpers for the Windows dark titlebar
def _colorref(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b << 16) | (g << 8) | r

TITLEBAR_BG_COLORREF   = _colorref(BRAND["colors"]["bg"])
TITLEBAR_TEXT_COLORREF = _colorref(BRAND["colors"]["text"])


# =========================
# LOGO GENERATION
# Draws the ShotTaker mark: a rounded-square electric gradient with a
# white focus-reticle (4 corner brackets + centre shutter dot).
# =========================
def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _gradient_square(size, c1, c2):
    """Diagonal gradient RGB image."""
    import numpy as np
    from PIL import Image
    top = np.array(_hex(c1), dtype=np.float32)
    bot = np.array(_hex(c2), dtype=np.float32)
    yy = np.linspace(0.0, 1.0, size).reshape(size, 1)
    xx = np.linspace(0.0, 1.0, size).reshape(1, size)
    t = (yy * 0.65 + xx * 0.35)[..., None]
    arr = (top * (1.0 - t) + bot * t).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def render_logo(size=256):
    """Returns a branded RGBA logo Image at the given size."""
    from PIL import Image, ImageDraw

    S = 512  # supersample for crisp edges
    grad = _gradient_square(S, BRAND["colors"]["primary"], BRAND["colors"]["primary2"]).convert("RGBA")

    # Rounded-square mask
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    draw = ImageDraw.Draw(img)

    # Focus reticle: 4 corner brackets
    m = int(S * 0.26)          # inset margin
    arm = int(S * 0.16)        # bracket arm length
    th = int(S * 0.052)        # thickness
    r = th // 2
    white = (255, 255, 255, 236)

    def bracket(cx, cy, dx, dy):
        # horizontal arm
        x0, x1 = sorted([cx, cx + dx * arm])
        draw.rounded_rectangle([x0, cy - r, x1, cy + r], radius=r, fill=white)
        # vertical arm
        y0, y1 = sorted([cy, cy + dy * arm])
        draw.rounded_rectangle([cx - r, y0, cx + r, y1], radius=r, fill=white)

    bracket(m, m, +1, +1)               # top-left
    bracket(S - m, m, -1, +1)           # top-right
    bracket(m, S - m, +1, -1)           # bottom-left
    bracket(S - m, S - m, -1, -1)       # bottom-right

    # Centre shutter dot
    cr = int(S * 0.105)
    cx = cy = S // 2
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 255, 255, 250))

    return img.resize((size, size), Image.LANCZOS)


def generate_icon(force=False, out_dir="static"):
    """
    Writes <out_dir>/icon.png and <out_dir>/icon.ico from the brand mark.
    Returns the .ico path (or None on failure).
    """
    icon_path = os.path.join(out_dir, "icon.ico")
    png_path = os.path.join(out_dir, "icon.png")

    if not force and os.path.exists(icon_path) and os.path.exists(png_path):
        return icon_path

    try:
        from PIL import Image
        os.makedirs(out_dir, exist_ok=True)

        logo = render_logo(256)
        logo.save(png_path, "PNG")

        ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        logo.save(icon_path, format="ICO", sizes=ico_sizes)
        return icon_path

    except Exception as e:
        print(f"[BRAND] Could not generate icon: {e}")
        return None


if __name__ == "__main__":
    # Regenerate brand assets on demand: python branding.py
    path = generate_icon(force=True)
    print(f"[BRAND] {BRAND['name']} {BRAND['version']} — icon written to {path}")
