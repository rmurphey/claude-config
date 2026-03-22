#!/usr/bin/env node

/**
 * Global PreToolUse hook for WebFetch.
 *
 * Fetches the URL, checks if the <head> is too large for WebFetch,
 * and denies the call with a detailed breakdown if so.
 *
 * Zero dependencies — uses only Node builtins + regex parsing.
 */

const WARN_THRESHOLD = 50 * 1024;
const FAIL_THRESHOLD = 100 * 1024;

function analyzeHead(html) {
  const headMatch = html.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
  if (!headMatch) {
    return { totalHeadBytes: 0, breakdown: emptyBreakdown(), verdict: "pass" };
  }

  const headContent = headMatch[1];
  const totalHeadBytes = Buffer.byteLength(headContent, "utf-8");

  const breakdown = emptyBreakdown();

  // Inline <style> blocks
  for (const m of headContent.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)) {
    breakdown.inlineStyles.count++;
    breakdown.inlineStyles.bytes += Buffer.byteLength(m[1], "utf-8");
  }

  // <script> blocks — categorize by type and src
  for (const m of headContent.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)) {
    const attrs = m[1];
    const body = m[2];

    if (/type\s*=\s*["']application\/ld\+json["']/i.test(attrs)) {
      breakdown.jsonLd.count++;
      breakdown.jsonLd.bytes += Buffer.byteLength(body, "utf-8");
    } else if (/\bsrc\s*=/i.test(attrs)) {
      breakdown.externalScripts.count++;
    } else {
      breakdown.inlineScripts.count++;
      breakdown.inlineScripts.bytes += Buffer.byteLength(body, "utf-8");
    }
  }

  // External stylesheets: <link rel="stylesheet" ...>
  for (const _ of headContent.matchAll(/<link[^>]+rel\s*=\s*["']stylesheet["'][^>]*>/gi)) {
    breakdown.externalStylesheets.count++;
  }

  // <meta> tags
  for (const m of headContent.matchAll(/<meta[^>]*\/?>/gi)) {
    breakdown.metaTags.count++;
    breakdown.metaTags.bytes += Buffer.byteLength(m[0], "utf-8");
  }

  let verdict;
  if (totalHeadBytes >= FAIL_THRESHOLD) {
    verdict = "fail";
  } else if (totalHeadBytes >= WARN_THRESHOLD) {
    verdict = "warn";
  } else {
    verdict = "pass";
  }

  return { totalHeadBytes, breakdown, verdict };
}

function emptyBreakdown() {
  return {
    inlineStyles: { count: 0, bytes: 0 },
    inlineScripts: { count: 0, bytes: 0 },
    externalStylesheets: { count: 0 },
    externalScripts: { count: 0 },
    metaTags: { count: 0, bytes: 0 },
    jsonLd: { count: 0, bytes: 0 },
  };
}

function formatKB(bytes) {
  return (bytes / 1024).toFixed(1);
}

// --- main ---

const input = await new Promise((resolve) => {
  let data = "";
  process.stdin.on("data", (chunk) => (data += chunk));
  process.stdin.on("end", () => resolve(data));
});

const { tool_input: toolInput } = JSON.parse(input);
const url = toolInput?.url;

if (!url) {
  process.exit(0);
}

try {
  const response = await fetch(url, {
    headers: { "User-Agent": "claude-check/0.1.0" },
    redirect: "follow",
  });

  if (!response.ok) {
    // Can't fetch — let WebFetch handle its own error
    process.exit(0);
  }

  const html = await response.text();
  const report = analyzeHead(html);

  if (report.verdict === "fail") {
    const { breakdown } = report;
    const reason = [
      `claude-check: <head> is ${formatKB(report.totalHeadBytes)} KB — too large for WebFetch.`,
      `Breakdown: ${breakdown.inlineStyles.count} inline styles (${formatKB(breakdown.inlineStyles.bytes)} KB),`,
      `${breakdown.inlineScripts.count} inline scripts (${formatKB(breakdown.inlineScripts.bytes)} KB),`,
      `${breakdown.jsonLd.count} JSON-LD blocks (${formatKB(breakdown.jsonLd.bytes)} KB),`,
      `${breakdown.metaTags.count} meta tags (${formatKB(breakdown.metaTags.bytes)} KB).`,
      `Consider using Bash with curl and a targeted selector instead.`,
    ].join(" ");

    console.log(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: reason,
        },
      })
    );
  }
} catch {
  // If the check itself fails, don't block WebFetch
  process.exit(0);
}
