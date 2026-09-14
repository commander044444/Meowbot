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

# فونت فارسی داخل پروژه
_FONT_DIR = Path(__file__).resolve().parent / "fonts"
_PERSIAN_FONT = _FONT_DIR / "NotoSansArabic-Bold.ttf"

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


def _prepare_text(text: str) -> str:
    """شکل‌دهی فارسی/عربی + RTL تا حروف به‌هم‌پیوسته درست دیده شوند."""
    text = str(text)
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        print(f"ℹ️ persian reshape skipped: {e}")
        return text


def _load_font(size: int):
    """اول فونت فارسی پروژه، بعد فونت‌های سیستم."""
    candidates = [
        str(_PERSIAN_FONT),
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


def _load_latin_font(size: int):
    """فونت لاتین برای واترمارک darkknightstudio (نه عربی)."""
    candidates = [
        str(_FONT_DIR / "DejaVuSans.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    # fallback: همان پیش‌فرض pillow برای لاتین معمولاً OK است
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
    max_w = int(img_w * 0.94)
    # متن بزرگ‌تر: حدود ۱/۷ ضلع کوچک‌تر تصویر
    base = max(28, min(img_w, img_h) // 7)
    base = min(base, 72)
    for size in range(base, 17, -2):
        font = _load_font(size)
        lines = _wrap_text(draw, text, font, max_w)
        if not lines:
            return font, []
        sample = lines[0]
        line_h = draw.textbbox((0, 0), sample, font=font)[3] - draw.textbbox((0, 0), sample, font=font)[1]
        line_h = max(line_h, size + 4)
        total_h = line_h * len(lines) + 6 * (len(lines) - 1)
        widest = max(
            (draw.textbbox((0, 0), ln, font=font)[2] - draw.textbbox((0, 0), ln, font=font)[0])
            for ln in lines
        )
        # تا ۴۵٪ ارتفاع تصویر برای متن مجاز
        if total_h <= img_h * 0.45 and widest <= max_w:
            return font, lines
    font = _load_font(20)
    return font, _wrap_text(draw, text, font, max_w)


def _draw_caption(frame: "Image.Image", text: str) -> "Image.Image":
    """یک فریم RGBA با متن پایین‌وسط + outline."""
    img = frame.convert("RGBA")
    # لایه متن جدا
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # فارسی: reshape + bidi قبل از اندازه‌گیری و رسم
    text = _prepare_text(text)

    font, lines = _fit_font_and_lines(draw, text, img.width, img.height)
    if not lines:
        return img.convert("P", palette=Image.ADAPTIVE)

    line_heights = []
    widths = []
    for ln in lines:
        bb = draw.textbbox((0, 0), ln, font=font)
        widths.append(bb[2] - bb[0])
        line_heights.append(bb[3] - bb[1])

    gap = max(4, int(img.height * 0.012))
    total_h = sum(line_heights) + gap * (len(lines) - 1)
    # فاصله از لبه پایین — متن کمی بالاتر تا نچسبد به لبه
    margin_bottom = max(16, int(img.height * 0.17))
    y = img.height - margin_bottom - total_h
    # حداقل فاصله از بالا برای متن‌های خیلی بلند
    if y < int(img.height * 0.45):
        y = int(img.height * 0.45)

    stroke = max(3, int(min(img.width, img.height) / 80))
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

    # واترمارک کوچک بالا-چپ — فونت لاتین، محو، کمی پایین‌تر از لبه
    wm = "darkknightstudio"
    wm_size = max(9, min(img.width, img.height) // 32)
    wm_font = _load_latin_font(wm_size)
    pad_x = max(4, int(img.width * 0.02))
    # ۳٪ پایین‌تر از لبه بالا
    pad_y = max(4, int(img.height * 0.03)) + max(2, int(img.height * 0.02))
    # رنگ محو خاکستری روشن — نه خیلی معلوم
    draw.text(
        (pad_x, pad_y),
        wm,
        font=wm_font,
        fill=(220, 220, 220, 110),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 90),
    )

    composed = Image.alpha_composite(img, overlay)
    # GIF palette
    return composed.convert("RGB")


def _detect_format(data: bytes) -> str:
    """تشخیص فرمت از magic bytes."""
    if not data or len(data) < 12:
        return "unknown"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:4] == b"\x1aE\xdf\xa3":
        return "webm"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    # بعضی پاسخ‌های خطا متنی‌اند
    head = data[:80].lstrip()
    if head.startswith(b"<") or head.startswith(b"{") or head.startswith(b"error"):
        return "error_payload"
    return "unknown"


def _resolve_ffmpeg() -> str:
    """مسیر ffmpeg: اول imageio-ffmpeg (برای Railway)، بعد سیستم."""
    import shutil
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path:
            return path
    except Exception as e:
        print(f"ℹ️ imageio-ffmpeg unavailable: {e}")
    system = shutil.which("ffmpeg")
    if system:
        return system
    raise RuntimeError(
        "ffmpeg پیدا نشد. imageio-ffmpeg را در requirements نصب کن "
        "یا ffmpeg را روی سرور بگذار."
    )


def _mp4_to_gif_bytes(video_bytes: bytes) -> bytes:
    """تبدیل Animation/MP4 به GIF با ffmpeg (باینری imageio یا سیستم)."""
    import subprocess

    ffmpeg_bin = _resolve_ffmpeg()
    print(f"🎬 using ffmpeg: {ffmpeg_bin}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "in.mp4"
        out = td / "out.gif"
        src.write_bytes(video_bytes)

        # fps محدود + مقیاس برای حجم کمتر
        cmd = [
            ffmpeg_bin, "-y", "-loglevel", "error",
            "-i", str(src),
            "-vf", f"fps=12,scale={MAX_SIDE}:-1:flags=lanczos:force_original_aspect_ratio=decrease",
            "-frames:v", str(MAX_FRAMES),
            "-gifflags", "+transdiff",
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=90)
        if proc.returncode != 0 or not out.is_file() or out.stat().st_size < 20:
            err = (proc.stderr or b"").decode("utf-8", "ignore")[:400]
            raise ValueError(f"تبدیل MP4 به GIF ناموفق: {err or 'خروجی خالی'}")
        return out.read_bytes()


def add_text_to_gif(gif_bytes: bytes, text: str) -> bytes:
    """
    متن را روی همه فریم‌ها می‌کشد و GIF جدید برمی‌گرداند.
    از GIF واقعی و Animationهای MP4 پشتیبانی می‌کند.
    """
    if Image is None:
        raise RuntimeError("Pillow نصب نیست. pip install Pillow")

    if not gif_bytes:
        raise ValueError("فایل خالی است")
    if len(gif_bytes) > MAX_FILE_BYTES:
        raise ValueError("حجم فایل زیاد است (حداکثر حدود ۸ مگابایت)")

    text = str(text).strip()
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "…"

    fmt = _detect_format(gif_bytes)
    print(f"🎬 gif_caption: detected={fmt} size={len(gif_bytes)}")

    if fmt == "error_payload":
        raise ValueError("دانلود فایل نامعتبر بود (پاسخ خطا از سرور)")
    if fmt in ("mp4", "webm", "unknown"):
        # بله اغلب Animation را به‌صورت MP4 می‌فرستد
        try:
            gif_bytes = _mp4_to_gif_bytes(gif_bytes)
            fmt = _detect_format(gif_bytes)
            print(f"🎬 after ffmpeg: detected={fmt} size={len(gif_bytes)}")
        except Exception as e:
            if fmt != "unknown":
                raise
            # unknown: یک‌بار با Pillow امتحان می‌شود پایین
            print(f"ℹ️ ffmpeg convert skipped/failed: {e}")

    if fmt not in ("gif", "unknown"):
        # jpeg/png تکی → یک فریم GIF
        if fmt in ("jpeg", "png", "webp"):
            img = Image.open(io.BytesIO(gif_bytes)).convert("RGB")
            w, h = img.size
            scale = min(1.0, MAX_SIDE / max(w, h))
            if scale < 1.0:
                img = img.resize(
                    (max(1, int(w * scale)), max(1, int(h * scale))),
                    Image.Resampling.LANCZOS,
                )
            drawn = _draw_caption(img.convert("RGBA"), text)
            out = io.BytesIO()
            drawn.save(out, format="GIF")
            return out.getvalue()
        raise ValueError(f"فرمت پشتیبانی نمی‌شود: {fmt}")

    try:
        src = Image.open(io.BytesIO(gif_bytes))
    except Exception as e:
        # آخرین تلاش: شاید mp4 بوده و detect اشتباه کرده
        try:
            gif_bytes = _mp4_to_gif_bytes(gif_bytes)
            src = Image.open(io.BytesIO(gif_bytes))
        except Exception:
            raise ValueError(
                f"نمی‌تونم فایل رو به‌عنوان تصویر باز کنم ({e}). "
                "مطمئن شو روی GIF یا Animation ریپلای کردی."
            ) from e

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
        raise ValueError("هیچ فریمی پیدا نشد")

    out = io.BytesIO()
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
    if len(data) > MAX_FILE_BYTES * 1.5 and len(frames_out) > 2:
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
        raise ValueError("حجم فایل زیاد است")

    data = None
    errors = []

    # روش ۱: animation.get() اگر باشد
    if hasattr(file_obj, "get"):
        try:
            data = await file_obj.get()
            if isinstance(data, (bytes, bytearray)) and len(data) > 32:
                data = bytes(data)
            else:
                data = None
        except Exception as e:
            errors.append(f"get:{e}")

    # روش ۲: bot.get_file(file_id) → bytes
    if data is None:
        try:
            raw = await bot.get_file(str(file_id))
            if isinstance(raw, (bytes, bytearray)) and len(raw) > 32:
                data = bytes(raw)
            else:
                errors.append(f"get_file:type={type(raw)} len={len(raw) if raw is not None else 0}")
        except Exception as e:
            errors.append(f"get_file:{e}")

    # روش ۳: save_to_memory
    if data is None and hasattr(file_obj, "save_to_memory"):
        try:
            buf = io.BytesIO()
            await file_obj.save_to_memory(buf)
            raw = buf.getvalue()
            if raw and len(raw) > 32:
                data = raw
        except Exception as e:
            errors.append(f"save_to_memory:{e}")

    if not data:
        raise ValueError("نتوانستم فایل را دانلود کنم: " + " | ".join(errors[:3]))

    print(
        f"🎬 downloaded {len(data)} bytes, head={data[:8]!r}, "
        f"mime={getattr(file_obj, 'mime_type', None)}"
    )
    return data
