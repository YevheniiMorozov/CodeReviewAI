import shutil
from pathlib import Path
from typing import TypedDict, Optional, Literal

from config.logger import get_logger
from config.main_config import REPO_CONTENT_PATH_DIR, OPEN_AI_TOKEN_LIMITS_PER_MINUTE
from openai_worker.service import OpenAIWorker
from repo_worker.worker import GithubAPIWorker
from config import exceptions as exc
from config.factories.redis_factory import get_redis_conn_async
from config.utils import extract_repo_owner_and_name_from_url, token_counter, \
    timestamp_to_human_date
from config.openai_config import SYS_MESSAGE, USER_MESSAGE_TEMPLATE, \
    USER_MESSAGE_TEMPLATE_FOR_CHUNKS


logger = get_logger(__name__)


class GithubRateLimitResponse(TypedDict):
    limit: int
    used: int
    remaining: int
    reset: int

class OrchestratorResponse(TypedDict):
    error: bool
    message: str


class Orchestrator:

    def __init__(self,
                 repo_url: str,
                 dev_lvl: Literal["Junior", "Middle", "Senior"],
                 assignment_description: str) -> None:
        self._owner, self._repo = extract_repo_owner_and_name_from_url(repo_url)
        self._repo_url = repo_url
        self._github_rate_limit: Optional[TypedDict] = None
        self._gpt_context_window = OPEN_AI_TOKEN_LIMITS_PER_MINUTE
        self.dev_lvl = dev_lvl
        self._assignment_description = assignment_description
        self._path_to_files = REPO_CONTENT_PATH_DIR / self._owner / self._repo

    async def _download_repo_content(self) -> None:
        """Download repo content from GitHub API.
        :raises: GithubRateLimitError if not enough API rate limit
        """
        self._github_rate_limit = await GithubAPIWorker.get_api_rate_limit()
        if self._github_rate_limit['remaining'] < 1:
            raise exc.GithubRateLimitError(
                f"GitHub API rate limit exceeded: {self._github_rate_limit}"
            )

        logger.info(f"GitHub API rate limit: {self._github_rate_limit}")

        await GithubAPIWorker(repo_url=self._repo_url).upload_repo_content()

        return

    @staticmethod
    def __is_text_file(path: Path) -> bool:
        try:
            with path.open('r', encoding='utf-8') as file:
                file.read(1024)
            return True
        except UnicodeDecodeError:
            return False

    def _read_repo_content(self) -> list[str]:
        """
        Parse repo content from path.
        :return: list with files content
        """

        files = []
        for item in self._path_to_files.rglob('*'):
            # ignoring all non-text files
            if item.is_file() and self.__is_text_file(item):

                relative_path = item.relative_to(self._path_to_files)

                with item.open('r', encoding='utf-8') as file:
                    content = file.read()
                    files.append(f"File_name:{relative_path}\nContent:\n{content}")

        return files

    async def _get_gpt_answer(self, files_content: str, previous_response: str = None) -> str:

        if previous_response:
            user_message = USER_MESSAGE_TEMPLATE_FOR_CHUNKS.format(
                dev_level=self.dev_lvl,
                repo_content=files_content,
                previous_response=previous_response,
                assignment_description=self._assignment_description
            )
        else:
            user_message = USER_MESSAGE_TEMPLATE.format(
                dev_level=self.dev_lvl,
                repo_content=files_content,
                assignment_description=self._assignment_description
            )

        async with OpenAIWorker() as worker:
            answer = await worker.get_answer_from_gpt(SYS_MESSAGE, user_message)

        return answer

    async def _get_gpt_result(self) -> str:

        repo_data: list[str] = self._read_repo_content()

        sys_msg_token = token_counter(SYS_MESSAGE)
        user_msg_token = token_counter(USER_MESSAGE_TEMPLATE)

        # Count remaining tokens with small reserve
        context_window = self._gpt_context_window - sys_msg_token - user_msg_token - 10

        total_data_tokens = 0
        previous_response = None
        files_content = ""
        total_context_remaining = context_window

        for data in repo_data:
            if total_data_tokens + token_counter(data) > total_context_remaining:
                previous_response = await self._get_gpt_answer(files_content, previous_response)
                total_data_tokens = 0
                files_content = ""
                total_context_remaining = context_window - token_counter(previous_response)

            files_content += f"{data}\n\n"

            total_data_tokens += token_counter(data)

        gpt_result = await self._get_gpt_answer(files_content, previous_response)

        red = await get_redis_conn_async()
        await red.set(self._repo_url, gpt_result, ex=3600)

        return gpt_result

    async def get_cached_gpt_result(self) -> str:
        red = await get_redis_conn_async()
        gpt_result = await red.get(self._repo_url)
        return gpt_result

    def _delete_repo_content_from_dir(self) -> None:
        if self._path_to_files.exists():
            shutil.rmtree(self._path_to_files)

    async def run(self) -> OrchestratorResponse:
        try:
            await self._download_repo_content()
        except exc.GithubRateLimitError as e:
            if not self._github_rate_limit:
                self._github_rate_limit = await GithubAPIWorker.get_api_rate_limit()
            _time = timestamp_to_human_date(self._github_rate_limit['reset'])

            return OrchestratorResponse(
                error=True,
                message=f"GitHub API rate limit exceeded. Reset in {_time}\nError: {e}"
            )
        except exc.GithubNotFoundError as e:
            return OrchestratorResponse(
                error=True,
                message=f"GitHub repository not found: {e}"
            )
        except Exception as e:
            msg = f"Unexpected error occurred when downloading repo content: {e}"
            logger.error(msg, exc_info=True)
            return OrchestratorResponse(error=True, message=msg)

        try:
            gpt_result = await self._get_gpt_result()
        except exc.OpenAIError as e:
            if isinstance(e, exc.OpenAIRateLimitError):

                return OrchestratorResponse(
                    error=True,
                    message=f"OpenAI API rate limit exceeded. Try again later\nError: {e}"
                )
            return OrchestratorResponse(
                error=True,
                message=f"OpenAI API error: {e}"
            )
        except Exception as e:
            msg = f"Unexpected error occurred when getting GPT answer: {e}"
            logger.error(msg, exc_info=True)
            return OrchestratorResponse(error=True, message=msg)

        self._delete_repo_content_from_dir()

        return OrchestratorResponse(
            error=False,
            message=gpt_result)
