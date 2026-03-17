---
title:
  page: "NemoClaw Inference Profiles — NVIDIA Cloud"
  nav: "Inference Profiles"
description: "Configuration reference for NVIDIA cloud inference profiles."
keywords: ["nemoclaw inference profiles", "nemoclaw nvidia cloud provider"]
topics: ["generative_ai", "ai_agents"]
tags: ["openclaw", "openshell", "inference_routing", "llms"]
content:
  type: reference
  difficulty: intermediate
  audience: ["developer", "engineer"]
status: published
---

<!--
  SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
  SPDX-License-Identifier: Apache-2.0
-->

# Inference Profiles

NemoClaw ships with an inference profile defined in `blueprint.yaml`.
The profile configures an OpenShell inference provider and model route.
The agent inside the sandbox uses whichever model is active.
Inference requests are routed transparently through the OpenShell gateway.

## Profile Summary

| Profile | Provider | Model | Endpoint | Use Case |
|---|---|---|---|---|
| `default` | NVIDIA cloud | `nvidia/nemotron-3-super-120b-a12b` | `integrate.api.nvidia.com` | Production. Requires an NVIDIA API key. |

## Available Models

The `nvidia-nim` provider registers the following models from [build.nvidia.com](https://build.nvidia.com):

| Model ID | Label | Context Window | Max Output |
|---|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b` | Nemotron 3 Super 120B | 131,072 | 8,192 |
| `nvidia/llama-3.1-nemotron-ultra-253b-v1` | Nemotron Ultra 253B | 131,072 | 4,096 |
| `nvidia/llama-3.3-nemotron-super-49b-v1.5` | Nemotron Super 49B v1.5 | 131,072 | 4,096 |
| `nvidia/nemotron-3-nano-30b-a3b` | Nemotron 3 Nano 30B | 131,072 | 4,096 |

The default profile uses Nemotron 3 Super 120B.
You can switch to any model in the catalog at runtime.

## `default` -- NVIDIA Cloud

The default profile routes inference to NVIDIA's hosted API through [build.nvidia.com](https://build.nvidia.com).

- **Provider type:** `nvidia`
- **Endpoint:** `https://integrate.api.nvidia.com/v1`
- **Model:** `nvidia/nemotron-3-super-120b-a12b`
- **Credential:** `NVIDIA_API_KEY` environment variable

Get an API key from [build.nvidia.com](https://build.nvidia.com).
The `nemoclaw onboard` command prompts for this key and stores it in `~/.nemoclaw/credentials.json`.

```console
$ openshell inference set --provider nvidia-nim --model nvidia/nemotron-3-super-120b-a12b
```

## Switching Models at Runtime

After the sandbox is running, switch models with the OpenShell CLI:

```console
$ openshell inference set --provider nvidia-nim --model <model-name>
```

The change takes effect immediately.
No sandbox restart is needed.

## Inference Security with Lakera Guard

NemoClaw can screen inference requests and responses through Lakera Guard
to detect prompt injection, jailbreaks, PII leakage, and content violations.

Lakera Guard is configured in the `components.guard` section of `blueprint.yaml`
and supports two deployment modes:

| Mode | Endpoint | Use Case |
|---|---|---|
| `saas` | `api.lakera.ai` | Cloud screening. Requires `LAKERA_GUARD_API_KEY`. |
| `sidecar` | `localhost:8932` | Local container. For air-gapped environments. |
| `disabled` | — | No content screening (default when no API key is set). |

The guard is invoked at two points in the inference pipeline:

1. **Pre-inference** — Screens the full message context before it reaches the provider.
2. **Post-inference** — Screens the LLM response before it reaches the agent.

A `fail_policy` setting controls behavior when the guard is unreachable:
`open` (default) allows requests through; `closed` blocks them.

See [Secure Inference with Lakera Guard](../inference/lakera-guard.md) for setup instructions and configuration reference.
