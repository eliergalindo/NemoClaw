---
title:
  page: "Secure Inference with Lakera Guard"
  nav: "Lakera Guard"
description: "Screen inference requests and responses for prompt injection, jailbreaks, PII leakage, and content violations."
keywords: ["nemoclaw lakera guard", "inference security prompt injection"]
topics: ["generative_ai", "ai_agents"]
tags: ["openclaw", "openshell", "inference_routing", "security", "lakera"]
content:
  type: how_to
  difficulty: intermediate
  audience: ["developer", "engineer", "security_engineer"]
status: published
---

<!--
  SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
  SPDX-License-Identifier: Apache-2.0
-->

# Secure Inference with Lakera Guard

NemoClaw can screen every inference request and response through
[Lakera Guard](https://www.lakera.ai/lakera-guard) to detect prompt injection,
jailbreaks, PII leakage, and content policy violations.

Without Lakera Guard, the sandbox enforces **network-level** security only
(deny-by-default egress, TLS termination, operator approval for unknown hosts).
Adding Lakera Guard closes the **content-level** security gap by inspecting
the actual prompt and response payloads that flow between the agent and the
inference provider.

## What Lakera Guard Detects

| Threat | Direction | Description |
|---|---|---|
| Prompt injection | Request | Adversarial input designed to override system instructions. |
| Jailbreak | Request | Attempts to bypass model safety guidelines. |
| PII leakage | Request + Response | Personal data (names, emails, credit cards) in prompts or outputs. |
| Content violations | Request + Response | Offensive, hateful, sexual, or violent content. |
| Malicious links | Response | URLs pointing to phishing, malware, or scam sites. |
| Indirect injection | Request | Injection payloads embedded in tool outputs or retrieved documents. |

## Prerequisites

- A running NemoClaw sandbox (or about to run `nemoclaw onboard`).
- A Lakera Guard API key from [platform.lakera.ai](https://platform.lakera.ai).
- Docker (required only for sidecar mode).

## Deployment Modes

Lakera Guard supports two deployment modes in NemoClaw.

### SaaS Mode (Recommended)

Requests are screened by calling the Lakera Guard cloud API at `api.lakera.ai`.
This is the simplest option and requires no additional containers.

```console
$ export LAKERA_GUARD_API_KEY="your-key-here"
$ nemoclaw onboard
```

Step 6 of the onboarding wizard detects the key and enables SaaS mode automatically.

### Sidecar Mode (Self-Hosted)

A local Lakera Guard container runs alongside the OpenShell gateway.
Use this mode to keep inference screening on-premises without routing
traffic through the Lakera cloud API. The sidecar container may still
require an API key for license validation and threat intelligence updates
depending on your Lakera subscription. Contact Lakera for fully offline
deployment options.

```console
$ export LAKERA_GUARD_API_KEY="your-key-here"
$ export LAKERA_GUARD_MODE="sidecar"
$ nemoclaw onboard
```

The onboarding wizard pulls the `lakera/lakera-guard:latest` image, starts the
container on port 8932, and waits for it to pass a health check.

## Enable on an Existing Sandbox

If you already have a running sandbox, set the environment variables and restart
the sandbox entrypoint:

```console
$ export LAKERA_GUARD_API_KEY="your-key-here"
$ export LAKERA_GUARD_MODE="saas"         # or "sidecar"
$ openshell sandbox exec my-assistant -- env \
    LAKERA_GUARD_API_KEY="$LAKERA_GUARD_API_KEY" \
    LAKERA_GUARD_MODE="$LAKERA_GUARD_MODE" \
    nemoclaw-start
```

## Configuration Reference

All Lakera Guard settings live under `components.guard` in `blueprint.yaml`.

| Field | Default | Description |
|---|---|---|
| `mode` | `saas` | `saas`, `sidecar`, or `disabled`. Overridden by `LAKERA_GUARD_MODE` env. |
| `endpoint` | `https://api.lakera.ai` | Guard API base URL. Overridden by `LAKERA_GUARD_URL` env. |
| `credential_env` | `LAKERA_GUARD_API_KEY` | Environment variable holding the API key. |
| `fail_policy` | `open` | `open` allows requests when the guard is unreachable. `closed` blocks them. |
| `screen_requests` | `true` | Screen prompts before they reach the inference provider. |
| `screen_responses` | `true` | Screen LLM responses before they reach the agent. |
| `sidecar.image` | `lakera/lakera-guard:latest` | Docker image for sidecar mode. |
| `sidecar.port` | `8932` | Host port for the sidecar container. |

### Environment Variables

| Variable | Description |
|---|---|
| `LAKERA_GUARD_API_KEY` | API key for Lakera Guard. Required for both SaaS and sidecar modes. |
| `LAKERA_GUARD_MODE` | Override the mode from `blueprint.yaml`. Values: `saas`, `sidecar`, `disabled`. |
| `LAKERA_GUARD_URL` | Override the guard API endpoint (e.g., a custom self-hosted instance). |
| `LAKERA_GUARD_PORT` | Override the sidecar container port (default: `8932`). |

## Network Policy

The baseline policy in `openclaw-sandbox.yaml` includes a `lakera_guard` entry
that allows the sandbox to reach the Lakera Guard API:

```yaml
lakera_guard:
  name: lakera_guard
  endpoints:
    - host: api.lakera.ai
      port: 443
      protocol: rest
      enforcement: enforce
      tls: terminate
      rules:
        - allow: { method: POST, path: "/v2/guard" }
        - allow: { method: GET, path: "/health" }
    - host: "127.0.0.1"
      port: 8932
      protocol: rest
      enforcement: enforce
      rules:
        - allow: { method: POST, path: "/v2/guard" }
        - allow: { method: GET, path: "/health" }
```

Only `POST /v2/guard` (screening) and `GET /health` (health check) are permitted.
No other Lakera Guard endpoints are reachable from the sandbox.

## Fail Policy

The `fail_policy` setting controls behavior when the guard is unreachable:

- **`open`** (default) — Requests pass through unscreened. A warning is logged.
  Use this for development or when guard availability is not critical.
- **`closed`** — Requests are blocked. The blueprint runner exits with an error
  if the sidecar fails to start. Use this in production when content screening
  is a hard requirement.

## How It Integrates

```
Agent → OpenShell Gateway → Lakera Guard (screen request)
                                ↓
                         Inference Provider (NVIDIA Cloud / NIM / vLLM / Ollama)
                                ↓
                         Lakera Guard (screen response) → Agent
```

Lakera Guard is invoked at two points in the inference pipeline:

1. **Pre-inference** — The full message context (system prompt + user message) is
   sent to `POST /v2/guard`. If any threat categories are flagged and the policy
   is `closed`, the request is blocked.
2. **Post-inference** — The LLM response is appended to the message context and
   screened again. Flagged responses are sanitized or rejected.

See the [Architecture Diagrams](../reference/architecture-diagrams.md#3a-inference-security-with-lakera-guard)
for detailed Mermaid diagrams of the integration.

## Verify Guard Status

Check whether Lakera Guard is active in the current sandbox:

```console
$ openclaw nemoclaw status --json
```

The output includes a `guard` section:

```json
{
  "guard": {
    "enabled": true,
    "mode": "saas",
    "endpoint": "https://api.lakera.ai",
    "fail_policy": "open"
  }
}
```

For sidecar mode, check the container health:

```console
$ docker inspect --format='{{.State.Running}}' lakera-guard
true
```

## Disable Lakera Guard

To disable screening without removing the configuration:

```console
$ export LAKERA_GUARD_MODE="disabled"
```

Or remove the `LAKERA_GUARD_API_KEY` variable entirely. The guard defaults to
`disabled` when no API key is set.

## Related Topics

- [Switch Inference Providers](switch-inference-providers.md) for changing models at runtime.
- [Inference Profiles](../reference/inference-profiles.md) for provider configuration.
- [Architecture Diagrams](../reference/architecture-diagrams.md) for visual diagrams of the guard integration.
- [Customize the Network Policy](../network-policy/customize-network-policy.md) for modifying endpoint access.
