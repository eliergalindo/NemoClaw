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

## 3a. Inference Security with Lakera Guard

The current inference pipeline has **no content-level security** — only network-level
allow-listing. Lakera Guard can be inserted as a request/response screening layer
between the OpenShell gateway and the inference provider to detect prompt injections,
jailbreaks, data leakage, and content policy violations.

### Current State vs. Proposed State

```{mermaid}
flowchart TB
    subgraph CURRENT ["CURRENT: No Content Security"]
        direction LR
        C_AGENT["Agent"] -->|"prompt"| C_GW["OpenShell<br/>Gateway"]
        C_GW -->|"network policy<br/>check only"| C_PROVIDER["Inference<br/>Provider"]
        C_PROVIDER -->|"response<br/>(unscreened)"| C_GW
        C_GW -->|"response"| C_AGENT
    end

    subgraph PROPOSED ["PROPOSED: With Lakera Guard"]
        direction LR
        P_AGENT["Agent"] -->|"prompt"| P_GW["OpenShell<br/>Gateway"]
        P_GW -->|"1. screen<br/>request"| P_GUARD["Lakera Guard<br/>(sidecar or SaaS)"]
        P_GUARD -->|"2. safe prompt<br/>forwarded"| P_PROVIDER["Inference<br/>Provider"]
        P_PROVIDER -->|"3. LLM<br/>response"| P_GUARD2["Lakera Guard<br/>(response screen)"]
        P_GUARD2 -->|"4. safe response<br/>returned"| P_AGENT
    end

    classDef nv fill:#76b900,stroke:#333,color:#fff
    classDef guard fill:#ff6b35,stroke:#333,color:#fff
    classDef provider fill:#e6f2cc,stroke:#76b900,color:#1a1a1a
    classDef current fill:#999,stroke:#333,color:#fff

    class C_AGENT,C_GW current
    class C_PROVIDER current
    class P_AGENT,P_GW nv
    class P_GUARD,P_GUARD2 guard
    class P_PROVIDER provider

    style CURRENT fill:#fff5f5,stroke:#d94a4a,stroke-width:2px,color:#1a1a1a
    style PROPOSED fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
```

### Detailed Lakera Guard Integration in Inference Pipeline

```{mermaid}
flowchart TD
    AGENT["OpenClaw Agent<br/>(inside sandbox)"]

    subgraph GW ["OpenShell Gateway (inference.local/v1)"]
        direction TB
        TLS["TLS termination +<br/>network policy check"]
    end

    subgraph LAKERA ["LAKERA GUARD LAYER"]
        direction TB

        subgraph PRE ["PRE-INFERENCE SCREENING"]
            direction TB
            PI["Prompt Injection<br/>Detection"]
            JB["Jailbreak<br/>Detection"]
            DL_IN["Data Leakage<br/>Scan (PII in prompt)"]
            CV_IN["Content Violation<br/>Check"]
        end

        DECISION_IN{"Threat<br/>detected?"}
    end

    subgraph PROVIDER ["INFERENCE PROVIDER"]
        direction TB
        NV_CLOUD["NVIDIA Cloud"]
        NIM_LOCAL["NIM Local"]
        VLLM_LOCAL["vLLM Local"]
        OLLAMA_LOCAL["Ollama Local"]
    end

    subgraph LAKERA_OUT ["LAKERA GUARD LAYER (Response)"]
        direction TB

        subgraph POST ["POST-INFERENCE SCREENING"]
            direction TB
            DL_OUT["Data Leakage<br/>Scan (PII in response)"]
            CV_OUT["Content Violation<br/>Check"]
            ML["Malicious Link<br/>Detection"]
            HALLUC["Harmful Content<br/>Detection"]
        end

        DECISION_OUT{"Threat<br/>detected?"}
    end

    AGENT -->|"system prompt +<br/>user message"| TLS
    TLS -->|"authorized request"| PRE
    PI --> JB --> DL_IN --> CV_IN
    CV_IN --> DECISION_IN
    DECISION_IN -->|"SAFE"| PROVIDER
    DECISION_IN -->|"BLOCKED"| ALERT_IN([Alert operator +<br/>log to audit trail])

    PROVIDER -->|"LLM response"| POST
    DL_OUT --> CV_OUT --> ML --> HALLUC
    HALLUC --> DECISION_OUT
    DECISION_OUT -->|"SAFE"| AGENT
    DECISION_OUT -->|"BLOCKED"| ALERT_OUT([Sanitize or reject<br/>+ log to audit trail])

    classDef nv fill:#76b900,stroke:#333,color:#fff
    classDef guard fill:#ff6b35,stroke:#333,color:#fff
    classDef provider fill:#e6f2cc,stroke:#76b900,color:#1a1a1a
    classDef blocked fill:#d94a4a,stroke:#333,color:#fff
    classDef decision fill:#ff6b35,stroke:#333,color:#fff

    class AGENT nv
    class TLS nv
    class PI,JB,DL_IN,CV_IN,DL_OUT,CV_OUT,ML,HALLUC guard
    class DECISION_IN,DECISION_OUT decision
    class NV_CLOUD,NIM_LOCAL,VLLM_LOCAL,OLLAMA_LOCAL provider
    class ALERT_IN,ALERT_OUT blocked

    style GW fill:none,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style LAKERA fill:none,stroke:#ff6b35,stroke-width:2px,color:#1a1a1a
    style LAKERA_OUT fill:none,stroke:#ff6b35,stroke-width:2px,color:#1a1a1a
    style PRE fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
    style POST fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
    style PROVIDER fill:none,stroke:#999,stroke-width:1px,color:#1a1a1a
```

### Integration Options

```{mermaid}
flowchart TB
    subgraph OPT_A ["Option A: Gateway Sidecar (Recommended)"]
        direction LR
        A1["Start Lakera Guard<br/>container alongside<br/>OpenShell gateway"]
        A2["Route inference.local<br/>through guard proxy<br/>(localhost:8932)"]
        A3["Guard forwards safe<br/>requests to provider"]
        A1 --> A2 --> A3
    end

    subgraph OPT_B ["Option B: SaaS API Middleware"]
        direction LR
        B1["Call Lakera Guard<br/>SaaS API before<br/>each inference call"]
        B2["POST /v2/guard<br/>with full message<br/>context"]
        B3["Proceed only if<br/>flagged_categories<br/>is empty"]
        B1 --> B2 --> B3
    end

    subgraph OPT_C ["Option C: Blueprint Policy Extension"]
        direction LR
        C1["Extend<br/>openclaw-sandbox.yaml<br/>with guard middleware"]
        C2["Policy engine calls<br/>Lakera Guard on<br/>inference endpoints"]
        C3["Block/alert based<br/>on policy rules"]
        C1 --> C2 --> C3
    end

    subgraph WHERE ["Where Each Option Hooks In"]
        direction TB
        W_A["Option A: nemoclaw-start.sh<br/>(start guard before gateway)"]
        W_B["Option B: runner.py<br/>(add --middleware to<br/>openshell provider create)"]
        W_C["Option C: openclaw-sandbox.yaml<br/>(add middleware: lakera-guard<br/>to inference endpoints)"]
    end

    classDef optA fill:#76b900,stroke:#333,color:#fff
    classDef optB fill:#4a90d9,stroke:#333,color:#fff
    classDef optC fill:#ff6b35,stroke:#333,color:#fff
    classDef where fill:#333,stroke:#76b900,color:#fff

    class A1,A2,A3 optA
    class B1,B2,B3 optB
    class C1,C2,C3 optC
    class W_A,W_B,W_C where

    style OPT_A fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style OPT_B fill:#eef4fc,stroke:#4a90d9,stroke-width:2px,color:#1a1a1a
    style OPT_C fill:#fff5ef,stroke:#ff6b35,stroke-width:2px,color:#1a1a1a
    style WHERE fill:none,stroke:#555,stroke-width:1px,stroke-dasharray:5 5,color:#1a1a1a
```

### Security Coverage Matrix

```{mermaid}
flowchart LR
    subgraph EXISTING ["Existing Security (NemoClaw)"]
        direction TB
        E1["Network allow-list<br/>(deny-by-default)"]
        E2["Filesystem isolation<br/>(RW: /sandbox, /tmp)"]
        E3["Process isolation<br/>(unprivileged user)"]
        E4["TLS termination<br/>(gateway level)"]
        E5["Blueprint digest<br/>verification"]
        E6["Credential encryption<br/>(mode 600)"]
    end

    subgraph GAP ["Security Gap (No Coverage)"]
        direction TB
        G1["Prompt injection"]
        G2["Jailbreak attempts"]
        G3["PII / data leakage"]
        G4["Harmful content<br/>generation"]
        G5["Malicious URLs<br/>in LLM output"]
        G6["Indirect injection<br/>via tool/retrieval"]
    end

    subgraph LAKERA_FIX ["Lakera Guard Fills The Gap"]
        direction TB
        L1["Prompt attack<br/>detection"]
        L2["Jailbreak<br/>detection"]
        L3["PII scanner<br/>(request + response)"]
        L4["Content violation<br/>detection"]
        L5["Malicious link<br/>detection"]
        L6["Agentic / MCP<br/>security screening"]
    end

    G1 -.->|"solved by"| L1
    G2 -.->|"solved by"| L2
    G3 -.->|"solved by"| L3
    G4 -.->|"solved by"| L4
    G5 -.->|"solved by"| L5
    G6 -.->|"solved by"| L6

    classDef existing fill:#76b900,stroke:#333,color:#fff
    classDef gap fill:#d94a4a,stroke:#333,color:#fff
    classDef fix fill:#ff6b35,stroke:#333,color:#fff

    class E1,E2,E3,E4,E5,E6 existing
    class G1,G2,G3,G4,G5,G6 gap
    class L1,L2,L3,L4,L5,L6 fix

    style EXISTING fill:#f5faed,stroke:#76b900,stroke-width:2px,color:#1a1a1a
    style GAP fill:#fff5f5,stroke:#d94a4a,stroke-width:2px,color:#1a1a1a
    style LAKERA_FIX fill:#fff5ef,stroke:#ff6b35,stroke-width:2px,color:#1a1a1a
```

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
