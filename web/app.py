from typing import Literal

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from orchestrator.orchestrator import Orchestrator, OrchestratorResponse

app = FastAPI()


class ReviewRequest(BaseModel):
    repo_url: str
    dev_lvl: Literal["Junior", "Middle", "Senior"]
    assignment_description: str
    use_cache: bool = False


class ReviewResponse(BaseModel):
    message: str
    error: bool


@app.post(
    "/review",
    summary="Process a Repository Review",
    description=(
            "This endpoint accepts a repository URL, developer level, assignment description, "
            "and an optional cache flag to fetch cached results from redis (if it exists) "
            "or run a detailed review. If repo contains a big file or a large number of files, "
            "it may take a long time to process it. For caching application use repo_url as a key, "
            "so if you want to change request parameters, use_cache=False should be set. "
            "Cache will automatically be cleared after 1 hour."
    ),
)
async def review_repo(request: ReviewRequest = Depends()):
    o = Orchestrator(
        repo_url=request.repo_url,
        dev_lvl=request.dev_lvl,
        assignment_description=request.assignment_description
    )

    if request.use_cache:
        result: str = await o.get_cached_gpt_result()
        if result:
            return JSONResponse(
                content=jsonable_encoder(ReviewResponse(message=result, error=False))
            )

    result: OrchestratorResponse = await o.run()

    return JSONResponse(
        content=jsonable_encoder(ReviewResponse(message=result['message'], error=result['error']))
    )
