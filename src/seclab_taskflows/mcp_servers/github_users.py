# SPDX-FileCopyrightText: GitHub, Inc.
# SPDX-License-Identifier: MIT

import json
import logging
import os
import re
from urllib.parse import parse_qs, urlparse

import httpx
from fastmcp import FastMCP
from pydantic import Field
from seclab_taskflow_agent.path_utils import log_file_name

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_file_name("mcp_github_users.log"),
    filemode="a",
)

mcp = FastMCP("GitHubUsers")

GH_TOKEN = os.getenv("GH_TOKEN", default="")


def _headers() -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {GH_TOKEN}",
    }


async def _request(method: str, url: str, params: dict | None = None, payload: dict | list | None = None) -> str | httpx.Response:
    try:
        async with httpx.AsyncClient(headers=_headers()) as client:
            response = await client.request(method=method, url=url, params=params or {}, json=payload)
            response.raise_for_status()
            return response
    except httpx.RequestError as e:
        return f"Request error: {e}"
    except json.JSONDecodeError as e:
        return f"JSON error: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e}"
    except httpx.AuthenticationError as e:
        return f"Authentication error: {e}"


async def _request_all_pages(url: str, params: dict | None = None) -> str | list:
    link_pattern = re.compile(r'<([^<>]+)>;\s*rel="next"')
    merged_results = []
    current_url = url
    current_params = params or {}

    while True:
        resp = await _request("GET", current_url, params=current_params)
        if isinstance(resp, str):
            return resp

        link = resp.headers.get("link", "")
        body = resp.json()
        if not isinstance(body, list):
            return "Could not parse paginated response."

        merged_results.extend(body)
        next_link = link_pattern.search(link)
        if not next_link:
            break
        current_url = next_link.group(1)
        current_params = parse_qs(urlparse(current_url).query)

    return merged_results


def _json_response(response: httpx.Response) -> str:
    if response.status_code == 204:
        return "Success"
    if not response.content:
        return "Success"
    return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_authenticated_user() -> str:
    """Get the authenticated user."""
    resp = await _request("GET", "https://api.github.com/user")
    if isinstance(resp, str):
        return resp
    return _json_response(resp)

@mcp.tool()
async def list_users(
    since: int = Field(default=0, description="User ID to start from"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List users."""
    url = "https://api.github.com/users"
    params = {"since": since, "per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def get_user(username: str = Field(description="The handle for the GitHub user account")) -> str:
    """Get a user."""
    resp = await _request("GET", f"https://api.github.com/users/{username}")
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def get_context_for_user(
    username: str = Field(description="The handle for the GitHub user account"),
    subject_type: str = Field(default="", description="Type of subject for context (organization, repository, issue, pull_request)"),
    subject_id: str = Field(default="", description="ID of the subject used to provide context"),
) -> str:
    """Get contextual hovercard information for a user."""
    params = {}
    if subject_type:
        params["subject_type"] = subject_type
    if subject_id:
        params["subject_id"] = subject_id
    resp = await _request("GET", f"https://api.github.com/users/{username}/hovercard", params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_followers_of_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List followers of the authenticated user."""
    url = "https://api.github.com/user/followers"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_followers_for_user(
    username: str = Field(description="The handle for the GitHub user account"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List followers of a user."""
    url = f"https://api.github.com/users/{username}/followers"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_following_for_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List users followed by the authenticated user."""
    url = "https://api.github.com/user/following"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_following_for_user(
    username: str = Field(description="The handle for the GitHub user account"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List users followed by a user."""
    url = f"https://api.github.com/users/{username}/following"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def check_person_is_followed_by_authenticated_user(
    username: str = Field(description="The handle for the GitHub user account")
) -> str:
    """Check if a person is followed by the authenticated user."""
    resp = await _request("GET", f"https://api.github.com/user/following/{username}")
    if isinstance(resp, str):
        if "404" in resp:
            return "Not following"
        return resp
    return "Following"


@mcp.tool()
async def check_user_follows_another_user(
    username: str = Field(description="The handle for the source GitHub user account"),
    target_user: str = Field(description="The handle for the target GitHub user account"),
) -> str:
    """Check if one user follows another user."""
    resp = await _request("GET", f"https://api.github.com/users/{username}/following/{target_user}")
    if isinstance(resp, str):
        if "404" in resp:
            return "Does not follow"
        return resp
    return "Follows"

@mcp.tool()
async def list_gpg_keys_for_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List GPG keys for the authenticated user."""
    url = "https://api.github.com/user/gpg_keys"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)

@mcp.tool()
async def list_public_emails_for_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
) -> str:
    """List public email addresses for the authenticated user."""
    resp = await _request("GET", "https://api.github.com/user/public_emails", params={"per_page": per_page, "page": page})
    if isinstance(resp, str):
        return resp
    return _json_response(resp)

@mcp.tool()
async def list_email_addresses_for_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
) -> str:
    """List email addresses for the authenticated user."""
    resp = await _request("GET", "https://api.github.com/user/emails", params={"per_page": per_page, "page": page})
    if isinstance(resp, str):
        return resp
    return _json_response(resp)



@mcp.tool()
async def list_public_ssh_keys_for_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List public SSH keys for the authenticated user."""
    url = "https://api.github.com/user/keys"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)



@mcp.tool()
async def get_public_ssh_key_for_authenticated_user(
    key_id: int = Field(description="The unique identifier of the key"),
) -> str:
    """Get a public SSH key for the authenticated user."""
    resp = await _request("GET", f"https://api.github.com/user/keys/{key_id}")
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_social_accounts_for_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
) -> str:
    """List social accounts for the authenticated user."""
    resp = await _request("GET", "https://api.github.com/user/social_accounts", params={"per_page": per_page, "page": page})
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_social_accounts_for_user(
    username: str = Field(description="The handle for the GitHub user account"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
) -> str:
    """List social accounts for a user."""
    resp = await _request(
        "GET",
        f"https://api.github.com/users/{username}/social_accounts",
        params={"per_page": per_page, "page": page},
    )
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_ssh_signing_keys_for_authenticated_user(
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
) -> str:
    """List SSH signing keys for the authenticated user."""
    resp = await _request("GET", "https://api.github.com/user/ssh_signing_keys", params={"per_page": per_page, "page": page})
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def get_ssh_signing_key_for_authenticated_user(
    ssh_signing_key_id: int = Field(description="The unique identifier of the SSH signing key"),
) -> str:
    """Get an SSH signing key for the authenticated user."""
    resp = await _request("GET", f"https://api.github.com/user/ssh_signing_keys/{ssh_signing_key_id}")
    if isinstance(resp, str):
        return resp
    return _json_response(resp)



@mcp.tool()
async def list_gpg_keys_for_user(
    username: str = Field(description="The handle for the GitHub user account"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List GPG keys for a user."""
    url = f"https://api.github.com/users/{username}/gpg_keys"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


@mcp.tool()
async def list_public_ssh_keys_for_user(
    username: str = Field(description="The handle for the GitHub user account"),
    per_page: int = Field(default=30, description="Results per page"),
    page: int = Field(default=1, description="Page number"),
    fetch_all_pages: bool = Field(default=False, description="Whether to fetch all pages"),
) -> str:
    """List public SSH keys for a user."""
    url = f"https://api.github.com/users/{username}/keys"
    params = {"per_page": per_page, "page": page}
    if fetch_all_pages:
        resp = await _request_all_pages(url, params)
        if isinstance(resp, str):
            return resp
        return json.dumps(resp, indent=2)

    resp = await _request("GET", url, params=params)
    if isinstance(resp, str):
        return resp
    return _json_response(resp)


if __name__ == "__main__":
    mcp.run(show_banner=False)