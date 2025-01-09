import os
from pathlib import Path
from decouple import RepositoryEnv, Config

BASE_DIR = Path(__file__).parent.parent

# Check config file in ENV_FILE environment variable
env_file = os.environ.get('ENV_FILE', ".env")
# configure decouple from env_file
config = Config(RepositoryEnv(env_file)) if os.path.exists(env_file) else Config(os.environ)

DEBUG = config('DEBUG', default=True, cast=bool)

LOG_LEVEL = 'DEBUG' if DEBUG else 'INFO'

# configure OpenAI settings
OPEN_AI_API_KEY = config('OPEN_AI_API_KEY')
OPEN_AI_MODEL = config('OPEN_AI_MODEL', default='gpt-4-turbo')
TOKEN_LIMITS = config('TOKEN_LIMITS', default=30_000, cast=int)

# configure GitHub settings
GITHUB_API_KEY = config('GITHUB_API_KEY')

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

REPO_CONTENT_PATH_DIR = BASE_DIR / 'repo_data'
REPO_CONTENT_PATH_DIR.mkdir(exist_ok=True)

MAX_CONCURRENT_TASKS = config('MAX_CONCURRENT_TASKS', default=10, cast=int)