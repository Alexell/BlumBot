from pydantic_settings import BaseSettings, SettingsConfigDict
from bot.utils.logger import log

logo = """

██████  ██      ██    ██ ███    ███     ██████   ██████  ████████
██   ██ ██      ██    ██ ████  ████     ██   ██ ██    ██    ██   
██████  ██      ██    ██ ██ ████ ██     ██████  ██    ██    ██   
██   ██ ██      ██    ██ ██  ██  ██     ██   ██ ██    ██    ██   
██████  ███████  ██████  ██      ██     ██████   ██████     ██   
                                                                 
"""

class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

	API_ID: int
	API_HASH: str
	
	GAMES_ENABLED: bool = True
	GAME_POINTS: list[int] = [100, 200]
	SLEEP_BETWEEN_GAME: list[int] = [10, 20]
	
	SLEEP_BETWEEN_START: list[int] = [20, 360]
	ERRORS_BEFORE_STOP: int = 3
	USE_PROXY_FROM_FILE: bool = False

try:
	config = Settings()
except Exception as error:
	log.error(error)
	config = False