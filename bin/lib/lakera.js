// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
// Lakera Guard integration — screens inference requests/responses for prompt
// injection, jailbreaks, PII leakage, and content violations.
//
// Supports two modes:
//   1. SaaS API  — calls api.lakera.ai (requires LAKERA_GUARD_API_KEY)
//   2. Sidecar   — local container on localhost:8932 (self-hosted)
//
// Env:
//   LAKERA_GUARD_API_KEY   API key for Lakera Guard SaaS
//   LAKERA_GUARD_URL       Override guard endpoint (default: https://api.lakera.ai)
//   LAKERA_GUARD_MODE      "saas" | "sidecar" | "disabled" (default: "saas" if key present)

const { runCapture, run } = require("./runner");

const LAKERA_SIDECAR_IMAGE = "lakera/lakera-guard:latest";
const LAKERA_SIDECAR_PORT = 8932;

/**
 * Determine the current guard mode based on environment variables.
 */
function resolveMode() {
  const explicit = process.env.LAKERA_GUARD_MODE;
  if (explicit) return explicit;
  if (process.env.LAKERA_GUARD_API_KEY) return "saas";
  return "disabled";
}

/**
 * Return the base URL for the Lakera Guard API.
 */
function guardBaseUrl() {
  if (process.env.LAKERA_GUARD_URL) {
    return process.env.LAKERA_GUARD_URL.replace(/\/$/, "");
  }
  const mode = resolveMode();
  if (mode === "sidecar") return `http://127.0.0.1:${LAKERA_SIDECAR_PORT}`;
  return "https://api.lakera.ai";
}

/**
 * Start the Lakera Guard sidecar container.
 * Returns { ok, port } on success.
 */
function startSidecar() {
  const name = "lakera-guard";

  // Stop any existing container
  run(`docker rm -f ${name} 2>/dev/null || true`, { ignoreError: true });

  const apiKey = process.env.LAKERA_GUARD_API_KEY || "";
  const { execFileSync } = require("child_process");
  const dockerArgs = [
    "run", "-d", "--name", name, "--restart", "unless-stopped",
    "-p", `${LAKERA_SIDECAR_PORT}:8000`,
  ];
  if (apiKey) {
    dockerArgs.push("-e", `LAKERA_GUARD_API_KEY=${apiKey}`);
  }
  dockerArgs.push(LAKERA_SIDECAR_IMAGE);
  execFileSync("docker", dockerArgs, { stdio: "pipe" });

  // Wait for health
  for (let i = 0; i < 15; i++) {
    const health = runCapture(
      `curl -sf http://127.0.0.1:${LAKERA_SIDECAR_PORT}/health 2>/dev/null`,
      { ignoreError: true }
    );
    if (health && health.includes("ok")) {
      return { ok: true, port: LAKERA_SIDECAR_PORT };
    }
    require("child_process").spawnSync("sleep", ["2"]);
  }

  return { ok: false, port: LAKERA_SIDECAR_PORT };
}

/**
 * Stop and remove the sidecar container.
 */
function stopSidecar() {
  run("docker rm -f lakera-guard 2>/dev/null || true", { ignoreError: true });
}

/**
 * Check if the sidecar container is running.
 */
function sidecarStatus() {
  const out = runCapture(
    'docker inspect --format="{{.State.Running}}" lakera-guard 2>/dev/null',
    { ignoreError: true }
  );
  return { running: out && out.trim() === "true" };
}

/**
 * Screen a prompt (pre-inference) via Lakera Guard API.
 *
 * @param {Array<{role: string, content: string}>} messages - Chat messages
 * @returns {{ flagged: boolean, categories: string[], raw: object }}
 */
function screenRequest(messages) {
  const mode = resolveMode();
  if (mode === "disabled") return { flagged: false, categories: [], raw: {} };

  const baseUrl = guardBaseUrl();
  const apiKey = process.env.LAKERA_GUARD_API_KEY || "";
  const authHeader = apiKey ? `-H "Authorization: Bearer ${apiKey}"` : "";

  const payload = JSON.stringify({ messages });
  // Use a temp file to avoid shell escaping issues with message content
  const fs = require("fs");
  const os = require("os");
  const path = require("path");
  const tmpFile = path.join(os.tmpdir(), `lakera-req-${Date.now()}.json`);
  fs.writeFileSync(tmpFile, payload, "utf8");

  try {
    const result = runCapture(
      `curl -sf -X POST "${baseUrl}/v2/guard" ` +
      `${authHeader} ` +
      `-H "Content-Type: application/json" ` +
      `-d @"${tmpFile}" 2>/dev/null`,
      { ignoreError: true }
    );

    if (!result) return { flagged: false, categories: [], raw: {} };

    const parsed = JSON.parse(result);
    const categories = (parsed.flagged_categories || []).map((c) => c.category || c);
    return {
      flagged: categories.length > 0,
      categories,
      raw: parsed,
    };
  } catch {
    // Guard unavailable — fail open (log but don't block)
    return { flagged: false, categories: [], raw: { error: "guard_unavailable" } };
  } finally {
    try { require("fs").unlinkSync(tmpFile); } catch { /* ignore */ }
  }
}

/**
 * Screen an LLM response (post-inference) via Lakera Guard API.
 *
 * @param {string} responseText - The LLM's response text
 * @param {Array<{role: string, content: string}>} context - Original messages for context
 * @returns {{ flagged: boolean, categories: string[], raw: object }}
 */
function screenResponse(responseText, context) {
  const fullMessages = [
    ...(context || []),
    { role: "assistant", content: responseText },
  ];
  return screenRequest(fullMessages);
}

module.exports = {
  resolveMode,
  guardBaseUrl,
  startSidecar,
  stopSidecar,
  sidecarStatus,
  screenRequest,
  screenResponse,
  LAKERA_SIDECAR_PORT,
};
