"""Tests for resilience_lib.stack_env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from resilience_lib.stack_env import load_stack_env


def test_load_stack_env_parses_key_value(tmp_path, monkeypatch):
    env_file = tmp_path / "stack.env"
    env_file.write_text("FOO=bar\nBAZ=qux\n")
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("BAZ", raising=False)

    load_stack_env(root=tmp_path)

    assert os.environ["FOO"] == "bar"
    assert os.environ["BAZ"] == "qux"


def test_load_stack_env_skips_comments(tmp_path, monkeypatch):
    env_file = tmp_path / "stack.env"
    env_file.write_text("# this is a comment\nREAL_KEY=real_value\n")
    monkeypatch.delenv("REAL_KEY", raising=False)

    load_stack_env(root=tmp_path)

    assert os.environ["REAL_KEY"] == "real_value"


def test_load_stack_env_does_not_overwrite_existing(tmp_path, monkeypatch):
    env_file = tmp_path / "stack.env"
    env_file.write_text("EXISTING_VAR=new_value\n")
    monkeypatch.setenv("EXISTING_VAR", "original_value")

    load_stack_env(root=tmp_path)

    assert os.environ["EXISTING_VAR"] == "original_value"


def test_load_stack_env_missing_file_is_noop(tmp_path):
    # No stack.env in tmp_path — should not raise
    result = load_stack_env(root=tmp_path)
    assert result == tmp_path / "stack.env"


def test_load_stack_env_skips_blank_lines(tmp_path, monkeypatch):
    env_file = tmp_path / "stack.env"
    env_file.write_text("\n\nVALID=yes\n\n")
    monkeypatch.delenv("VALID", raising=False)

    load_stack_env(root=tmp_path)

    assert os.environ["VALID"] == "yes"


def test_load_stack_env_value_with_equals(tmp_path, monkeypatch):
    """Values that contain '=' are preserved correctly."""
    env_file = tmp_path / "stack.env"
    env_file.write_text("URL=http://host/path?a=1\n")
    monkeypatch.delenv("URL", raising=False)

    load_stack_env(root=tmp_path)

    assert os.environ["URL"] == "http://host/path?a=1"
