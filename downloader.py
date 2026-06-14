from __future__ import annotations
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import GetForumTopicsRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from PIL import Image
from tqdm import tqdm

import config
from db import save_photo, get_last_run, set_last_run
from hasher import compute_md5, compute_phash


async def _get_sender_name(client: TelegramClient, message) -> tuple[int, str]:
    sender_id = message.sender_id or 0
    try:
        sender = await message.get_sender()
        if sender:
            name = getattr(sender, "first_name", "") or ""
            last = getattr(sender, "last_name", "") or ""
            username = getattr(sender, "username", "") or ""
            full = f"{name} {last}".strip() or username or str(sender_id)
            return sender_id, full
    except Exception:
        pass
    return sender_id, str(sender_id)


async def _save_images(src: str, thumb_path: str, full_path: str):
    img = Image.open(src).convert("RGB")
    full = img.copy()
    full.thumbnail((1000, 1000))
    full.save(full_path, "JPEG", quality=85)
    img.thumbnail((128, 128))
    img.save(thumb_path, "JPEG", quality=75)


async def _iter_messages(client: TelegramClient, entity):
    """Iterate messages from regular group or all topics of a forum group."""
    is_forum = getattr(entity, "forum", False)
    if not is_forum:
        async for msg in client.iter_messages(entity):
            yield msg
        return

    # Forum group — get all topics then iterate each
    print(f"  Форум-группа: получаю топики...")
    try:
        result = await client(GetForumTopicsRequest(
            channel=entity, q="",
            offset_date=0, offset_id=0, offset_topic=0,
            limit=100,
        ))
        topics = result.topics
    except Exception as e:
        print(f"  Не удалось получить топики: {e}. Читаю как обычную группу.")
        async for msg in client.iter_messages(entity):
            yield msg
        return

    print(f"  Топиков найдено: {len(topics)}")
    for topic in topics:
        async for msg in client.iter_messages(entity, reply_to=topic.id):
            yield msg


async def fetch_new_photos(client: TelegramClient, group_id: int, on_progress=None):
    thumbs_dir = Path(config.THUMBS_DIR)
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    entity = await client.get_entity(group_id)
    group_name = getattr(entity, "title", str(group_id))
    is_forum = getattr(entity, "forum", False)

    since = get_last_run(group_id)
    if since is None:
        since = datetime(datetime.now().year, 1, 1, tzinfo=timezone.utc)
        print(f"  [{group_name}] Первый запуск — загрузка с {since.date()}")
    else:
        print(f"  [{group_name}] Инкрементальный запуск — с {since.date()}")

    if is_forum:
        total = 0  # неизвестно заранее для форумов
        print(f"  [{group_name}] Режим: форум с топиками")
    else:
        total = (await client.get_messages(entity, limit=0)).total
        print(f"  [{group_name}] Всего сообщений: {total}")

    count = 0
    processed = 0
    newest_date = since

    with tqdm(total=total or None, desc=group_name, unit="фото", ncols=70, colour="green") as bar:
        async for message in _iter_messages(client, entity):
            # Принимаем фото и изображения отправленные как документ
            is_photo = isinstance(message.media, MessageMediaPhoto)
            is_image_doc = (
                isinstance(message.media, MessageMediaDocument)
                and getattr(message.media.document, "mime_type", "").startswith("image/")
            )
            if not (is_photo or is_image_doc):
                bar.update(1)
                continue

            msg_date = message.date.replace(tzinfo=timezone.utc) if message.date.tzinfo is None else message.date
            processed += 1
            if on_progress:
                on_progress(processed, total, group_name)

            if msg_date <= since:
                bar.update(1)
                continue

            if msg_date > newest_date:
                newest_date = msg_date

            thumb_filename = f"{group_id}_{message.id}.jpg"
            full_filename  = f"{group_id}_{message.id}_full.jpg"
            thumb_path = str(thumbs_dir / thumb_filename)
            full_path  = str(thumbs_dir / full_filename)

            tmp_path = thumb_path + ".tmp"
            while True:
                try:
                    await client.download_media(message, file=tmp_path)
                    break
                except FloodWaitError as e:
                    wait = e.seconds + 5
                    bar.write(f"  FloodWaitError: ждём {wait} сек...")
                    await asyncio.sleep(wait)
                except Exception as e:
                    bar.write(f"  Пропускаем msg {message.id}: {e}")
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    tmp_path = None
                    break

            bar.update(1)

            if not tmp_path or not os.path.exists(tmp_path):
                continue

            try:
                file_hash = compute_md5(tmp_path)
                phash = compute_phash(tmp_path)
                await _save_images(tmp_path, thumb_path, full_path)
            except Exception as e:
                bar.write(f"  Ошибка обработки msg {message.id}: {e}")
                os.remove(tmp_path)
                continue
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            sender_id, sender_name = await _get_sender_name(client, message)

            save_photo(
                message_id=message.id,
                group_id=group_id,
                group_name=group_name,
                sender_id=sender_id,
                sender_name=sender_name,
                date=msg_date.isoformat(),
                file_hash=file_hash,
                phash=phash,
                thumb_path=str(Path(config.THUMBS_DIR) / thumb_filename),
                full_path=str(Path(config.THUMBS_DIR) / full_filename),
            )
            count += 1

    set_last_run(group_id, newest_date if newest_date > since else datetime.now(timezone.utc))
    print(f"  [{group_name}] Готово: загружено {count} новых фото.")
    return group_name
