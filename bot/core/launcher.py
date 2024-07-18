import os
import asyncio
from argparse import ArgumentParser
from pathlib import Path
from itertools import cycle
from pyrogram import Client
from better_proxy import Proxy
from bot.utils.logger import log
from bot.utils.settings import config, logo
from bot.core.bot import run_bot

start_text = logo + """
Select an action:
    1. Create session
    2. Run bot
"""

def get_session_names() -> list[str]:
	session_path = Path('sessions')
	session_files = session_path.glob('*.session')
	session_names = [file.stem for file in session_files]
	return session_names

async def register_sessions() -> None:
	session_name = input('\nEnter the session name (press Enter to exit): ')
	if not session_name: return None
	
	if not os.path.exists(path='sessions'): os.mkdir(path='sessions')

	session = Client(
		name=session_name,
		api_id=config.API_ID,
		api_hash=config.API_HASH,
		workdir="sessions/"
	)

	async with session: user_data = await session.get_me()
	log.success(f"Session added successfully: {user_data.username or user_data.id} | "
                   f"{user_data.first_name or ''} {user_data.last_name or ''}")

def get_proxies() -> list[Proxy]:
	if config.USE_PROXY_FROM_FILE:
		with open(file='proxies.txt', encoding='utf-8-sig') as file:
			proxies = [Proxy.from_str(proxy=row.strip()).as_url for row in file if row.strip()]
	else:
		proxies = []

	return proxies

async def get_tg_clients() -> list[Client]:
	session_names = get_session_names()

	if not session_names:
		raise FileNotFoundError("Not found session files")

	tg_clients = [Client(
		name=session_name,
		api_id=config.API_ID,
		api_hash=config.API_HASH,
		workdir='sessions/',
		plugins=dict(root='bot/plugins')
	) for session_name in session_names]

	return tg_clients

async def run_clients(tg_clients: list[Client]):
	proxies = get_proxies()
	proxies_cycle = cycle(proxies) if proxies else cycle([None])
	clients = [asyncio.create_task(run_bot(tg_client=tg_client, proxy=next(proxies_cycle)))
			 for tg_client in tg_clients]
	await asyncio.gather(*clients)

async def start() -> None:
	if not config:
		log.warning(f"API_ID and API_HASH must be set in the .env file.")
		return
	parser = ArgumentParser()
	parser.add_argument('-a', '--action', type=int, choices=[1, 2], help='Action to perform  (1 or 2)')
	log.info(f"Detected {len(get_session_names())} sessions | {len(get_proxies())} proxies")
	action = parser.parse_args().action

	if not action:
		print(start_text)
		while True:
			action = input('> ').strip()
			if action.isdigit() and action in ['1', '2']:
				action = int(action)
				break
			log.warning("Action must be a number (1 or 2)")

	if action == 1:
		await register_sessions()
	elif action == 2:
		tg_clients = await get_tg_clients()
		await run_clients(tg_clients=tg_clients)