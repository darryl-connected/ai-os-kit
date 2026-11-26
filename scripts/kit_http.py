"""Shared credential reading and non-secret HTTP diagnostics for the two connectors."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

from kit_context import KitError


def credential(root: Path, name: str) -> str:
    """A defined process value, even if blank, wins over this vault's .env."""
    value = os.environ.get(name)
    if value is None:
        try:
            value = dotenv_values(root / ".env", interpolate=False).get(name)
        except (OSError, UnicodeError):
            raise KitError("Cannot read the vault's .env file.") from None
    if not value or not value.strip():
        raise KitError(f"Missing configuration: set {name} in the process environment or the vault's .env.")
    return value.strip()


def request_json(
    service: str, method: str, url: str, headers: Mapping[str, str], *, expect_json: bool = True, **options: Any
) -> Any:
    try:
        with requests.Session() as session:
            # Avoid ambient .netrc credentials overriding the chosen API token.
            session.trust_env = False
            response = session.request(method, url, headers=headers, timeout=60, allow_redirects=False, **options)
    except requests.RequestException:
        raise KitError(f"{service} request failed. Check network access and retry when safe.") from None
    if response.status_code in (401, 403):
        raise KitError(f"{service} rejected authentication or access to this scope (HTTP {response.status_code}).")
    if not 200 <= response.status_code < 300:
        raise KitError(f"{service} request failed (HTTP {response.status_code}).")
    if not expect_json:
        return None
    try:
        return response.json()
    except (ValueError, requests.RequestException):
        raise KitError(f"{service} returned an invalid JSON response.") from None
