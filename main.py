from __future__ import annotations
import argparse
import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient

import config
from db import init_db, get_all_photos, update_group_name
from downloader import fetch_new_photos
from hasher import find_exact_duplicates, find_similar_duplicates
from reporter import generate_report
from whatsapp_loader import load_whatsapp_export


def parse_args():
    parser = argparse.ArgumentParser(description="Поиск дубликатов фото")
    parser.add_argument(
        "--source",
        choices=["telegram", "whatsapp", "both"],
        default="both",
        help="Источник данных: telegram / whatsapp / both (по умолчанию: both)",
    )
    return parser.parse_args()


async def run_telegram():
    if config.API_ID == 0 or not config.API_HASH:
        print("\nОШИБКА: Заполни API_ID и API_HASH в файле config.py")
        sys.exit(1)
    if config.GROUP_1_ID == 0 or config.GROUP_2_ID == 0:
        print("\nОШИБКА: Заполни GROUP_1_ID и GROUP_2_ID в файле config.py")
        sys.exit(1)

    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    async with client:
        await client.start()
        me = await client.get_me()
        print(f"Авторизован как: {me.first_name} (@{me.username})\n")
        for group_id in (config.GROUP_1_ID, config.GROUP_2_ID):
            real_name = await fetch_new_photos(client, group_id)
            update_group_name(group_id, real_name)
            print()


def run_whatsapp():
    if not config.WHATSAPP_EXPORT:
        print("ОШИБКА: Заполни WHATSAPP_EXPORT в файле config.py")
        sys.exit(1)
    load_whatsapp_export(config.WHATSAPP_EXPORT)
    print()


async def main():
    args = parse_args()

    print("=" * 50)
    print(f"  Источник: {args.source.upper()}")
    print("=" * 50 + "\n")

    Path("data").mkdir(exist_ok=True)
    init_db()

    if args.source in ("telegram", "both"):
        await run_telegram()

    if args.source in ("whatsapp", "both"):
        run_whatsapp()

    print("Анализирую дубликаты...")
    all_photos = get_all_photos()
    print(f"  Всего фото в базе: {len(all_photos)}")

    exact_pairs = find_exact_duplicates(all_photos)
    print(f"  Точных дубликатов: {len(exact_pairs)}")

    exact_hashes = {p["file_hash"] for pair in exact_pairs for p in pair if p.get("file_hash")}
    similar_pairs = find_similar_duplicates(all_photos, config.PHASH_THRESHOLD, exact_hashes)
    print(f"  Похожих пар: {len(similar_pairs)}")

    print("\nГенерирую отчёт...")
    report_path = generate_report(exact_pairs, similar_pairs, total_photos=len(all_photos))
    print(f"\nГотово! Отчёт сохранён:\n  {Path(report_path).resolve()}")
    print("\nОткрой файл в браузере для просмотра результатов.")


if __name__ == "__main__":
    asyncio.run(main())
