#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Lakera Guard integration for the NemoClaw blueprint runner.

Screens inference requests and responses for prompt injection, jailbreaks,
PII leakage, and content violations via the Lakera Guard API.

Modes:
  saas     — calls api.lakera.ai (requires LAKERA_GUARD_API_KEY env)
  sidecar  — local container on localhost:8932
  disabled — no screening (default when no key is set)

Env:
  LAKERA_GUARD_API_KEY   API key for Lakera Guard SaaS
  LAKERA_GUARD_URL       Override guard endpoint
  LAKERA_GUARD_MODE      "saas" | "sidecar" | "disabled"
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

LAKERA_SIDECAR_IMAGE = "lakera/lakera-guard:latest"
LAKERA_SIDECAR_PORT = 8932


@dataclass
class ScreenResult:
    """Result from a Lakera Guard screening call."""

    flagged: bool = False
    categories: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def resolve_mode() -> str:
    """Determine the guard mode from environment."""
    explicit = os.environ.get("LAKERA_GUARD_MODE", "")
    if explicit:
        return explicit
    if os.environ.get("LAKERA_GUARD_API_KEY"):
        return "saas"
    return "disabled"


def guard_base_url() -> str:
    """Return the Lakera Guard API base URL."""
    override = os.environ.get("LAKERA_GUARD_URL", "")
    if override:
        return override.rstrip("/")
    mode = resolve_mode()
    if mode == "sidecar":
        return f"http://127.0.0.1:{LAKERA_SIDECAR_PORT}"
    return "https://api.lakera.ai"


def start_sidecar() -> dict[str, Any]:
    """Start the Lakera Guard sidecar Docker container."""
    name = "lakera-guard"
    subprocess.run(
        ["docker", "rm", "-f", name],
        capture_output=True,
        check=False,
    )

    api_key = os.environ.get("LAKERA_GUARD_API_KEY", "")
    cmd = [
        "docker", "run", "-d",
        "--name", name,
        "--restart", "unless-stopped",
        "-p", f"{LAKERA_SIDECAR_PORT}:8000",
    ]
    if api_key:
        cmd.extend(["-e", f"LAKERA_GUARD_API_KEY={api_key}"])
    cmd.append(LAKERA_SIDECAR_IMAGE)

    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Wait for health
    for _ in range(15):
        try:
            result = subprocess.run(
                ["curl", "-sf", f"http://127.0.0.1:{LAKERA_SIDECAR_PORT}/health"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and "ok" in result.stdout.lower():
                return {"ok": True, "port": LAKERA_SIDECAR_PORT}
        except Exception:
            pass
        time.sleep(2)

    return {"ok": False, "port": LAKERA_SIDECAR_PORT}


def stop_sidecar() -> None:
    """Stop and remove the sidecar container."""
    subprocess.run(
        ["docker", "rm", "-f", "lakera-guard"],
        capture_output=True,
        check=False,
    )


def screen_messages(messages: list[dict[str, str]]) -> ScreenResult:
    """
    Screen a list of chat messages via Lakera Guard.

    Args:
        messages: List of {role, content} dicts (OpenAI chat format).

    Returns:
        ScreenResult with flagged status, categories, and raw API response.
    """
    mode = resolve_mode()
    if mode == "disabled":
        return ScreenResult()

    base_url = guard_base_url()
    api_key = os.environ.get("LAKERA_GUARD_API_KEY", "")

    payload = json.dumps({"messages": messages})

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name

    try:
        curl_cmd = [
            "curl", "-sf", "-X", "POST",
            f"{base_url}/v2/guard",
            "-H", "Content-Type: application/json",
        ]
        if api_key:
            curl_cmd.extend(["-H", f"Authorization: Bearer {api_key}"])
        curl_cmd.extend(["-d", f"@{tmp_path}"])

        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        if result.returncode != 0 or not result.stdout.strip():
            logger.warning("Lakera Guard unavailable — failing open")
            return ScreenResult(raw={"error": "guard_unavailable"})

        parsed = json.loads(result.stdout)
        categories = [
            c.get("category", c) if isinstance(c, dict) else c
            for c in parsed.get("flagged_categories", [])
        ]
        return ScreenResult(
            flagged=len(categories) > 0,
            categories=categories,
            raw=parsed,
        )
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        logger.warning("Lakera Guard error — failing open: %s", exc)
        return ScreenResult(raw={"error": str(exc)})
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def screen_request(
    system_prompt: str,
    user_message: str,
) -> ScreenResult:
    """Screen a pre-inference request (system prompt + user message)."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    return screen_messages(messages)


def screen_response(
    response_text: str,
    context: list[dict[str, str]] | None = None,
) -> ScreenResult:
    """Screen a post-inference response."""
    messages = list(context or [])
    messages.append({"role": "assistant", "content": response_text})
    return screen_messages(messages)


def guard_config_for_plan(blueprint: dict[str, Any]) -> dict[str, Any]:
    """
    Extract Lakera Guard configuration from the blueprint for inclusion
    in a deployment plan.
    """
    guard_cfg = (
        blueprint.get("components", {}).get("guard", {})
    )
    mode = resolve_mode()
    return {
        "enabled": mode != "disabled",
        "mode": mode,
        "endpoint": guard_base_url() if mode != "disabled" else None,
        "fail_policy": guard_cfg.get("fail_policy", "open"),
        "screen_requests": guard_cfg.get("screen_requests", True),
        "screen_responses": guard_cfg.get("screen_responses", True),
    }
