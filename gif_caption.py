# ==========================================
# 🎬 MeowBot - GIF Caption
# ==========================================
# ریپلای روی GIF + «گیف متن» → متن روی فریم‌ها
# ==========================================

import io
import re
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageSequence
except ImportError:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageSequence = None


# محدودیت‌ها
MAX_FILE_BYTES = 8 * 1024 * 1024      # 8 MB
MAX_FRAMES = 120
MAX_SIDE = 640                         # بزرگ‌ترین ضلع خروجی
MAX_TEXT_CHARS = 80

_GIF_PREFIXES = (
    "گیف ",
    "گیف\u200c",
    "گیف\n",
    "گیف\t",
    "gif ",
)


def is_gif_caption_command(text: str) -> bool:
    if not text:
        return False
    t = str(text).strip()
    low = t.lower()
    if low == "گیف" or low == "gif":
        return True
    for p in _GIF_PREFIXES:
        if t.startswith(p) or low.startswith(p.lower()):
            return True
    if t.startswith("گیف"):
        return True
    return False


def extract_caption_text(text: str):
    """متن بعد از «گیف» / «gif». None اگر فقط پیشوند باشد."""
    if not text:
        return None
    t = str(text).strip()
    low = t.lower()

    if low.startswith("gif "):
        rest = t[4:].strip()
        return rest if rest else None
    if low == "gif" or t == "گیف":
        return None
    if t.startswith("گیف"):
        rest = t[3:].lstrip(" \t\n\u200c")
        return rest if rest else None
    return None


def get_animation_from_message(msg):
    """
    از پیام Reply شده Animation یا Document از نوع gif را برمی‌گرداند.
    """
    if msg is None:
        return None

    anim = getattr(msg, "animation", None)
    if anim is not None:
        return anim

    # بعضی کلاینت‌ها GIF را به صورت document می‌فرستند
    doc = getattr(msg, "document", None)
    if doc is not None:
        mime = (getattr(doc, "mime_type", None) or "").lower()
        name = (getattr(doc, "file_name", None) or "").lower()
        if "gif" in mime or name.endswith(".gif"):
            return doc

    return None


def _load_font(size: int):
    """فونت bold در صورت وجود؛ وگرنه پیش‌فرض Pillow."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    """شکستن متن به چند خط بر اساس عرض."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return []

    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    # اگر یک کلمه خیلی بلند بود
    final = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            final.append(line)
            continue
        chunk = ""
        for ch in line:
            trial = chunk + ch
            bb = draw.textbbox((0, 0), trial, font=font)
            if bb[2] - bb[0] <= max_width:
                chunk = trial
            else:
                if chunk:
                    final.append(chunk)
                chunk = ch
        if chunk:
            final.append(chunk)
    return final[:6]  # حداکثر ۶ خط


def _fit_font_and_lines(draw, text, img_w, img_h):
    max_w = int(img_w * 0.92)
    # اندازه فونت بر اساس ارتفاع و طول متن
    base = max(14, min(img_w, img_h) // 12)
    for size in range(base, 11, -2):
        font = _load_font(size)
        lines = _wrap_text(draw, text, font, max_w)
        if not lines:
            return font, []
        line_h = draw.textbbox((0, 0), "Ay", font=font)[3]
        total_h = line_h * len(lines) + 4 * (len(lines) - 1)
        widest = max(
            draw.textbbox((0, 0), ln, font=font)[2] for ln in lines
        )
        if total_h <= img_h * 0.35 and widest <= max_w:
            return font, lines
    font = _load_font(12)
    return font, _wrap_text(draw, text, font, max_w)


def _draw_caption(frame: "Image.Image", text: str) -> "Image.Image":
    """یک فریم RGBA با متن پایین‌وسط + outline."""
    img = frame.convert("RGBA")
    # لایه متن جدا
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font, lines = _fit_font_and_lines(draw, text, img.width, img.height)
    if not lines:
        return img.convert("P", palette=Image.ADAPTIVE)

    line_heights = []
    widths = []
    for ln in lines:
        bb = draw.textbbox((0, 0), ln, font=font)
        widths.append(bb[2] - bb[0])
        line_heights.append(bb[3] - bb[1])

    gap = max(2, int(img.height * 0.008))
    total_h = sum(line_heights) + gap * (len(lines) - 1)
    margin_bottom = max(8, int(img.height * 0.04))
    y = img.height - margin_bottom - total_h

    stroke = max(2, int(min(img.width, img.height) / 120))
    for ln, w, h in zip(lines, widths, line_heights):
        x = (img.width - w) // 2
        # outline تیره برای خوانایی
        draw.text(
            (x, y),
            ln,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, 230),
        )
        y += h + gap

    composed = Image.alpha_composite(img, overlay)
    # GIF palette
    return composed.convert("RGB")


def add_text_to_gif(gif_bytes: bytes, text: str) -> bytes:
    """
    متن را روی همه فریم‌ها می‌کشد و GIF جدید برمی‌گرداند.
    """
    if Image is None:
        raise RuntimeError("Pillow نصب نیست. pip install Pillow")

    if not gif_bytes:
        raise ValueError("فایل خالی است")
    if len(gif_bytes) > MAX_FILE_BYTES:
        raise ValueError("حجم GIF زیاد است (حداکثر حدود ۸ مگابایت)")

    text = str(text).strip()
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "…"

    src = Image.open(io.BytesIO(gif_bytes))
    frames_out = []
    durations = []

    count = 0
    for frame in ImageSequence.Iterator(src):
        count += 1
        if count > MAX_FRAMES:
            raise ValueError(f"تعداد فریم‌ها زیاد است (حداکثر {MAX_FRAMES})")

        duration = frame.info.get("duration", 100)
        if not duration or duration < 20:
            duration = 80
        durations.append(int(duration))

        fr = frame.convert("RGBA")
        # مقیاس اگر خیلی بزرگ
        w, h = fr.size
        scale = min(1.0, MAX_SIDE / max(w, h))
        if scale < 1.0:
            fr = fr.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))),
                Image.Resampling.LANCZOS,
            )

        drawn = _draw_caption(fr, text)
        frames_out.append(drawn)

    if not frames_out:
        raise ValueError("هیچ فریمی در GIF پیدا نشد")

    out = io.BytesIO()
    # ذخیره به صورت GIF با حفظ timing
    first, rest = frames_out[0], frames_out[1:]
    save_kwargs = {
        "format": "GIF",
        "save_all": True,
        "append_images": rest,
        "duration": durations[: len(frames_out)],
        "loop": src.info.get("loop", 0),
        "optimize": False,
        "disposal": 2,
    }
    first.save(out, **save_kwargs)
    data = out.getvalue()
    if len(data) > MAX_FILE_BYTES * 1.5:
        # تلاش دوم با کیفیت کمتر: فقط نصف فریم‌ها
        slim = frames_out[::2]
        slim_dur = durations[::2]
        out2 = io.BytesIO()
        slim[0].save(
            out2,
            format="GIF",
            save_all=True,
            append_images=slim[1:],
            duration=slim_dur[: len(slim)],
            loop=0,
            optimize=True,
            disposal=2,
        )
        data = out2.getvalue()
    return data


async def download_animation_bytes(bot, file_obj) -> bytes:
    """دانلود با get_file یا متد خود فایل."""
    file_id = getattr(file_obj, "file_id", None)
    if not file_id:
        raise ValueError("file_id پیدا نشد")

    size = getattr(file_obj, "file_size", None)
    if size and int(size) > MAX_FILE_BYTES:
        raise ValueError("حجم GIF زیاد است")

    # روش ۱: animation.get() اگر باشد
    if hasattr(file_obj, "get"):
        try:
            data = await file_obj.get()
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        except Exception:
            pass

    # روش ۲: bot.get_file(file_id) → bytes
    data = await bot.get_file(file_id)
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)

    # روش ۳: save_to_memory
    if hasattr(file_obj, "save_to_memory"):
        buf = io.BytesIO()
        await file_obj.save_to_memory(buf)
        return buf.getvalue()

    raise ValueError("نتوانستم فایل را دانلود کنم")
