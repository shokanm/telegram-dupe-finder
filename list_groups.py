"""Вспомогательный скрипт: показывает все группы/каналы аккаунта с их ID."""
import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
import config


async def main():
    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    async with client:
        await client.start()
        print(f"\n{'ID':<20} {'Название'}")
        print("-" * 60)
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, (Channel, Chat)):
                print(f"{dialog.id:<20} {dialog.name}")
        print("\nСкопируй нужные ID в config.py (GROUP_1_ID и GROUP_2_ID)")


asyncio.run(main())
