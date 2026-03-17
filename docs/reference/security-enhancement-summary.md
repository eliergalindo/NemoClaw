---
title:
  page: "Lakera Guard Security Enhancement Summary"
  nav: "Security Enhancement Summary"
description: "Summary of documentation changes and how Lakera Guard enhances NemoClaw inference security."
keywords: ["nemoclaw lakera guard security summary", "inference security enhancement"]
topics: ["generative_ai", "ai_agents"]
tags: ["openclaw", "openshell", "inference_routing", "security", "lakera"]
content:
  type: reference
  difficulty: intermediate
  audience: ["developer", "engineer", "security_engineer"]
status: published
---

<!--
  SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
  SPDX-License-Identifier: Apache-2.0
-->

# Lakera Guard Security Enhancement Summary

This page summarizes all documentation and code changes introduced by the
Lakera Guard integration, and maps each change to the specific security
enhancement it provides.

## Documentation Changes

| Document | Type | Section Added / Updated | What Changed |
|---|---|---|---|
| [Secure Inference with Lakera Guard](../inference/lakera-guard.md) | **New** how-to | Full guide | Complete how-to guide covering deployment modes (SaaS / sidecar), configuration reference, network policy, fail policy, verification, and disabling. |
| [Architecture Diagrams](../reference/architecture-diagrams.md) | Updated reference | Section 3a: Inference Security with Lakera Guard | Four new Mermaid diagrams: current vs. proposed pipeline, detailed pre/post-inference screening flow, three integration options, and security coverage matrix. |
| [How It Works](../about/how-it-works.md) | Updated concept | Inference Security | New conceptual section explaining guard modes, fail policy, and how screening fits between inference routing and network policy. |
| [Inference Profiles](../reference/inference-profiles.md) | Updated reference | Inference Security with Lakera Guard | New section with deployment mode table (saas/sidecar/disabled) and pre/post-inference screening explanation. |
| [Home (index.md)](../index.md) | Updated index | Explore grid + toctree | Added "Inference Security" grid card and sidebar navigation entry linking to the Lakera Guard guide. |

## Code Changes

| File | Type | What Changed | Security Enhancement |
|---|---|---|---|
| `bin/lib/lakera.js` | **New** module | JS client — `resolveMode()`, `startSidecar()`, `stopSidecar()`, `screenRequest()`, `screenResponse()` | Provides the runtime screening API that inspects every inference request and response for threats. |
| `nemoclaw-blueprint/orchestrator/lakera.py` | **New** module | Python helper — `screen_messages()`, `screen_request()`, `screen_response()`, `guard_config_for_plan()` | Blueprint-side screening integration; extracts guard config into deployment plans for auditability. |
| `nemoclaw-blueprint/blueprint.yaml` | Updated config | Added `components.guard` section (mode, endpoint, fail_policy, sidecar settings) | Centralizes guard configuration as a first-class blueprint component. |
| `nemoclaw-blueprint/policies/openclaw-sandbox.yaml` | Updated policy | Added `lakera_guard` network policy entry | Restricts sandbox-to-guard traffic to only `POST /v2/guard` and `GET /health` — no other endpoints. |
| `scripts/nemoclaw-start.sh` | Updated entrypoint | Added `setup_lakera_guard()` function, runs before gateway startup | Ensures guard is healthy before any inference traffic flows. |
| `nemoclaw-blueprint/orchestrator/runner.py` | Updated runner | Step 4: Configure Lakera Guard; sidecar cleanup on rollback; guard state in `plan.json` | Guard lifecycle is managed alongside sandbox lifecycle (start on apply, stop on rollback). |
| `bin/lib/onboard.js` | Updated wizard | Step 6/8: Interactive Lakera Guard setup with mode selection | Users are prompted to configure guard during onboarding — security by default. |

## How Lakera Guard Enhances Security

### Security Layer Comparison

| Security Layer | Without Lakera Guard | With Lakera Guard |
|---|---|---|
| **Network egress** | Deny-by-default allow-list (endpoints, methods, paths) | Same — unchanged |
| **TLS termination** | Gateway terminates TLS, inspects HTTP metadata | Same — unchanged |
| **Filesystem isolation** | Read-only system paths, read-write only `/sandbox` and `/tmp` | Same — unchanged |
| **Process isolation** | Unprivileged `sandbox` user, Landlock LSM | Same — unchanged |
| **Prompt injection** | No detection | Pre-inference screening via `POST /v2/guard` — detects adversarial inputs designed to override system instructions |
| **Jailbreak attempts** | No detection | Pre-inference screening — detects attempts to bypass model safety guidelines |
| **PII / data leakage** | No detection | Bi-directional scanning — flags personal data (names, emails, credit cards, SSNs) in both prompts and LLM responses |
| **Harmful content** | No detection | Post-inference screening — flags offensive, hateful, sexual, or violent content in LLM output |
| **Malicious URLs** | No detection | Post-inference screening — detects phishing, malware, and scam URLs in LLM responses |
| **Indirect injection** | No detection | Pre-inference screening — detects injection payloads embedded in tool outputs, retrieval results, or MCP responses |
| **Audit trail** | Network-level logs only | Guard screening results logged per-request with threat categories and confidence scores |

### Threat Coverage Matrix

| Threat Vector | NemoClaw (Existing) | Lakera Guard (Added) | Combined Coverage |
|---|---|---|---|
| Unauthorized network access | Network allow-list blocks | — | Full |
| Credential theft via egress | TLS termination + method/path rules | PII scanner catches leaked keys in prompts | Full |
| Prompt injection (direct) | None | Prompt attack detector (98%+ accuracy, sub-50ms) | Full |
| Prompt injection (indirect) | None | Agentic/MCP screening of tool and retrieval inputs | Full |
| Jailbreak / safety bypass | None | Jailbreak detector trained on 100K+ daily attacks | Full |
| PII in prompts | None | PII scanner (names, emails, credit cards, SSNs) | Full |
| PII in responses | None | Response-side PII scanner | Full |
| Harmful content generation | None | Content violation detector (hate, violence, sexual) | Full |
| Malicious links in output | None | Malicious URL detector | Full |
| Data exfiltration via model | Filesystem isolation limits data access | PII scanner catches exfiltration attempts in prompts | Full |
| Supply chain (blueprint) | Digest verification | — | Full |

### Deployment Mode Comparison

| Aspect | SaaS Mode | Sidecar Mode | Disabled |
|---|---|---|---|
| **Endpoint** | `api.lakera.ai:443` | `localhost:8932` | — |
| **Latency overhead** | Sub-50ms (cloud round-trip) | Sub-10ms (local) | None |
| **Threat intelligence** | Continuously updated | Updated via container pulls | — |
| **Network requirement** | Outbound HTTPS to `api.lakera.ai` | None (local container) | — |
| **Setup complexity** | Set one env var | Docker container + env var | — |
| **Best for** | Most deployments | On-premises / regulated environments | Development / testing |

### Fail Policy Behavior

| Scenario | `fail_policy: open` | `fail_policy: closed` |
|---|---|---|
| Guard API unreachable | Request passes through (warning logged) | Request blocked, operator alerted |
| Sidecar fails health check | Sandbox starts, guard disabled (warning logged) | Blueprint runner exits with error |
| Screening timeout (>10s) | Request passes through (warning logged) | Request blocked |
| Guard flags a threat | Threat logged, categories returned to caller | Threat logged, request/response blocked |
| **Recommended for** | Development, non-critical workloads | Production, compliance-sensitive deployments |

## Architecture Impact

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        EXISTING SECURITY LAYERS                         │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Filesystem  │  │   Process    │  │   Network    │  │     TLS      │  │
│  │  Isolation   │  │  Isolation   │  │  Allow-list  │  │ Termination  │  │
│  │  (Landlock)  │  │  (sandbox)   │  │ (deny-all)   │  │  (gateway)   │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                                    +
┌──────────────────────────────────────────────────────────────────────────┐
│                    NEW: LAKERA GUARD CONTENT LAYER                       │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Prompt     │  │  Jailbreak   │  │     PII      │  │   Content    │  │
│  │  Injection   │  │  Detection   │  │   Scanner    │  │  Violation   │  │
│  │  Detection   │  │              │  │ (req + resp) │  │   Checker    │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐                                      │
│  │  Malicious   │  │  Indirect    │           Fail policy: open/closed   │
│  │    Link      │  │  Injection   │           Audit: per-request logs    │
│  │  Detection   │  │  (MCP/tools) │           Latency: <50ms            │
│  └─────────────┘  └──────────────┘                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

## Related Topics

- [Secure Inference with Lakera Guard](../inference/lakera-guard.md) — Full setup and configuration guide.
- [Architecture Diagrams](../reference/architecture-diagrams.md#3a-inference-security-with-lakera-guard) — Visual diagrams of the guard integration.
- [Network Policies](../reference/network-policies.md) — Baseline egress control reference.
- [How It Works](../about/how-it-works.md#inference-security) — Conceptual overview.
