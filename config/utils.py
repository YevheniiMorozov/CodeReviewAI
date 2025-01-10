import re
import shutil
from pathlib import Path
from datetime import datetime, UTC

import tiktoken

from config.main_config import OPEN_AI_MODEL


def extract_repo_owner_and_name_from_url(url: str) -> tuple[str, str]:
    pattern = r"https:\/\/github\.com\/([^\/]+)\/([^\/]+).*"
    matches = re.match(pattern, url)

    if not matches:
        raise ValueError(f"Invalid URL: {url}")

    try:
        return matches.group(1), matches.group(2).replace(".git", '')
    except IndexError:
        raise ValueError(f"Invalid URL: {url}")


def token_counter(text: str) -> int:
    encoding = tiktoken.encoding_for_model(OPEN_AI_MODEL)
    return len(encoding.encode(text, disallowed_special=()))


def timestamp_to_human_date(_timestamp: int) -> str:
    return datetime.fromtimestamp(_timestamp, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")