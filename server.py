import os
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from urllib.parse import quote
import requests
from biz.service import service
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class GitLabContext:
    host: str
    token: str
    api_version: str = "v4"


def make_gitlab_api_request(ctx: Context, endpoint: str, method: str = "GET",
                            data: Optional[Dict[str, Any]] = None) -> Any:
    """Make a REST API request to GitLab and handle the response"""
    gitlab_ctx = ctx.request_context.lifespan_context

    if not gitlab_ctx.token:
        logger.error("GitLab token not set in context")
        raise ValueError("GitLab token not set. Please set GITLAB_TOKEN in your environment.")

    url = f"{gitlab_ctx.host}/api/{gitlab_ctx.api_version}/{endpoint}"
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'GitLabMCPCodeReview/1.0',
        'Private-Token': gitlab_ctx.token
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, verify=True)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, verify=True)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code == 401:
            logger.error("Authentication failed. Check your GitLab token.")
            raise Exception("Authentication failed. Please check your GitLab token.")

        response.raise_for_status()

        if not response.content:
            return {}

        try:
            return response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise Exception(f"Failed to parse GitLab response as JSON: {str(e)}")

    except requests.exceptions.RequestException as e:
        logger.error(f"REST request failed: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response status: {e.response.status_code}")
        raise Exception(f"Failed to make GitLab API request: {str(e)}")


@asynccontextmanager
async def gitlab_lifespan(server: FastMCP) -> AsyncIterator[GitLabContext]:
    """Manage GitLab connection details"""
    host = os.getenv("GITLAB_URL", "gitlab.com")
    token = os.getenv("GITLAB_ACCESS_TOKEN", "aaaa")

    if not token:
        logger.error("Missing required environment variable: GITLAB_TOKEN")
        raise ValueError(
            "Missing required environment variable: GITLAB_TOKEN. "
            "Please set this in your environment or .env file."
        )

    ctx = GitLabContext(host=host, token=token)
    try:
        yield ctx
    finally:
        pass


port = int(os.environ.get('PORT', 8001))
mcp = FastMCP(
    "GitLab MCP for Code Review",
    description="MCP server for reviewing GitLab code changes",
    lifespan=gitlab_lifespan,
    dependencies=["python-dotenv", "requests"], port=port
)


@mcp.tool()
def analysisMergeRequest(ctx: Context, project_id: str, iid: str) -> Dict[str, Any]:
    mr_endpoint = f"projects/{quote(project_id, safe='')}/merge_requests/{iid}"
    mergeInfo = make_gitlab_api_request(ctx, mr_endpoint)

    if not mergeInfo:
        raise ValueError(f"Merge request {iid} not found in project {project_id}")

    service.handle_gitlab(mergeInfo);



if __name__ == "__main__":
    try:
        logger.info(f"Starting MCP Server on port {port}...")
        logger.info("Starting GitLab Review MCP server")
        # Initialize and run the server
        mcp.run(transport='sse')
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")
        raise 