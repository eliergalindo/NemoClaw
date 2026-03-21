#!/usr/bin/env python3
"""Generate the Lakera Guard Integration Analysis Word document."""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn


def set_cell_shading(cell, color_hex):
    """Set background color on a table cell."""
    shading = cell._element.get_or_add_tcPr()
    shd = shading.makeelement(qn("w:shd"), {
        qn("w:fill"): color_hex,
        qn("w:val"): "clear",
    })
    shading.append(shd)


def style_header_row(row, color_hex="1B2A4A"):
    """Style a header row with dark background and white bold text."""
    for cell in row.cells:
        set_cell_shading(cell, color_hex)
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                run.font.bold = True
                run.font.size = Pt(9)


def add_table_row(table, cells, bold_first=False):
    """Add a row to a table with cell contents."""
    row = table.add_row()
    for i, text in enumerate(cells):
        cell = row.cells[i]
        p = cell.paragraphs[0]
        run = p.add_run(str(text))
        run.font.size = Pt(9)
        if bold_first and i == 0:
            run.font.bold = True
    return row


def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)
    return h


def main():
    doc = Document()

    # Page setup
    section = doc.sections[0]
    section.page_width = Cm(29.7)  # A4 landscape
    section.page_height = Cm(21.0)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    # -- Title --
    title = doc.add_heading("NemoClaw + Lakera Guard Integration", level=0)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)

    subtitle = doc.add_paragraph()
    run = subtitle.add_run("Security Analysis & Double-Layer Content Protection")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    run.font.italic = True

    meta = doc.add_paragraph()
    run = meta.add_run("Prepared: March 2026  |  Classification: Internal Review  |  Branch: claude/lakera-security-integration")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    doc.add_page_break()

    # ================================================================
    # TABLE OF CONTENTS (manual)
    # ================================================================
    add_heading(doc, "Table of Contents", level=1)
    toc_items = [
        "1. Executive Summary",
        "2. Current Security Architecture (4 Layers)",
        "3. Identified Security Gaps",
        "4. Lakera Guard Integration — Two Additional Layers",
        "5. Layer-by-Layer Comparison",
        "6. Threat Coverage Matrix",
        "7. Operational Characteristics",
        "8. Risk Residual Summary",
        "9. Integration Points in Code",
        "10. Runtime Data Flow",
        "11. Recommendations",
    ]
    for item in toc_items:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_after = Pt(2)
        for run in p.runs:
            run.font.size = Pt(11)

    doc.add_page_break()

    # ================================================================
    # 1. EXECUTIVE SUMMARY
    # ================================================================
    add_heading(doc, "1. Executive Summary", level=1)
    doc.add_paragraph(
        "NemoClaw provides a robust 4-layer infrastructure security model for sandboxing "
        "autonomous AI agents: network isolation (deny-by-default egress), filesystem confinement "
        "(Landlock LSM), process isolation (seccomp + non-root user), and inference routing "
        "(OpenShell gateway proxy). However, it currently has no content-level security on LLM "
        "interactions — prompts and completions pass through the gateway uninspected."
    )
    doc.add_paragraph(
        "Integrating Lakera Guard adds two additional security layers — input screening and output "
        "screening — that detect and block prompt injection, jailbreaks, PII leakage, toxic content, "
        "and data exfiltration at the content level. This creates a complete 6-layer defense-in-depth "
        "model where no single layer failure compromises the system."
    )
    doc.add_paragraph(
        "The integration is minimally invasive: Lakera hooks into the existing OpenShell inference "
        "gateway proxy, requires no agent modification, and can be toggled via hot-reloadable "
        "policy presets without sandbox restart."
    )

    doc.add_page_break()

    # ================================================================
    # 2. CURRENT SECURITY ARCHITECTURE
    # ================================================================
    add_heading(doc, "2. Current Security Architecture (4 Layers)", level=1)
    doc.add_paragraph(
        "NemoClaw enforces a defense-in-depth model through OpenShell with the following layers:"
    )

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, text in enumerate(["Layer", "Security Domain", "Mechanism", "Reload"]):
        hdr.cells[i].paragraphs[0].add_run(text)
    style_header_row(hdr)

    rows = [
        ["1 — Network", "Unauthorized outbound connections", "Deny-by-default egress policy; allowlist-only endpoints; operator approves unknowns via TUI", "Hot-reloadable"],
        ["2 — Filesystem", "Unauthorized file access", "Landlock LSM (best-effort); /sandbox + /tmp writeable; system paths read-only", "Creation-locked"],
        ["3 — Process", "Privilege escalation", "seccomp + non-root sandbox:sandbox user; dangerous syscalls blocked", "Creation-locked"],
        ["4 — Inference", "Rogue LLM API calls", "OpenShell gateway proxies all LLM traffic; credentials injected server-side", "Hot-reloadable"],
    ]
    for r in rows:
        add_table_row(table, r, bold_first=True)

    doc.add_page_break()

    # ================================================================
    # 3. IDENTIFIED SECURITY GAPS
    # ================================================================
    add_heading(doc, "3. Identified Security Gaps", level=1)
    doc.add_paragraph(
        "Despite strong infrastructure isolation, NemoClaw has no content-level security "
        "on LLM interactions. The following gaps exist:"
    )

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, text in enumerate(["Gap", "Description", "Risk Level"]):
        hdr.cells[i].paragraphs[0].add_run(text)
    style_header_row(hdr)

    gaps = [
        ["No prompt injection detection", "Malicious prompts embedded in user input, tool output, or retrieved documents can hijack agent behavior", "HIGH"],
        ["No PII / data leakage scanning", "Sensitive data (API keys, credentials, personal info) can be exfiltrated via LLM completions", "HIGH"],
        ["No toxic content filtering", "Agent-generated content is forwarded to users unfiltered", "MEDIUM"],
        ["No content-level audit trail", "Only network-level approvals are logged; no content analysis records", "MEDIUM"],
        ["Credentials stored as plaintext", "~/.nemoclaw/credentials.json has no encryption at rest", "MEDIUM"],
    ]
    for r in gaps:
        row = add_table_row(table, r, bold_first=True)
        # Color the risk cell
        risk_cell = row.cells[2]
        if r[2] == "HIGH":
            set_cell_shading(risk_cell, "FFCCCC")
        elif r[2] == "MEDIUM":
            set_cell_shading(risk_cell, "FFF3CD")

    doc.add_page_break()

    # ================================================================
    # 4. LAKERA GUARD — TWO ADDITIONAL LAYERS
    # ================================================================
    add_heading(doc, "4. Lakera Guard Integration — Two Additional Layers", level=1)
    doc.add_paragraph(
        "Lakera Guard is an AI security API that screens LLM inputs and outputs in real-time. "
        "Integrating it into NemoClaw creates two additional security layers on top of the "
        "existing four:"
    )

    add_heading(doc, "Layer 5 — Input Screening (Pre-Inference)", level=2)
    doc.add_paragraph(
        "Before any prompt reaches the LLM provider, the OpenShell gateway sends it to "
        "Lakera Guard for analysis. The guard detects prompt injection, jailbreak attempts, "
        "and PII present in the input. If a threat is detected, the request is blocked and "
        "the operator is notified."
    )

    add_heading(doc, "Layer 6 — Output Screening (Post-Inference)", level=2)
    doc.add_paragraph(
        "After the LLM returns a completion, the gateway sends it to Lakera Guard before "
        "forwarding to the agent. The guard detects PII leakage, toxic content, and data "
        "exfiltration attempts. PII is redacted; harmful content is blocked."
    )

    add_heading(doc, "Architecture Diagram", level=2)
    flow_lines = [
        "Agent (inside sandbox)",
        "  │",
        "  ▼",
        "OpenShell Gateway",
        "  │",
        "  ├──▶ [LAYER 5: Lakera INPUT Guard] ──▶ flagged? ──▶ BLOCK + notify operator",
        "  │                                         │",
        "  │                                     clean ▼",
        "  │                                   LLM Provider (NVIDIA / NIM / vLLM / Ollama)",
        "  │                                         │",
        "  │                                     response ▼",
        "  ├──◀ [LAYER 6: Lakera OUTPUT Guard] ──◀ flagged? ──▶ REDACT/BLOCK + notify",
        "  │                                         │",
        "  │                                     clean ▼",
        "  ◀─── sanitized response returned to Agent",
        "",
        "Existing layers (always active):",
        "  Layer 4: Inference routing (OpenShell proxy)",
        "  Layer 3: Process isolation (seccomp + sandbox user)",
        "  Layer 2: Filesystem confinement (Landlock LSM)",
        "  Layer 1: Network policy (deny-by-default egress)",
    ]
    for line in flow_lines:
        p = doc.add_paragraph(line)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        for run in p.runs:
            run.font.name = "Courier New"
            run.font.size = Pt(9)

    doc.add_page_break()

    # ================================================================
    # 5. LAYER-BY-LAYER COMPARISON
    # ================================================================
    add_heading(doc, "5. Layer-by-Layer Comparison", level=1)

    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, text in enumerate(["Layer", "Security Domain", "Without Lakera", "With Lakera", "Delta"]):
        hdr.cells[i].paragraphs[0].add_run(text)
    style_header_row(hdr)

    comparison = [
        ["1 — Network", "Network Isolation",
         "Deny-by-default egress; allowlist-only endpoints; operator approves unknowns in real-time",
         "Same + api.lakera.ai:443 added to baseline allowlist",
         "No change in posture; one trusted endpoint added"],
        ["2 — Filesystem", "Filesystem Confinement",
         "Landlock LSM; /sandbox + /tmp writeable; system paths read-only",
         "Unchanged",
         "No change"],
        ["3 — Process", "Process Isolation",
         "seccomp + non-root sandbox:sandbox user; no privilege escalation",
         "Unchanged",
         "No change"],
        ["4 — Inference", "Inference Routing",
         "OpenShell gateway proxies all LLM traffic; credentials injected server-side, invisible to agent",
         "Gateway now wraps each call with Lakera pre/post hooks",
         "Proxy becomes active inspection point"],
        ["5 — Input", "Input Screening",
         "None — prompts forwarded to LLM without inspection",
         "Lakera Guard scans every prompt before it reaches the LLM",
         "NEW LAYER: blocks prompt injection, jailbreaks, PII in prompts"],
        ["6 — Output", "Output Screening",
         "None — LLM responses forwarded to agent without inspection",
         "Lakera Guard scans every completion before it reaches the agent",
         "NEW LAYER: redacts PII, blocks toxic content, prevents data exfiltration"],
    ]
    for r in comparison:
        row = add_table_row(table, r, bold_first=True)
        if r[0].startswith("5") or r[0].startswith("6"):
            set_cell_shading(row.cells[4], "D4EDDA")  # green highlight for new layers

    doc.add_page_break()

    # ================================================================
    # 6. THREAT COVERAGE MATRIX
    # ================================================================
    add_heading(doc, "6. Threat Coverage Matrix", level=1)
    doc.add_paragraph(
        "The following table shows which layer addresses each threat vector. "
        "Cells marked BLOCKED/FLAGGED/REDACTED indicate active protection."
    )

    headers = ["Threat Vector", "L1\nNetwork", "L2\nFilesys", "L3\nProcess", "L4\nInference", "L5\nLakera In", "L6\nLakera Out"]
    table = doc.add_table(rows=1, cols=7)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, text in enumerate(headers):
        hdr.cells[i].paragraphs[0].add_run(text)
    style_header_row(hdr)

    threats = [
        ["Unauthorized outbound connections",   "BLOCKED", "—", "—", "—", "—", "—"],
        ["Filesystem escape (/etc/shadow, etc.)", "—", "BLOCKED", "—", "—", "—", "—"],
        ["Privilege escalation / dangerous syscalls", "—", "—", "BLOCKED", "—", "—", "—"],
        ["Rogue LLM API calls (bypass provider)", "BLOCKED", "—", "—", "BLOCKED", "—", "—"],
        ["Direct prompt injection",              "—", "—", "—", "—", "BLOCKED", "—"],
        ["Indirect prompt injection (tool output)", "—", "—", "—", "—", "BLOCKED", "—"],
        ["Jailbreak attempts",                   "—", "—", "—", "—", "BLOCKED", "—"],
        ["PII leakage in prompts",               "—", "—", "—", "—", "FLAGGED", "—"],
        ["PII in LLM responses",                 "—", "—", "—", "—", "—", "REDACTED"],
        ["Toxic / harmful content generation",   "—", "—", "—", "—", "—", "BLOCKED"],
        ["Data exfiltration via completions",    "Partial", "—", "—", "—", "—", "BLOCKED"],
        ["Credential leakage in context",        "—", "—", "—", "—", "DETECTED", "REDACTED"],
        ["Unauthorized package installs",        "BLOCKED", "BLOCKED", "—", "—", "—", "—"],
        ["Container breakout",                   "—", "BLOCKED", "BLOCKED", "—", "—", "—"],
    ]
    for r in threats:
        row = add_table_row(table, r, bold_first=True)
        for i in range(1, 7):
            val = r[i]
            if val in ("BLOCKED", "DETECTED", "FLAGGED", "REDACTED"):
                set_cell_shading(row.cells[i], "D4EDDA")
            elif val == "Partial":
                set_cell_shading(row.cells[i], "FFF3CD")

    doc.add_page_break()

    # ================================================================
    # 7. OPERATIONAL CHARACTERISTICS
    # ================================================================
    add_heading(doc, "7. Operational Characteristics", level=1)

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, text in enumerate(["Dimension", "Without Lakera (4 Layers)", "With Lakera (6 Layers)"]):
        hdr.cells[i].paragraphs[0].add_run(text)
    style_header_row(hdr)

    ops = [
        ["Protection scope", "Infrastructure only (network, fs, process, routing)", "Infrastructure + content-level AI security"],
        ["LLM content visibility", "Opaque — gateway routes traffic but does not inspect payloads", "Full inspection — every prompt and completion scanned"],
        ["Prompt injection defense", "None", "Real-time detection and blocking"],
        ["PII protection", "None", "Input flagging + output redaction"],
        ["Audit granularity", "Network-level (host:port approved/denied)", "Network-level + content-level (threat type, severity, content hash)"],
        ["Agent modification required", "N/A", "None — transparent proxy integration"],
        ["Latency overhead", "0 ms", "~50–100 ms per LLM call (negligible vs. LLM inference time)"],
        ["Hot-reloadable", "Yes (network policies)", "Yes (Lakera can be toggled via policy preset)"],
        ["Credential management", "NVIDIA_API_KEY, GITHUB_TOKEN, TELEGRAM_BOT_TOKEN", "Same + LAKERA_GUARD_API_KEY"],
        ["Operator notifications", "Unknown host approval prompts (TUI)", "Same + content-threat alerts with classification"],
    ]
    for r in ops:
        add_table_row(table, r, bold_first=True)

    doc.add_page_break()

    # ================================================================
    # 8. RISK RESIDUAL SUMMARY
    # ================================================================
    add_heading(doc, "8. Risk Residual Summary", level=1)

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, text in enumerate(["Risk Category", "4-Layer Risk", "6-Layer Risk", "Reduction"]):
        hdr.cells[i].paragraphs[0].add_run(text)
    style_header_row(hdr)

    risks = [
        ["Infrastructure compromise",       "LOW",    "LOW",  "—"],
        ["Network exfiltration",             "LOW",    "LOW",  "—"],
        ["Prompt injection / jailbreak",     "HIGH",   "LOW",  "Significant"],
        ["PII / data leakage via LLM",       "HIGH",   "LOW",  "Significant"],
        ["Toxic content generation",         "MEDIUM", "LOW",  "Moderate"],
        ["Credential exposure in context",   "MEDIUM", "LOW",  "Moderate"],
        ["Supply chain (packages)",          "LOW",    "LOW",  "—"],
    ]
    for r in risks:
        row = add_table_row(table, r, bold_first=True)
        # Color risk cells
        for idx in [1, 2]:
            val = r[idx]
            if val == "HIGH":
                set_cell_shading(row.cells[idx], "FFCCCC")
            elif val == "MEDIUM":
                set_cell_shading(row.cells[idx], "FFF3CD")
            elif val == "LOW":
                set_cell_shading(row.cells[idx], "D4EDDA")
        # Color reduction
        if r[3] == "Significant":
            set_cell_shading(row.cells[3], "D4EDDA")
        elif r[3] == "Moderate":
            set_cell_shading(row.cells[3], "D4EDDA")

    doc.add_page_break()

    # ================================================================
    # 9. INTEGRATION POINTS IN CODE
    # ================================================================
    add_heading(doc, "9. Integration Points in Code", level=1)
    doc.add_paragraph(
        "The following table identifies the exact files and locations where changes are "
        "needed to integrate Lakera Guard into NemoClaw:"
    )

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, text in enumerate(["File", "Location", "Change", "Purpose"]):
        hdr.cells[i].paragraphs[0].add_run(text)
    style_header_row(hdr)

    code_points = [
        ["bin/lib/credentials.js", "After line 73", "Add ensureLakeraKey()", "Prompt for and store LAKERA_GUARD_API_KEY"],
        ["bin/lib/onboard.js", "Line 509 (between steps 5–6)", "Add Step 5.5: Configure Lakera Guard", "Call ensureLakeraKey(), register proxy sidecar"],
        ["policies/openclaw-sandbox.yaml", "After line 168", "Add lakera_guard network policy entry", "Allow api.lakera.ai:443 in baseline policy"],
        ["policies/presets/lakera.yaml", "New file", "Create optional Lakera preset", "Enable Lakera for users who skip onboard"],
        ["orchestrator/runner.py", "Lines 189–225", "Deploy Lakera guard proxy middleware", "Wire input/output screening into inference flow"],
        ["nemoclaw/src/index.ts", "Line 146", "Add LAKERA_GUARD_API_KEY to NemoClawConfig", "Expose config to plugin system"],
        ["bin/nemoclaw.js", "Lines 271–288", "Update help text", "Document Lakera Guard commands"],
    ]
    for r in code_points:
        add_table_row(table, r, bold_first=True)

    doc.add_page_break()

    # ================================================================
    # 10. RUNTIME DATA FLOW
    # ================================================================
    add_heading(doc, "10. Runtime Data Flow", level=1)

    add_heading(doc, "Layer 5 — Input Guard (Pre-Inference)", level=2)
    steps_input = [
        "1. Agent constructs prompt (system + user + tool outputs).",
        "2. OpenShell gateway intercepts the outbound request.",
        "3. Gateway sends prompt to Lakera Guard API:",
        "     POST https://api.lakera.ai/v2/guard",
        '     { "input": "<full prompt>", "type": "prompt_injection" }',
        "4. If Lakera flags the input:",
        "     a. Log the threat (type, severity, content hash).",
        "     b. BLOCK the request — return HTTP 403 to agent.",
        "     c. Notify operator via OpenShell TUI alert.",
        "5. If clean: forward to LLM provider normally.",
    ]
    for s in steps_input:
        p = doc.add_paragraph(s)
        for run in p.runs:
            run.font.size = Pt(10)

    add_heading(doc, "Layer 6 — Output Guard (Post-Inference)", level=2)
    steps_output = [
        "1. LLM returns completion to the OpenShell gateway.",
        "2. Gateway sends response to Lakera Guard API:",
        "     POST https://api.lakera.ai/v2/guard",
        '     { "input": "<completion>", "type": "pii,toxicity,relevance" }',
        "3. If Lakera flags the output:",
        "     a. Log the threat (type, severity, content hash).",
        "     b. REDACT PII — replace sensitive tokens with [REDACTED].",
        "     c. BLOCK harmful content — return sanitized version.",
        "     d. Notify operator via OpenShell TUI alert.",
        "4. If clean: forward to agent normally.",
    ]
    for s in steps_output:
        p = doc.add_paragraph(s)
        for run in p.runs:
            run.font.size = Pt(10)

    doc.add_page_break()

    # ================================================================
    # 11. RECOMMENDATIONS
    # ================================================================
    add_heading(doc, "11. Recommendations", level=1)

    recs = [
        ("Adopt Lakera Guard at the gateway proxy level",
         "This is the highest-value, lowest-friction integration point. It requires zero changes "
         "to the sandboxed agent, works with all inference providers (NVIDIA Cloud, NIM, vLLM, "
         "Ollama), and can be hot-reloaded via policy presets."),
        ("Make Lakera a default-on onboarding step",
         "Add Lakera Guard configuration to the onboard wizard (Step 5.5) so that all new "
         "sandboxes benefit from content-level protection out of the box."),
        ("Create a Lakera policy preset for opt-in enablement",
         "For users who skip onboarding or upgrade existing sandboxes, provide a lakera.yaml "
         "preset that can be applied via 'nemoclaw <name> policy-add'."),
        ("Implement content-level audit logging",
         "Lakera Guard responses should be logged to a structured audit file alongside existing "
         "network-level approval logs, creating a complete security audit trail."),
        ("Consider Lakera Guard for credential rotation alerts",
         "If Lakera detects credential patterns (API keys, tokens) in prompts or completions, "
         "trigger an automated credential rotation workflow."),
        ("Encrypt credentials at rest",
         "Independently of Lakera, the plaintext ~/.nemoclaw/credentials.json should be "
         "encrypted at rest using OS keychain integration (macOS Keychain, Linux secret-tool)."),
    ]
    for title, body in recs:
        p = doc.add_paragraph()
        run = p.add_run(f"{title}: ")
        run.font.bold = True
        run.font.size = Pt(10)
        run = p.add_run(body)
        run.font.size = Pt(10)

    # -- Footer note --
    doc.add_paragraph("")
    p = doc.add_paragraph()
    run = p.add_run(
        "This document was prepared for internal review. The analysis is based on the NemoClaw "
        "codebase at branch claude/lakera-security-integration-6glBA as of March 2026."
    )
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    run.font.italic = True

    # Save
    output_path = "/home/user/NemoClaw/NemoClaw_Lakera_Security_Analysis.docx"
    doc.save(output_path)
    print(f"Document saved to: {output_path}")


if __name__ == "__main__":
    main()
