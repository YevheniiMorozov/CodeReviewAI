import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openai_worker.service import OpenAIWorker


@pytest.fixture
def mocked_client():
    """Fixture to mock the OpenAI AsyncClient."""
    with patch("openai_worker.service.AsyncClient", autospec=True) as mock_client:
        mock_chat = AsyncMock()
        mock_client.return_value.chat = mock_chat
        yield mock_client


# Test case for OpenAIWorker
@pytest.mark.asyncio
async def test_openai_worker(mocked_client):
    """Test the OpenAIWorker behavior."""

    mocked_client_instance = mocked_client.return_value

    mocked_client_instance.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="This is GPT's response"))]
    ))

    mocked_client_instance.close = AsyncMock()

    async with OpenAIWorker() as worker:
        response = await worker.get_answer_from_gpt(
            user_message="Hello, GPT!",
            sys_message="You are a helpful assistant."
        )

    mocked_client_instance.close.assert_called_once()

    assert response == "This is GPT's response"
