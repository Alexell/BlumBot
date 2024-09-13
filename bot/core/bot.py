import asyncio, aiohttp, random, json
from time import time
from urllib.parse import unquote
from typing import Any, Dict
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView

from bot.utils.logger import log
from bot.utils.settings import config
from .headers import headers

class CryptoBot:
	def __init__(self, tg_client: Client):
		self.session_name = tg_client.name
		self.tg_client = tg_client
		self.errors = 0

	async def get_tg_web_data(self, proxy: str | None) -> str:
		if proxy:
			proxy = Proxy.from_str(proxy)
			proxy_dict = dict(
				scheme=proxy.protocol,
				hostname=proxy.host,
				port=proxy.port,
				username=proxy.login,
				password=proxy.password
			)
		else:
			proxy_dict = None

		self.tg_client.proxy = proxy_dict

		try:
			if not self.tg_client.is_connected:
				try:
					await self.tg_client.connect()
				except (Unauthorized, UserDeactivated, AuthKeyUnregistered) as error:
					raise RuntimeError(str(error)) from error
			web_view = await self.tg_client.invoke(RequestWebView(
				peer=await self.tg_client.resolve_peer('BlumCryptoBot'),
				bot=await self.tg_client.resolve_peer('BlumCryptoBot'),
				platform='android',
				from_bot_menu=False,
				url='https://telegram.blum.codes/'
			))
			auth_url = web_view.url
			tg_web_data = unquote(
				string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])
			if self.tg_client.is_connected:
				await self.tg_client.disconnect()

			return tg_web_data

		except RuntimeError as error:
			raise error

		except Exception as error:
			log.error(f"{self.session_name} | Authorization error: {error}")
			await asyncio.sleep(delay=3)

	async def login(self, init_data: str) -> tuple[str | bool, str]:
		url = 'https://user-domain.blum.codes/api/v1/auth/provider/PROVIDER_TELEGRAM_MINI_APP'
		try:
			log.info(f"{self.session_name} | Trying to login...")
			self.http_client.headers.pop('Authorization', None)
			json_data = {'query': init_data}
			response = await self.http_client.post(url, json=json_data)
			response.raise_for_status()
			response_json = await response.json()
			token = response_json.get('token', {})
			access_token = token.get('access', '')
			refresh_token = token.get('refresh', '')
			log.success(f"{self.session_name} | Login successful")
			return access_token, refresh_token
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			self.errors += 1
			log.error(f"{self.session_name} | Login http error: {error}")
			await asyncio.sleep(delay=3)
			return False, ''
		except Exception as error:
			log.error(f"{self.session_name} | Login error: {error}")
			await asyncio.sleep(delay=3)
			return False, ''

	async def get_profile(self) -> Dict[str, Any]:
		url = 'https://game-domain.blum.codes/api/v1/user/balance'
		try:
			await self.http_client.options(url)
			response = await self.http_client.get(url)
			response.raise_for_status()
			response_json = await response.json()
			return response_json
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			self.errors += 1
			log.error(f"{self.session_name} | Profile data http error: {error}")
			await asyncio.sleep(delay=3)
			return {}
		except Exception as error:
			log.error(f"{self.session_name} | Profile data error: {error}")
			await asyncio.sleep(delay=3)
			return {}

	async def daily_reward(self) -> bool:
		url = 'https://game-domain.blum.codes/api/v1/daily-reward?offset=-180'
		await self.http_client.options(url)
		response = await self.http_client.post(url)
		content_type = response.headers.get('Content-Type', '') # the response can contain both text and json
		try:
			if 'application/json' in content_type:
				response_json = await response.json()
				if response_json.get('message', '') != 'same day':
					log.warning(f"{self.session_name} | Unknown response in daily reward: {str(response_json)}")
				return False
			else:
				response_text = await response.text()
				if response_text == 'OK':
					return True
				else:
					log.warning(f"{self.session_name} | Unknown response in daily reward: {response_text}")
					return False
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			log.error(f"{self.session_name} | Daily reward http error: {str(error)}")
			return False
		except Exception as error:
			log.error(f"{self.session_name} | Daily reward error: {str(error)}")
			return False

	async def farming_claim(self) -> bool:
		url = 'https://game-domain.blum.codes/api/v1/farming/claim'
		try:
			await self.http_client.options(url)
			response = await self.http_client.post(url)
			response.raise_for_status()
			response_json = await response.json()
			balance = response_json.get('availableBalance', False)
			if balance is not False:
				self.balance = int(float(balance))
				return True
			else: return False
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			self.errors += 1
			log.error(f"{self.session_name} | Claim http error: {error}")
			await asyncio.sleep(delay=3)
			return False
		except Exception as error:
			log.error(f"{self.session_name} | Claim error: {error}")
			await asyncio.sleep(delay=3)
			return False
			
	async def farming_start(self) -> bool:
		url = 'https://game-domain.blum.codes/api/v1/farming/start'
		try:
			await self.http_client.options(url)
			response = await self.http_client.post(url)
			response.raise_for_status()
			return True
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			self.errors += 1
			log.error(f"{self.session_name} | Starting farm http error: {error}")
			await asyncio.sleep(delay=3)
			return False
		except Exception as error:
			log.error(f"{self.session_name} | Starting farm error: {error}")
			await asyncio.sleep(delay=3)
			return False

	async def perform_friend_rewards(self) -> None:
		balance_url = 'https://user-domain.blum.codes/v1/friends/balance'
		claim_url  = 'https://user-domain.blum.codes/v1/friends/claim'
		try:
			await self.http_client.options(balance_url)
			response = await self.http_client.post(balance_url)
			response_json = await response.json()
			claim_amount = response_json.get('amountForClaim', 0)
			can_claim = response_json.get('canClaim', False)
			if claim_amount > 0 and can_claim is not False:
				log.info(f"{self.session_name} | Reward for friends available")
				await asyncio.sleep(3)
				await self.http_client.options(claim_url)
				response = await self.http_client.post(claim_url)
				response_json = await response.json()
				claim_amount = response_json.get('claimBalance', 0)
				if claim_amount > 0:
					log.success(f"{self.session_name} | Claimed {claim_amount} points")
					self.errors = 0
				else:
					log.warning(f"{self.session_name} | Unable to claim friend reward")
			else:
				log.info(f"{self.session_name} | Reward for friends not available")
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			self.errors += 1
			log.error(f"{self.session_name} | Friend reward http error: {error}")
			await asyncio.sleep(delay=3)
		except Exception as error:
			log.error(f"{self.session_name} | Friend reward error: {error}")
			await asyncio.sleep(delay=3)

	async def perform_games(self, games: int) -> None:
		start_url = 'https://game-domain.blum.codes/api/v1/game/play'
		finish_url = 'https://game-domain.blum.codes/api/v1/game/claim'
		
		if games > 4: games = 4 # play a maximum of 4 games in a row
		while games > 0:
			try:
				await self.http_client.options(start_url)
				response = await self.http_client.post(start_url)
				response.raise_for_status()
				response_json = await response.json()
				game_id = response_json.get('gameId', False)
				
				if game_id is not False:
					log.info(f"{self.session_name} | Game started")
					await asyncio.sleep(30)
					points = random.randint(*config.GAME_POINTS)
					json_data = {'gameId': game_id, "points": points}
					await self.http_client.options(finish_url)
					response = await self.http_client.post(finish_url, json=json_data)
					response.raise_for_status()
					response_text = await response.text()
					if response_text == 'OK':
						log.success(f"{self.session_name} | Game completed (+{points} points)")
						self.errors = 0
						games -= 1
						await asyncio.sleep(random.randint(*config.SLEEP_BETWEEN_GAME))
			except aiohttp.ClientResponseError as error:
				if error.status == 401: self.authorized = False
				self.errors += 1
				log.error(f"{self.session_name} | Games http error: {error}")
				await asyncio.sleep(delay=3)
			except Exception as error:
				log.error(f"{self.session_name} | Games error: {error}")
				await asyncio.sleep(delay=3)
			
	async def perform_tasks(self) -> None:
		url = 'https://earn-domain.blum.codes/api/v1/tasks'
		try:
			await self.http_client.options(url)
			response = await self.http_client.get(url)
			response.raise_for_status()
			response_json = await response.json()
			started = 0
			completed = 0
			for category in response_json:
				tasks = category.get('tasks', [])
				for task in tasks:
					if started == 2 or completed == 2: break
					if task['status'] == 'FINISHED'or task.get('isHidden', False): continue
					if 'socialSubscription' not in task or task.get('socialSubscription', {}).get('openInTelegram', False): continue
					log.info(f"{self.session_name} | Processing task {task['id']}")
					if task['status'] == 'NOT_STARTED':
						await self.http_client.post(f"https://earn-domain.blum.codes/api/v1/tasks/{task['id']}/start")
						await asyncio.sleep(random.randint(4, 8))
						started += 1
					elif task['status'] == 'READY_FOR_CLAIM':
						await self.http_client.post(f"https://earn-domain.blum.codes/api/v1/tasks/{task['id']}/claim")
						await asyncio.sleep(1)
						log.success(f"{self.session_name} | Task {task['id']} completed and reward claimed")
						self.errors = 0
						await asyncio.sleep(random.randint(2, 4))
						completed += 1
				sub_sections = category.get('subSections', [])
				for sub_section in sub_sections:
					tasks = sub_section.get('tasks', [])
					for task in tasks:
						if started == 2 or completed == 2: break
						if task['status'] == 'FINISHED' or task.get('isHidden', False): continue
						if 'socialSubscription' not in task or task.get('socialSubscription', {}).get('openInTelegram', False): continue
						log.info(f"{self.session_name} | Processing task {task['id']}")
						if task['status'] == 'NOT_STARTED':
							await self.http_client.post(f"https://earn-domain.blum.codes/api/v1/tasks/{task['id']}/start")
							await asyncio.sleep(random.randint(4, 8))
							started += 1
						elif task['status'] == 'READY_FOR_CLAIM':
							await self.http_client.post(f"https://earn-domain.blum.codes/api/v1/tasks/{task['id']}/claim")
							await asyncio.sleep(1)
							log.success(f"{self.session_name} | Task {task['id']} completed and reward claimed")
							self.errors = 0
							await asyncio.sleep(random.randint(2, 4))
							completed += 1
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			self.errors += 1
			log.error(f"{self.session_name} | Tasks http error: {error}")
			await asyncio.sleep(delay=3)
		except Exception as error:
			log.error(f"{self.session_name} | Tasks error: {error}")
			self.errors += 1
			await asyncio.sleep(delay=3)

	async def refresh_tokens(self) -> str | bool:
		url = 'https://user-domain.blum.codes/v1/auth/refresh'
		try:
			await self.http_client.options(url)
			json_data = {'refresh': self.refresh_token}
			response = await self.http_client.post(url, json=json_data)
			response.raise_for_status()
			response_json = await response.json()
			self.access_token = response_json.get('access', '')
			self.refresh_token = response_json.get('refresh', '')
			return True if self.access_token != '' else False
		except aiohttp.ClientResponseError as error:
			if error.status == 401: self.authorized = False
			self.errors += 1
			log.warning(f"{self.session_name} | Refresh auth tokens http error")
			return False
		except Exception:
			log.warning(f"{self.session_name} | Refresh auth tokens error")
			return False

	async def check_proxy(self, proxy: Proxy) -> None:
		try:
			response = await self.http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
			ip = (await response.json()).get('origin')
			log.info(f"{self.session_name} | Proxy IP: {ip}")
		except Exception as error:
			log.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

	async def run(self, proxy: str | None) -> None:
		access_token_created_time = 0
		proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

		async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
			self.http_client = http_client
			if proxy:
				await self.check_proxy(proxy=proxy)

			self.authorized = False
			while True:
				if self.errors >= config.ERRORS_BEFORE_STOP:
					log.error(f"{self.session_name} | Bot stopped (too many errors)")
					break
				try:
					if not self.authorized:
						tg_web_data = await self.get_tg_web_data(proxy=proxy)
						access_token, refresh_token = await self.login(init_data=tg_web_data)
						if access_token is not False and refresh_token != '':
							self.authorized = True
							self.access_token = access_token
							self.refresh_token = refresh_token
							self.http_client.headers['Authorization'] = 'Bearer ' + access_token
							access_token_created_time = time()
						else: continue
				
					if time() - access_token_created_time >= 3600:
						refresh_success = await self.refresh_tokens()
						if refresh_success:
							self.http_client.headers['Authorization'] = 'Bearer ' + self.access_token
							access_token_created_time = time()
						else:
							self.authorized = False
							continue

					daily_claimed = await self.daily_reward()
					if daily_claimed:
						log.success(f"{self.session_name} | Daily reward claimed")
						self.errors = 0
					else:
						log.info(f"{self.session_name} | Daily reward not available")
					
					profile = await self.get_profile()
					self.balance = profile['availableBalance']
					log.info(f"{self.session_name} | Balance: {self.balance}")
					
					await asyncio.sleep(random.randint(2, 4))
					await self.perform_friend_rewards()
					
					games_left = profile['playPasses']
					system_time = profile['timestamp'] // 1000
					farming = profile.get('farming', {})
					farm_start = farming.get('startTime', 0) // 1000
					farm_end = farming.get('endTime', 0) // 1000
					
					await asyncio.sleep(random.randint(2, 4))
					if farm_start == 0 or farm_end == 0:
						log.info(f"{self.session_name} | Start farming...")
						if await self.farming_start():
							log.success(f"{self.session_name} | Farming started successfully")
							self.errors = 0
					elif system_time > farm_end:
						log.info(f"{self.session_name} | Time to claim and restart farming")
						if await self.farming_claim():
							log.success(f"{self.session_name} | Claim successful")
							self.errors = 0
						else: continue
						if await self.farming_start():
							log.success(f"{self.session_name} | Farming restarted successfully")
							self.errors = 0
						else: continue
					
					await asyncio.sleep(random.randint(2, 4))
					await self.perform_tasks()
					
					if config.GAMES_ENABLED and games_left > 0:
						await asyncio.sleep(random.randint(2, 4))
						await self.perform_games(games=games_left)
					
					# Log current balance
					profile = await self.get_profile()
					self.balance = profile['availableBalance']
					log.info(f"{self.session_name} | Balance: {self.balance}")
					
					if system_time < farm_end:
						claim_wait = farm_end - system_time
						hours = claim_wait // 3600
						minutes = (claim_wait % 3600) // 60
						log.info(f"{self.session_name} | Waiting for {hours} hours and {minutes} minutes before claiming and restarting")
						await asyncio.sleep(claim_wait)
					
				except RuntimeError as error:
					raise error
				except Exception as error:
					log.error(f"{self.session_name} | Unknown error: {error}")
					await asyncio.sleep(delay=3)
				else:
					log.info(f"Sleep 1 min")
					await asyncio.sleep(delay=60)

async def run_bot(tg_client: Client, proxy: str | None):
	try:
		await CryptoBot(tg_client=tg_client).run(proxy=proxy)
	except RuntimeError as error:
		log.error(f"{tg_client.name} | Session error: {str(error)}")
