import pytest
import httpx
from unittest.mock import AsyncMock, patch
from pathlib import Path
from config.exceptions import GithubNotFoundError
from repo_worker.worker import GithubAPIWorker

# Mock configuration values
REPO_URL = "https://github.com/owner/repo"
API_KEY = "mock_api_key"
MAX_CONCURRENT_TASKS = 10


@pytest.fixture
def mock_github_api_worker():
    # Create an instance of GithubAPIWorker with a mock repository URL
    return GithubAPIWorker(REPO_URL)


@pytest.fixture
def mock_response_limit():
    # Create a mock response object
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.json.return_value = {"rate": {"limit": 5000, "remaining": 4999}}
    mock_resp.raise_for_status = AsyncMock()
    return mock_resp


@pytest.fixture
def moke_response_repo_result():
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.json.return_value = [
        {"type": "file", "name": "file1.txt", "download_url": "http://example.com/file1.txt"},
        {"type": "dir", "name": "subdir", "url": "http://example.com/subdir"}
    ]
    mock_resp.raise_for_status = AsyncMock()
    return mock_resp


@pytest.mark.asyncio
async def test_get_api_rate_limit(mock_github_api_worker, mock_response_limit):
    # Patch the _make_request method to return the mocked response
    with patch.object(GithubAPIWorker, "_make_request", return_value=mock_response_limit):
        rate_limit = await mock_github_api_worker.get_api_rate_limit()

        assert rate_limit == {"limit": 5000, "remaining": 4999}


@pytest.mark.asyncio
async def test_get_api_rate_limit_handle_error(mock_github_api_worker):
    # Mock a response that will raise ValueError when calling .json()
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.json.side_effect = ValueError("Invalid JSON response")
    mock_resp.raise_for_status = AsyncMock()

    # Patch _make_request to return the mocked response
    with patch.object(GithubAPIWorker, "_make_request", return_value=mock_resp):
        result = await mock_github_api_worker.get_api_rate_limit()
        assert "error" in result


@pytest.mark.asyncio
async def test_upload_repo_content_invalid_url(mock_github_api_worker):
    # Test invalid repo URL scenario
    with pytest.raises(ValueError):
        await mock_github_api_worker.upload_repo_content(repo_api_url=None, deeper=True,
                                                         dir_name='dir')
