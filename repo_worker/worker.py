import asyncio
from asyncio import Semaphore
from pathlib import Path
from typing import Literal

import httpx
from httpx import Response, RequestError, HTTPStatusError

from config.main_config import GITHUB_API_KEY, REPO_CONTENT_PATH_DIR, MAX_CONCURRENT_TASKS
from config.utils import extract_repo_owner_and_name_from_url
from config.exceptions import GithubNotFoundError
from config.logger import get_logger

logger = get_logger(__name__)

class GithubAPIWorker:
    def __init__(self, repo_url: str) -> None:
        self._owner, self._repo = extract_repo_owner_and_name_from_url(repo_url)
        self._path_to_save = REPO_CONTENT_PATH_DIR / self._owner / self._repo
        self._path_to_save.mkdir(parents=True, exist_ok=True)
        self._api_root_url = f"https://api.github.com/repos/{self._owner}/{self._repo}/contents/"
        self._semaphore = Semaphore(MAX_CONCURRENT_TASKS)


    @staticmethod
    def _get_api_headers() -> dict:
        return {"Authorization": f"token {GITHUB_API_KEY}"}

    @staticmethod
    def _get_api_rate_limit_headers() -> dict:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {GITHUB_API_KEY}",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    @staticmethod
    async def _make_request(client: httpx.AsyncClient,
                            url: str,
                            headers: dict,
                            method: Literal['GET', 'POST'] = 'GET') -> Response:

        attempt = 0
        retries = 5

        while attempt < retries:
            try:
                response = await client.request(method, url, headers=headers)
                response.raise_for_status()
                return response
            except RequestError as e:
                attempt += 1
                if attempt < retries:
                    logger.error(f"Request failed: {e}, attempt: {attempt + 1}")
                    await asyncio.sleep(2)
                    continue
                logger.error(f"Request failed: {e}", exc_info=True)
                raise
            except HTTPStatusError as e:
                logger.error(e, exc_info=True)
                raise GithubNotFoundError(f"Repo not found: {url}")

    @classmethod
    async def get_api_rate_limit(cls) -> dict:
        url = "https://api.github.com/rate_limit"
        headers = cls._get_api_rate_limit_headers()

        async with httpx.AsyncClient(timeout=10) as client:
            response = await cls._make_request(client, url, headers)
            try:
                return response.json()["rate"]
            except ValueError:
                error_message = "Failed to get rate limit information from GitHub API, "\
                                f"response: {response.text}"
                return {"error": error_message}

    async def upload_repo_content(self,
                                  repo_api_url: str = None,
                                  dir_name: Path = None,
                                  deeper: bool = False,
                                  path_to_save: Path = None) -> bool:
        """Download repo content from using GitHub API
        :param repo_api_url: parameter is used for recursive downloading
        :param dir_name: directory name, where files will be downloaded
        :param deeper: this parameter is used for recursive downloading, if repo has subdirectories
        :param path_to_save: parameter is used for recursive downloading
        """

        if deeper:
            path_to_save = path_to_save / dir_name if path_to_save else self._path_to_save / dir_name
            logger.debug(f"Uploading directory: {dir_name} to {path_to_save}")
            path_to_save.mkdir(parents=True, exist_ok=True)

        else:
            logger.info(f"Uploading repo: {self._repo}")
            path_to_save = self._path_to_save
            repo_api_url = self._api_root_url

        if not repo_api_url:
            raise ValueError("Invalid repo url")

        headers = self._get_api_headers()

        async with self._semaphore:
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    response = await self._make_request(client, repo_api_url, headers)
                    items = response.json()

                    tasks = []
                    for item in items:
                        logger.debug(f"{item['type'].capitalize()}: {item['name']}")
                        if item["type"] == "file":
                            # Download the file
                            task = self._download_file(client, item, path_to_save, headers)
                            tasks.append(task)
                        elif item["type"] == "dir":
                            # Recurse into subdirectories
                            task = self.upload_repo_content(
                                item["url"],
                                deeper=True,
                                dir_name=item["name"],
                                path_to_save=path_to_save
                            )
                            tasks.append(task)

                    await asyncio.gather(*tasks)

                    logger.info("Finished uploading repo")

                    return True
                except Exception as e:
                    logger.error(f"Failed to upload repo: {e}", exc_info=True)
                    return False

    async def _download_file(self,
                             client: httpx.AsyncClient,
                             item: dict,
                             path_to_save: Path,
                             headers: dict):
        """Download a single file."""
        try:
            file_response = await self._make_request(client, item["download_url"], headers)
            content = file_response.content
            with open(path_to_save / item["name"], "wb") as file:
                file.write(content)
            logger.debug(f"Downloaded: {item['name']}")
        except Exception as e:
            logger.error(f"Failed to download file {item['name']}: {e}", exc_info=True)


if __name__ == '__main__':

    worker = GithubAPIWorker("https://github.com/openai/tiktoken.git")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker.upload_repo_content())
    rate_limit = loop.run_until_complete(GithubAPIWorker.get_api_rate_limit())
    print(rate_limit)
