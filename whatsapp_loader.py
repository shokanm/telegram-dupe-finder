from __future__ import annotations
import hashlib
import re
import zipfile
import shutil
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

import config
from db import save_photo, clear_group_by_name
from hasher import compute_md5, compute_phash

MEDIA_PLACEHOLDER = "<Без медиафайлов>"
LINE_RE = re.compile(r'^(\d{2}\.\d{2}\.\d{4}), (\d{2}:\d{2}) - ([^:]+): (.+)$')
WA_NUM_RE = re.compile(r'WA(\d+)', re.IGNORECASE)


def _save_images(src: str, thumb_path: str, full_path: str):
    img = Image.open(src).convert("RGB")
    full = img.copy()
    full.thumbnail((1000, 1000))
    full.save(full_path, "JPEG", quality=85)
    img.thumbnail((128, 128))
    img.save(thumb_path, "JPEG", quality=75)



def _find_export_dir(source: str) -> Path:
    """Принимает путь к zip-архиву или папке, возвращает папку с файлами."""
    source_path = Path(source)

    if source_path.is_dir():
        return source_path

    if source_path.suffix.lower() == ".zip":
        extract_dir = Path("data/whatsapp_tmp")
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)
        with zipfile.ZipFile(source_path, 'r') as zf:
            zf.extractall(extract_dir)
        # WhatsApp иногда кладёт всё в подпапку
        subdirs = [p for p in extract_dir.iterdir() if p.is_dir()]
        if subdirs and not list(extract_dir.glob("*.txt")):
            return subdirs[0]
        return extract_dir

    raise ValueError(f"Неизвестный формат: {source}. Укажи путь к .zip или папке.")


def load_whatsapp_export(source: str):
    """
    Загружает фото из экспорта WhatsApp (zip-архив или папка).
    Сопоставляет фото с отправителями по порядку записей в .txt файле.
    """
    thumbs_dir = Path(config.THUMBS_DIR)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    if not source or not Path(source).exists():
        print(f"  Ошибка: папка не найдена: {source}")
        return

    export_dir = _find_export_dir(source)
    extracted_from_zip = (source != str(export_dir))

    # Находим .txt файл
    txt_files = list(export_dir.glob("*.txt"))
    if not txt_files:
        print("  [WhatsApp] Ошибка: .txt файл не найден в архиве/папке")
        return
    txt_file = txt_files[0]
    group_name = " ".join(txt_file.stem.split())  # нормализуем пробелы (убираем \xa0)

    # Парсим .txt — собираем список (datetime, sender) для каждого медиасообщения
    media_entries: list[tuple[datetime, str]] = []
    with open(txt_file, encoding="utf-8") as f:
        for line in f:
            m = LINE_RE.match(line.strip())
            if m:
                date_str, time_str, sender, message = m.groups()
                if MEDIA_PLACEHOLDER in message:
                    dt = datetime.strptime(
                        f"{date_str} {time_str}", "%d.%m.%Y %H:%M"
                    ).replace(tzinfo=timezone.utc)
                    media_entries.append((dt, sender.strip()))

    # Сортируем jpg-файлы по номеру WA
    jpg_files = sorted(
        export_dir.glob("IMG-*.jpg"),
        key=lambda p: int(m.group(1)) if (m := WA_NUM_RE.search(p.name)) else 0
    )

    # Стабильный group_id через md5 (одинаков между запусками)
    group_id = int(hashlib.md5(group_name.encode()).hexdigest()[:8], 16)

    print(f"\nЗагружаю фото из: {group_name} (WhatsApp)")
    print(f"  Фото в архиве: {len(jpg_files)}, медиазаписей в чате: {len(media_entries)}")

    # Всегда чистим старые данные — WhatsApp экспорт полный, не инкрементальный
    clear_group_by_name(group_name)
    print(f"  Старые данные группы очищены, загружаю заново...")
    if abs(len(jpg_files) - len(media_entries)) > 5:
        print(f"  Предупреждение: количество фото и записей сильно расходится — "
              f"часть данных об отправителях может быть неточной")

    count = 0
    for i, jpg_path in enumerate(jpg_files):
        if i < len(media_entries):
            dt, sender = media_entries[i]
        else:
            # Если записей меньше чем фото — берём дату из имени файла
            date_match = re.search(r'(\d{8})', jpg_path.name)
            if date_match:
                dt = datetime.strptime(date_match.group(1), "%Y%m%d").replace(tzinfo=timezone.utc)
            else:
                dt = datetime.now(timezone.utc)
            sender = "Неизвестно"

        wa_m = WA_NUM_RE.search(jpg_path.name)
        wa_num = int(wa_m.group(1)) if wa_m else i

        thumb_filename = f"wa_{group_id}_{wa_num}.jpg"
        full_filename  = f"wa_{group_id}_{wa_num}_full.jpg"
        thumb_path = str(thumbs_dir / thumb_filename)
        full_path  = str(thumbs_dir / full_filename)

        try:
            file_hash = compute_md5(str(jpg_path))
            phash     = compute_phash(str(jpg_path))
            _save_images(str(jpg_path), thumb_path, full_path)
        except Exception as e:
            print(f"  Пропускаем {jpg_path.name}: {e}")
            continue

        save_photo(
            message_id=wa_num,
            group_id=group_id,
            group_name=group_name,
            sender_id=0,
            sender_name=sender,
            date=dt.isoformat(),
            file_hash=file_hash,
            phash=phash,
            thumb_path=thumb_path,
            full_path=full_path,
        )
        count += 1
        if count % 50 == 0:
            print(f"  [{group_name}] Обработано: {count} фото...")

    print(f"  [{group_name}] Готово: {count} фото загружено.")

    if extracted_from_zip:
        shutil.rmtree(Path("data/whatsapp_tmp"), ignore_errors=True)

    return group_id
