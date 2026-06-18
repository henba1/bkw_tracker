"""Tests for scripts/lib/write_env.py :: set_env_values."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

from write_env import set_env_values


def test_update_existing_key(tmp_path):
    env = tmp_path / "test.env"
    env.write_text("FOO=old\nBAR=keep\n")

    set_env_values(env, {"FOO": "new"})

    lines = env.read_text().splitlines()
    assert "FOO=new" in lines
    assert "BAR=keep" in lines


def test_append_new_key(tmp_path):
    env = tmp_path / "test.env"
    env.write_text("EXISTING=1\n")

    set_env_values(env, {"NEW_KEY": "hello"})

    content = env.read_text()
    assert "EXISTING=1" in content
    assert "NEW_KEY=hello" in content


def test_preserves_comments(tmp_path):
    env = tmp_path / "test.env"
    env.write_text("# a comment\nFOO=bar\n")

    set_env_values(env, {"FOO": "baz"})

    content = env.read_text()
    assert "# a comment" in content
    assert "FOO=baz" in content


def test_creates_file_if_missing(tmp_path):
    env = tmp_path / "new.env"
    # file does not exist yet
    set_env_values(env, {"K": "v"})
    assert env.exists()
    assert "K=v" in env.read_text()


def test_value_with_equals_sign(tmp_path):
    env = tmp_path / "test.env"
    env.write_text("URL=http://old\n")

    set_env_values(env, {"URL": "http://host/path?a=1&b=2"})

    assert "URL=http://host/path?a=1&b=2" in env.read_text()


def test_multiple_updates_at_once(tmp_path):
    env = tmp_path / "test.env"
    env.write_text("A=1\nB=2\nC=3\n")

    set_env_values(env, {"A": "10", "C": "30"})

    lines = env.read_text().splitlines()
    assert "A=10" in lines
    assert "B=2" in lines
    assert "C=30" in lines


def test_output_ends_with_newline(tmp_path):
    env = tmp_path / "test.env"
    env.write_text("X=1\n")
    set_env_values(env, {"X": "2"})
    assert env.read_text().endswith("\n")
