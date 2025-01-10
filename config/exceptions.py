class GithubAPIError(Exception):
    """Basic exception for GitHub API errors"""
    pass

class GithubRateLimitError(GithubAPIError):
    """Raised when GitHub API rate limit is exceeded"""
    pass

class GithubNotFoundError(GithubAPIError):
    """Raised when repository is not found"""
    pass


class OpenAIError(Exception):
    """Basic exception for OpenAI API errors"""
    pass

class OpenAIRateLimitError(OpenAIError):
    """Raised when OpenAI API rate limit is exceeded"""
    pass