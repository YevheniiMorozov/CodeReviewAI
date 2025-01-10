import asyncio

from openai import AsyncClient, RateLimitError
from openai.types.chat import ChatCompletion

from config.main_config import OPEN_AI_API_KEY, OPEN_AI_MODEL
from config.exceptions import OpenAIRateLimitError, OpenAIError
from config.logger import get_logger

logger = get_logger(__name__)

class OpenAIWorker:
    def __init__(self) -> None:

        self._retries = 10
        self._timeout = 10

    def __enter__(self):
        try:
            logger.debug("Initializing OpenAI client")
            self._client = AsyncClient(
                api_key=OPEN_AI_API_KEY
            )
            self._open_ai_model = OPEN_AI_MODEL
            return self
        except Exception as e:
            logger.error(f"OpenAI client initialization failed: {e}", exc_info=True)
            raise OpenAIError(e)

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._client.close()
            logger.debug("OpenAI client closed")
        except Exception as e:
            logger.error(f"OpenAI client close failed: {e}", exc_info=True)
            raise OpenAIError(e)


    async def _get_completion(self, model: str, messages: list[dict]) -> ChatCompletion:

        attempt = 0
        while attempt < self._retries:
            try:
                completion = await self._client.chat.completions.create(model=model, messages=messages)

                return completion
            except RateLimitError as e:
                attempt += 1
                if attempt < self._retries:
                    logger.error(f"Request failed: {e}, attempt: {attempt + 1}")
                    await asyncio.sleep(self._timeout)
                    continue
                logger.error(f"Request failed: {e}", exc_info=True)
                raise OpenAIRateLimitError(e)
            except Exception as e:
                logger.error(f"Request failed: {e}", exc_info=True)
                raise OpenAIError(e)


    async def get_answer_from_gpt(self, user_message: str, sys_message: str) -> str:
        logger.info(f"Asks GPT: {user_message}")

        messages = [
            {"role": "system", "content": sys_message},
            {"role": "user", "content": user_message},
        ]

        completion = await self._get_completion(self._open_ai_model, messages)

        answer = completion.choices[0].message.content

        logger.info(f"Got answer: {answer}")

        return answer
