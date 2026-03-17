---
title:
  page: "NemoClaw Architecture Diagrams"
  nav: "Architecture Diagrams"
description: "Visual diagrams of NemoClaw's architecture, data flow, deployment options, and onboarding lifecycle."
keywords: ["nemoclaw architecture diagram", "nemoclaw data flow"]
topics: ["generative_ai", "ai_agents"]
tags: ["openclaw", "openshell", "sandboxing", "blueprints", "inference_routing"]
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

# Architecture Diagrams

## 1. High-Level System Architecture

```{mermaid}
flowchart TB
    USER([Developer / Operator])

    subgraph HOST ["HOST MACHINE"]
        direction TB
        CLI["nemoclaw CLI<br/>(bin/nemoclaw.js)"]
        ONBOARD["Onboard Wizard<br/>(bin/lib/onboard.js)"]
        REGISTRY["Sandbox Registry<br/>(~/.nemoclaw/sandboxes.json)"]
        CREDS["Credential Store<br/>(~/.nemoclaw/credentials.json)"]

        subgraph PLUGIN ["NEMOCLAW PLUGIN (TypeScript)"]
            direction LR
            RESOLVE["resolve.ts<br/>Version + Cache"]
            FETCH["fetch.ts<br/>OCI Download"]
            VERIFY["verify.ts<br/>Digest Check"]
            EXEC["exec.ts<br/>Subprocess"]
        end

        subgraph BLUEPRINT ["NEMOCLAW BLUEPRINT (Python)"]
            direction LR
            RUNNER["runner.py<br/>plan / apply /<br/>status / rollback"]
            POLICIES["policies/<br/>openclaw-sandbox.yaml<br/>+ presets/"]
        end

        OPENSHELL_CLI["OpenShell CLI<br/>sandbox · gateway ·<br/>inference · policy"]
    end

    subgraph SANDBOX ["OPENSHELL SANDBOX (Docker Container)"]
        direction TB
        AGENT["OpenClaw Agent"]
        GATEWAY["OpenShell Gateway<br/>(nemoclaw-start.sh)"]
        WORKSPACE["/sandbox (read-write)<br/>/tmp (read-write)<br/>system paths (read-only)"]
        NET_POLICY["Network Policy<br/>(deny-by-default)"]
    end

    subgraph INFERENCE ["INFERENCE PROVIDERS"]
        direction TB
        NVIDIA_CLOUD["NVIDIA Cloud<br/>integrate.api.nvidia.com"]
        OLLAMA["Ollama (local)<br/>localhost:11434"]
        VLLM["vLLM (local)<br/>localhost:8000"]
        NIM["NIM Container (local)<br/>nim-service.local:8000"]
    end

    USER --> CLI
    CLI --> ONBOARD
    CLI --> REGISTRY
    CLI --> CREDS
    ONBOARD --> PLUGIN
    RESOLVE --> FETCH --> VERIFY --> EXEC
    EXEC --> RUNNER
    RUNNER --> POLICIES
    RUNNER --> OPENSHELL_CLI
    OPENSHELL_CLI --> SANDBOX
    AGENT --> GATEWAY
    GATEWAY --> NET_POLICY
    GATEWAY --> INFERENCE

    classDef nv fill:#76b900,stroke:#333,color:#fff
    classDef nvDark fill:#333,stroke:#76b900,color:#fff
    classDef nvLight fill:#e6f2cc,stroke:#76b900,color:#1a1a1a
    classDef user fill:#4a90d9,stroke:#333,color:#fff

    class USER user
    class CLI,ONBOARD nvDark
    class RESOLVE,FETCH,VERIFY,EXEC nvDark
    class RUNNER,POLICIES nvDark
    class OPENSHELL_CLI nv
    class AGENT,GATEWAY nv
    class WORKSPACE,NET_POLICY nvLight
    class NVIDIA_CLOUD,OLLAMA,VLLM,NIM nvLight

    style HOST fill:none,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style SANDBOX fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style PLUGIN fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
    style BLUEPRINT fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
    style INFERENCE fill:none,stroke:#999,stroke-width:1px,color:#1a1a1a
```

## 2. Onboarding Flow (7 Steps)

```{mermaid}
flowchart TD
    START([nemoclaw onboard]) --> S1

    S1["Step 1: PREFLIGHT<br/>Docker check · OpenShell CLI ·<br/>cgroup v2 · GPU detection"]
    S1 -->|pass| S2
    S1 -->|fail| ERR1([Fix prerequisites])

    S2["Step 2: GATEWAY<br/>Start OpenShell gateway<br/>(optional GPU passthrough)"]
    S2 --> S3

    S3["Step 3: SANDBOX<br/>openshell sandbox create<br/>--from Dockerfile<br/>--policy openclaw-sandbox.yaml"]
    S3 --> S4

    S4{"Step 4: NIM SETUP<br/>GPU detected?"}
    S4 -->|yes| S4A["Local NIM container<br/>(120GB+ VRAM)"]
    S4 -->|no| S4B["Cloud inference<br/>(NVIDIA API key)"]
    S4A --> S5
    S4B --> S5

    S5["Step 5: INFERENCE PROVIDER<br/>Configure OpenShell<br/>provider routing"]
    S5 --> S6

    S6["Step 6: OPENCLAW<br/>Validate installation<br/>inside sandbox"]
    S6 --> S7

    S7["Step 7: POLICIES<br/>Apply baseline +<br/>dynamic presets<br/>(Telegram, Slack, etc.)"]
    S7 --> DONE([Sandbox ready])

    classDef step fill:#333,stroke:#76b900,color:#fff
    classDef decision fill:#76b900,stroke:#333,color:#fff
    classDef endpoint fill:#4a90d9,stroke:#333,color:#fff
    classDef error fill:#d94a4a,stroke:#333,color:#fff

    class S1,S2,S3,S5,S6,S7,S4A,S4B step
    class S4 decision
    class START,DONE endpoint
    class ERR1 error
```

## 3. Inference Routing & Network Policy

```{mermaid}
flowchart LR
    subgraph SANDBOX ["Sandbox (isolated container)"]
        AGENT["OpenClaw<br/>Agent"]
    end

    subgraph GATEWAY ["OpenShell Gateway"]
        INTERCEPT["Intercept<br/>all requests"]
        POLICY_CHECK{"Network<br/>policy<br/>check"}
    end

    subgraph ALLOWED ["Allowed Endpoints"]
        NV["NVIDIA Cloud<br/>integrate.api.nvidia.com"]
        GH["GitHub<br/>github.com<br/>api.github.com"]
        NPM["npm Registry<br/>registry.npmjs.org"]
        TELE["Telegram*<br/>api.telegram.org"]
        OTHER["Other presets*<br/>Slack · Discord ·<br/>Jira · PyPI · HF"]
    end

    BLOCKED([Blocked & surfaced<br/>in TUI for approval])

    AGENT -->|"all egress"| INTERCEPT
    INTERCEPT --> POLICY_CHECK
    POLICY_CHECK -->|"in allow-list"| ALLOWED
    POLICY_CHECK -->|"not in allow-list"| BLOCKED

    classDef nv fill:#76b900,stroke:#333,color:#fff
    classDef nvLight fill:#e6f2cc,stroke:#76b900,color:#1a1a1a
    classDef blocked fill:#d94a4a,stroke:#333,color:#fff

    class AGENT nv
    class INTERCEPT,POLICY_CHECK nv
    class NV,GH,NPM,TELE,OTHER nvLight
    class BLOCKED blocked

    style SANDBOX fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style GATEWAY fill:none,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style ALLOWED fill:none,stroke:#999,stroke-width:1px,color:#1a1a1a
```

_* Presets are optional and applied via `nemoclaw <name> policy-add`._

## 4. Blueprint Lifecycle

```{mermaid}
flowchart LR
    R["RESOLVE<br/>Locate artifact,<br/>check version<br/>constraints"]
    V["VERIFY<br/>Check digest<br/>against expected<br/>value"]
    P["PLAN<br/>Determine resources:<br/>gateway · providers ·<br/>sandbox · policy"]
    A["APPLY<br/>Execute plan via<br/>openshell CLI<br/>commands"]
    S["STATUS<br/>Report current<br/>run state from<br/>~/.nemoclaw/state/"]
    RB["ROLLBACK<br/>Stop sandbox,<br/>remove resources,<br/>clean state"]

    R --> V --> P --> A --> S
    A -.->|"on failure"| RB

    classDef step fill:#333,stroke:#76b900,color:#fff
    classDef rollback fill:#d94a4a,stroke:#333,color:#fff

    class R,V,P,A,S step
    class RB rollback
```

## 5. Deployment Options

```{mermaid}
flowchart TB
    subgraph LOCAL ["Option A: Local Deployment"]
        direction TB
        L1["curl -fsSL<br/>nvidia.com/nemoclaw.sh | bash"]
        L2["Installs Node.js 22,<br/>Ollama (if GPU), NemoClaw"]
        L3["nemoclaw onboard"]
        L4["Sandbox runs locally<br/>via Docker"]
        L1 --> L2 --> L3 --> L4
    end

    subgraph REMOTE ["Option B: Remote GPU (Brev)"]
        direction TB
        R1["nemoclaw deploy <instance>"]
        R2["Provisions GPU VM<br/>via Brev CLI"]
        R3["rsync code + .env<br/>to remote"]
        R4["Runs setup +<br/>starts services"]
        R1 --> R2 --> R3 --> R4
    end

    subgraph SPARK ["Option C: DGX Spark"]
        direction TB
        K1["nemoclaw setup-spark"]
        K2["Fixes cgroup v2 +<br/>Docker cgroupns"]
        K3["nemoclaw onboard"]
        K4["Sandbox runs on<br/>DGX Spark hardware"]
        K1 --> K2 --> K3 --> K4
    end

    classDef step fill:#333,stroke:#76b900,color:#fff
    class L1,L2,L3,L4,R1,R2,R3,R4,K1,K2,K3,K4 step

    style LOCAL fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style REMOTE fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style SPARK fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
```

## 6. Sandbox Container Internals

```{mermaid}
flowchart TB
    subgraph CONTAINER ["Docker Container (node:22-slim)"]
        direction TB

        subgraph RUNTIME ["Runtime"]
            USER_SANDBOX["sandbox user<br/>(unprivileged)"]
            NODEJS["Node.js 22"]
            PYTHON["Python 3"]
            OPENCLAW_CLI["OpenClaw CLI v2026.3.11"]
            NEMOCLAW_PLUGIN["NemoClaw Plugin<br/>(dist/)"]
            BLUEPRINT_RUNNER["Blueprint Runner<br/>(orchestrator/runner.py)"]
        end

        subgraph FS ["Filesystem Access"]
            RW["/sandbox — agent workspace (RW)<br/>/tmp — temporary files (RW)"]
            RO["/usr · /lib · /proc · /app ·<br/>/etc · /var/log · /dev/urandom (RO)"]
        end

        subgraph ENTRYPOINT ["Entrypoint"]
            START_SCRIPT["nemoclaw-start.sh<br/>Starts OpenClaw gateway,<br/>configures auth profiles,<br/>applies policies"]
        end
    end

    classDef rw fill:#76b900,stroke:#333,color:#fff
    classDef ro fill:#e6f2cc,stroke:#76b900,color:#1a1a1a
    classDef runtime fill:#333,stroke:#76b900,color:#fff
    classDef entry fill:#4a90d9,stroke:#333,color:#fff

    class RW rw
    class RO ro
    class USER_SANDBOX,NODEJS,PYTHON,OPENCLAW_CLI,NEMOCLAW_PLUGIN,BLUEPRINT_RUNNER runtime
    class START_SCRIPT entry

    style CONTAINER fill:none,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style RUNTIME fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
    style FS fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
    style ENTRYPOINT fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
```
