import pytest
from unittest.mock import AsyncMock, patch

from orchestrator.orchestrator import Orchestrator, OrchestratorResponse
from config import exceptions as exc


@pytest.mark.asyncio
@patch("orchestrator.orchestrator.OpenAIWorker.get_answer_from_gpt")
@patch("orchestrator.orchestrator.GithubAPIWorker.get_api_rate_limit")
@patch("orchestrator.orchestrator.GithubAPIWorker.upload_repo_content")
@patch("orchestrator.orchestrator.get_redis_conn_async")
async def test_orchestrator_run_success(mock_redis_conn, mock_upload_repo_content,
                                        mock_get_api_rate_limit, mock_get_answer_from_gpt):
    # Mock GitHub API rate limit
    mock_get_api_rate_limit.return_value = {"limit": 5000, "used": 1000, "remaining": 4000, "reset": 1234567890}

    # Mock GPT response
    mock_get_answer_from_gpt.return_value = "Mock GPT Response"

    # Mock Redis
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set = AsyncMock()
    mock_redis_conn.return_value = mock_redis

    orchestrator = Orchestrator(
        repo_url="https://github.com/test/repo",
        dev_lvl="Junior",
        assignment_description="Test assignment"
    )

    response = await orchestrator.run()

    # Assertions
    assert response == OrchestratorResponse(error=False, message="Mock GPT Response")
    mock_get_api_rate_limit.assert_called_once()
    mock_upload_repo_content.assert_called_once()
    mock_get_answer_from_gpt.assert_called()
    mock_redis.set.assert_called_once_with("https://github.com/test/repo", "Mock GPT Response", ex=3600)


@pytest.mark.asyncio
@patch("orchestrator.orchestrator.GithubAPIWorker.get_api_rate_limit")
@patch("orchestrator.orchestrator.GithubAPIWorker.upload_repo_content")
async def test_orchestrator_run_github_rate_limit_error(mock_upload_repo_content, mock_get_api_rate_limit):
    # Mock GitHub API rate limit exceeded
    mock_get_api_rate_limit.return_value = {"limit": 5000, "used": 5000, "remaining": 0, "reset": 1234567890}

    orchestrator = Orchestrator(
        repo_url="https://github.com/test/repo",
        dev_lvl="Junior",
        assignment_description="Test assignment"
    )

    response = await orchestrator.run()

    assert response["error"] is True
    assert "GitHub API rate limit exceeded" in response["message"]
    mock_get_api_rate_limit.assert_called_once()
    mock_upload_repo_content.assert_not_called()


@pytest.mark.asyncio
@patch("orchestrator.orchestrator.OpenAIWorker.get_answer_from_gpt")
@patch("orchestrator.orchestrator.GithubAPIWorker.get_api_rate_limit")
@patch("orchestrator.orchestrator.GithubAPIWorker.upload_repo_content")
@patch("orchestrator.orchestrator.get_redis_conn_async")
async def test_orchestrator_run_openai_error(mock_redis_conn, mock_upload_repo_content,
                                             mock_get_api_rate_limit, mock_get_answer_from_gpt):
    # Mock GitHub API rate limit
    mock_get_api_rate_limit.return_value = {"limit": 5000, "used": 1000, "remaining": 4000, "reset": 1234567890}

    # Simulate OpenAI error
    mock_get_answer_from_gpt.side_effect = exc.OpenAIRateLimitError("Rate limit exceeded")

    orchestrator = Orchestrator(
        repo_url="https://github.com/test/repo",
        dev_lvl="Junior",
        assignment_description="Test assignment"
    )

    response = await orchestrator.run()

    assert response["error"] is True
    assert "OpenAI API rate limit exceeded" in response["message"]
    mock_get_api_rate_limit.assert_called_once()
    mock_upload_repo_content.assert_called_once()
    mock_get_answer_from_gpt.assert_called()


@pytest.mark.asyncio
@patch("orchestrator.orchestrator.GithubAPIWorker.upload_repo_content")
@patch("orchestrator.orchestrator.OpenAIWorker.get_answer_from_gpt")
@patch("orchestrator.orchestrator.get_redis_conn_async")
async def test_orchestrator_with_cached_gpt_result(mock_redis_conn, mock_get_answer_from_gpt, mock_upload_repo_content):
    # Mock Redis with cached result
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "Cached GPT Response"
    mock_redis_conn.return_value = mock_redis

    orchestrator = Orchestrator(
        repo_url="https://github.com/test/repo",
        dev_lvl="Junior",
        assignment_description="Test assignment"
    )

    gpt_result = await orchestrator.get_cached_gpt_result()

    assert gpt_result == "Cached GPT Response"
    mock_redis.get.assert_called_once_with("https://github.com/test/repo")
    mock_get_answer_from_gpt.assert_not_called()
    mock_upload_repo_content.assert_not_called()
