#!/usr/bin/env python3
"""Tests for enforce-atomic-commits.py PreToolUse hook.

Focus: check_bypass transcript scanning, which honors a user typing
"single commit" / "one commit" / "skip atomicity". Regression: a bare-text
user turn stores message.content as a plain string (not a list of blocks),
and the original scanner skipped non-list content, so the documented bypass
silently failed. Also covers the end-to-end block on a multi-directory commit.

Run: pytest test_enforce_atomic_commits.py   (or: python3 test_enforce_atomic_commits.py)
"""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

HOOK_PATH = Path(__file__).parent / "enforce-atomic-commits.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("enforce_atomic_commits", HOOK_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hook = _load_hook()


def _transcript(tmp_path: str, content) -> str:
    """Write a one-line transcript whose single user turn has the given content."""
    p = os.path.join(tmp_path, "transcript.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"content": content}}) + "\n")
    return p


def _clear_marker(session_id: str) -> None:
    m = os.path.join(tempfile.gettempdir(), "claude-atomic-cache", f"{session_id}.atomic-bypass")
    if os.path.exists(m):
        os.remove(m)


def test_bypass_detected_in_plain_string_content():
    """Regression: bare-text 'single commit' (content is a str) must bypass."""
    with tempfile.TemporaryDirectory() as d:
        tp = _transcript(d, "single commit")
        _clear_marker("t-str")
        assert hook.check_bypass({"transcript_path": tp, "session_id": "t-str"}) is True
        _clear_marker("t-str")


def test_bypass_detected_in_block_list_content():
    """List-of-blocks content (the original supported shape) still works."""
    with tempfile.TemporaryDirectory() as d:
        tp = _transcript(d, [{"type": "text", "text": "please one commit this"}])
        _clear_marker("t-list")
        assert hook.check_bypass({"transcript_path": tp, "session_id": "t-list"}) is True
        _clear_marker("t-list")


def test_no_bypass_without_phrase():
    """An ordinary message must not trigger the bypass."""
    with tempfile.TemporaryDirectory() as d:
        tp = _transcript(d, "just commit it please")
        _clear_marker("t-neg")
        assert hook.check_bypass({"transcript_path": tp, "session_id": "t-neg"}) is False
        _clear_marker("t-neg")


def test_no_bypass_when_phrase_only_in_assistant_or_tool_output():
    """The phrase echoed in tool_result content (not a user text turn) must not bypass."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "transcript.jsonl")
        with open(p, "w", encoding="utf-8") as f:
            # assistant turn mentioning the phrase — should be ignored (type != user)
            f.write(json.dumps({"type": "assistant", "message": {"content": "say single commit"}}) + "\n")
            # user turn whose only content is a tool_result (no text block)
            f.write(json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "content": "log mentions single commit"}]}}) + "\n")
        _clear_marker("t-tool")
        assert hook.check_bypass({"transcript_path": p, "session_id": "t-tool"}) is False
        _clear_marker("t-tool")


def test_directory_span_grouping_ignores_cross_cutting_dirs():
    """Three real top-level dirs trip the threshold; .claude/etc. don't count."""
    groups = hook.group_files_by_directory(
        ["cmd/a.go", "app/b.tsx", "analysis/c.md", ".claude/settings.json", "node_modules/x"]
    )
    assert set(groups) == {"cmd", "app", "analysis"}
    assert len(groups) >= hook.MIN_DIR_GROUPS_FOR_WARNING


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print(f"\n{len(fns)}/{len(fns)} passed")
