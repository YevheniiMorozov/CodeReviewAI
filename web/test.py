from fastapi.testclient import TestClient
from web.app import app
from web.app import ReviewRequest

client = TestClient(app)

def test_review_request_model():
    review_request = ReviewRequest(repo_url="https://github.com/test/repo", dev_lvl="Junior", assignment_description="Test assignment")
    assert review_request.repo_url == "https://github.com/test/repo"
    assert review_request.dev_lvl == "Junior"
    assert review_request.assignment_description == "Test assignment"
    assert review_request.use_cache == False