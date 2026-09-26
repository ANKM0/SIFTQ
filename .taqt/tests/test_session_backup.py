"""Tests for encrypted session backup (Issue #571)."""

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.session_backup import (
    backup_codex,
    backup_opencode,
    resolve_identity,
    restore_codex,
    restore_opencode,
)


def test_resolve_identity_prefers_identity_file(tmp_path: Path) -> None:
    identity_file = tmp_path / "explicit.key"
    resolved = resolve_identity(
        {"AGE_IDENTITY_FILE": str(identity_file), "AGE_IDENTITY": "inline-key"}
    )
    assert resolved == identity_file


def test_resolve_identity_uses_inline_identity_without_file() -> None:
    assert resolve_identity({"AGE_IDENTITY": "AGE-SECRET-KEY-1INLINE"}) == (
        "AGE-SECRET-KEY-1INLINE"
    )


def test_resolve_identity_defaults_to_config_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AGE_IDENTITY_FILE", raising=False)
    monkeypatch.delenv("AGE_IDENTITY", raising=False)

    assert resolve_identity() == tmp_path / ".config" / "age" / "session.key"


def test_resolve_identity_treats_blank_env_as_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGE_IDENTITY_FILE", "")
    monkeypatch.setenv("AGE_IDENTITY", "")

    assert resolve_identity() == tmp_path / ".config" / "age" / "session.key"


def _age_recipient_file(tmp_path: Path) -> tuple[Path, Path]:
    identity = tmp_path / "session.key"
    subprocess.run(
        ["age-keygen", "-o", str(identity)],
        check=True,
        capture_output=True,
    )
    recipient = subprocess.run(
        ["age-keygen", "-y", str(identity)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    recipient_file = tmp_path / "recipient.pub"
    recipient_file.write_text(recipient + "\n", encoding="utf-8")
    return identity, recipient_file


def _seed_session(sessions_root: Path, name: str, content: bytes) -> Path:
    source = sessions_root / "2026" / "09" / "26" / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(content)
    return source


def _decrypt(target: Path, identity: Path) -> bytes:
    compressed = subprocess.run(
        ["age", "-d", "-i", str(identity)],
        input=target.read_bytes(),
        check=True,
        capture_output=True,
    ).stdout
    return subprocess.run(
        ["zstd", "-d", "-c"],
        input=compressed,
        check=True,
        capture_output=True,
    ).stdout


def test_backup_codex_writes_dated_encrypted_archive(tmp_path: Path) -> None:
    content = b'{"type":"session","payload":"hello"}\n'
    sessions_root = tmp_path / "sessions"
    source = _seed_session(sessions_root, "rollout-abc.jsonl", content)
    identity, recipient_file = _age_recipient_file(tmp_path)

    created = backup_codex(
        sessions_root=sessions_root,
        output_root=tmp_path / "out",
        recipient_file=recipient_file,
    )

    target = tmp_path / "out" / "codex" / "2026" / "09" / "26" / "rollout-abc.jsonl.zst.age"
    assert created == [target]
    assert target.is_file()
    assert _decrypt(target, identity) == content
    assert str(source).encode() not in target.read_bytes()


def test_backup_codex_skips_unchanged_archives(tmp_path: Path) -> None:
    sessions_root = tmp_path / "sessions"
    _seed_session(sessions_root, "rollout-abc.jsonl", b"{}\n")
    _, recipient_file = _age_recipient_file(tmp_path)
    kwargs = {
        "sessions_root": sessions_root,
        "output_root": tmp_path / "out",
        "recipient_file": recipient_file,
    }

    first = backup_codex(**kwargs)
    second = backup_codex(**kwargs)

    assert len(first) == 1
    assert second == []


def _seed_opencode_db(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE event (id INTEGER PRIMARY KEY, payload TEXT)")
    connection.execute(
        "INSERT INTO event (payload) VALUES (?)", ("secret-session-event",)
    )
    connection.commit()
    return connection


def test_backup_opencode_encrypts_consistent_snapshot_with_events(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "opencode.db"
    writer = _seed_opencode_db(db_path)
    try:
        identity, recipient_file = _age_recipient_file(tmp_path)

        created = backup_opencode(
            db_path=db_path,
            output_root=tmp_path / "out",
            recipient_file=recipient_file,
        )
    finally:
        writer.close()

    target = tmp_path / "out" / "opencode" / "opencode.db.zst.age"
    assert created == target
    assert target.is_file()
    assert b"secret-session-event" not in target.read_bytes()

    restored = tmp_path / "restored.db"
    restored.write_bytes(_decrypt(target, identity))
    with sqlite3.connect(restored) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        rows = connection.execute("SELECT payload FROM event").fetchall()
    assert rows == [("secret-session-event",)]


def test_restore_codex_reproduces_original_content(tmp_path: Path) -> None:
    content = b'{"type":"session","payload":"round-trip"}\n'
    sessions_root = tmp_path / "sessions"
    _seed_session(sessions_root, "rollout-abc.jsonl", content)
    identity, recipient_file = _age_recipient_file(tmp_path)
    backup_root = tmp_path / "out"
    backup_codex(
        sessions_root=sessions_root,
        output_root=backup_root,
        recipient_file=recipient_file,
    )

    restored_root = tmp_path / "restored"
    restored = restore_codex(
        backup_root=backup_root,
        sessions_root=restored_root,
        identity=identity,
    )

    target = restored_root / "2026" / "09" / "26" / "rollout-abc.jsonl"
    assert restored == [target]
    assert target.read_bytes() == content


def test_restore_opencode_reproduces_queryable_database(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    writer = _seed_opencode_db(db_path)
    try:
        identity, recipient_file = _age_recipient_file(tmp_path)
        backup_root = tmp_path / "out"
        backup_opencode(
            db_path=db_path,
            output_root=backup_root,
            recipient_file=recipient_file,
        )
    finally:
        writer.close()

    restored = tmp_path / "restored.db"
    result = restore_opencode(
        backup_root=backup_root,
        db_path=restored,
        identity=identity,
    )

    assert result == restored
    with sqlite3.connect(restored) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        rows = connection.execute("SELECT payload FROM event").fetchall()
    assert rows == [("secret-session-event",)]


def test_cli_backup_restore_round_trip(tmp_path: Path) -> None:
    content = b'{"type":"session","payload":"cli-round-trip"}\n'
    codex_home = tmp_path / "codex-home"
    _seed_session(codex_home / "sessions", "rollout-cli.jsonl", content)
    db_path = tmp_path / "opencode.db"
    writer = _seed_opencode_db(db_path)
    identity, recipient_file = _age_recipient_file(tmp_path)
    output_root = tmp_path / "out"
    restored_codex_home = tmp_path / "restored-codex-home"
    restored_db = tmp_path / "restored.db"
    script = REPOSITORY_ROOT / "scripts" / "session_backup.py"

    try:
        subprocess.run(
            [
                sys.executable,
                str(script),
                "backup",
                "--codex-home",
                str(codex_home),
                "--opencode-db",
                str(db_path),
                "--output-root",
                str(output_root),
                "--recipient",
                str(recipient_file),
            ],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(script),
                "restore",
                "--codex-home",
                str(restored_codex_home),
                "--opencode-db",
                str(restored_db),
                "--backup-root",
                str(output_root),
                "--identity-file",
                str(identity),
            ],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        )
    finally:
        writer.close()

    restored_session = (
        restored_codex_home / "sessions" / "2026" / "09" / "26" / "rollout-cli.jsonl"
    )
    assert restored_session.read_bytes() == content

    with sqlite3.connect(restored_db) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        rows = connection.execute("SELECT payload FROM event").fetchall()
    assert rows == [("secret-session-event",)]


def test_taskfile_exposes_session_backup_and_restore() -> None:
    task_bin = shutil.which("task")
    if task_bin is None:
        pytest.skip("task binary is not available")

    result = subprocess.run(
        ["task", "-t", ".config/Taskfile.yml", "--list", "--json"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    names = {task["name"] for task in json.loads(result.stdout)["tasks"]}
    assert {"session:backup", "session:restore"} <= names
