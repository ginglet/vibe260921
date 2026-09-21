"""업로드 이미지를 WebP로 변환하고 크기를 제한한다 (PRD 7. 성능 - 이미지 최적화)."""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def optimize_image(field_file, max_width=1600, quality=82):
    """새로 업로드된 이미지(FieldFile)만 WebP로 바꿔 저장 대기 상태로 만든다."""
    if not field_file or getattr(field_file, "_committed", True):
        return
    try:
        field_file.file.seek(0)
        img = Image.open(field_file.file)
        if getattr(img, "is_animated", False):      # 움직이는 이미지는 그대로 둔다
            field_file.file.seek(0)
            return
        img = ImageOps.exif_transpose(img)
        if img.width > max_width:
            img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
        has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
        img = img.convert("RGBA" if has_alpha else "RGB")
        buf = BytesIO()
        img.save(buf, "WEBP", quality=quality, method=4)
    except Exception:
        field_file.file.seek(0)
        return
    field_file.save(f"{Path(field_file.name).stem}.webp", ContentFile(buf.getvalue()), save=False)
