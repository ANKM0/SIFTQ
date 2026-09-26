"""Encrypted session backup for the public repository (Issue #571).

Codex sessions are backed up file by file: every ``*.jsonl`` under the Codex
sessions root becomes ``sessions/codex/<YYYY>/<MM>/<DD>/<name>.jsonl.zst.age``.
Opencode sessions are backed up as one consistent SQLite snapshot of
``opencode.db`` (every table, ``event`` included) at
``sessions/opencode/opencode.db.zst.age``. Both are zstd-compressed and
age-encrypted (X25519). The private identity is never read here; only the
recipient public key is tracked.
"""

import argparse
import os
import shutil
import sqlite3
import subprocess
import tempfile
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "sessions"
DEFAULT_RECIPIENT_FILE = REPOSITORY_ROOT / ".taqt" / "session-backup" / "recipient.pub"


def default_identity_file() -> Path:
    return Path.home() / ".config" / "age" / "session.key"


def resolve_identity(env: Mapping[str, str] | None = None) -> Path | str:
    """Resolve the age identity used to decrypt backups.

    ``AGE_IDENTITY_FILE`` (path to a key file) wins over ``AGE_IDENTITY``
    (inline key material), which wins over ``~/.config/age/session.key``.
    A ``Path`` result is a file reference; a ``str`` result is inline material.
    """
    values = os.environ if env is None else env
    identity_file = values.get("AGE_IDENTITY_FILE")
    if identity_file:
        return Path(identity_file)
    identity = values.get("AGE_IDENTITY")
    if identity:
        return identity
    return default_identity_file()


def codex_home() -> Path:
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


def codex_sessions_root(codex_home_dir: Path | None = None) -> Path:
    return (codex_home_dir or codex_home()) / "sessions"


def codex_session_files(sessions_root: Path) -> list[Path]:
    return sorted(path for path in sessions_root.rglob("*.jsonl") if path.is_file())


def codex_backup_path(sessions_root: Path, source: Path, output_root: Path) -> Path:
    relative = source.relative_to(sessions_root)
    return output_root / "codex" / relative.parent / f"{relative.name}.zst.age"


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"{name} is required; run 'task setup:aqua'")
    return path


def compress_encrypt(source: Path, target: Path, recipient_file: Path) -> None:
    zstd = require_tool("zstd")
    age = require_tool("age")
    target.parent.mkdir(parents=True, exist_ok=True)
    compressed = target.with_name(target.name + ".zst.tmp")
    temporary = target.with_name(target.name + ".tmp")
    try:
        subprocess.run(
            [zstd, "-q", "-f", str(source), "-o", str(compressed)],
            check=True,
        )
        subprocess.run(
            [age, "-R", str(recipient_file), "-o", str(temporary), str(compressed)],
            check=True,
        )
        temporary.replace(target)
    finally:
        compressed.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


def backup_codex(
    *,
    sessions_root: Path,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    recipient_file: Path = DEFAULT_RECIPIENT_FILE,
) -> list[Path]:
    if not sessions_root.is_dir():
        raise SystemExit(f"codex sessions root not found: {sessions_root}")
    if not recipient_file.is_file():
        raise SystemExit(f"age recipient file not found: {recipient_file}")

    created: list[Path] = []
    for source in codex_session_files(sessions_root):
        target = codex_backup_path(sessions_root, source, output_root)
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            continue
        compress_encrypt(source, target, recipient_file)
        created.append(target)
    return created


def opencode_data_root(override: Path | None = None) -> Path:
    if override is not None:
        return override
    env = os.environ.get("OPENCODE_DATA_DIR")
    return Path(env) if env else Path.home() / ".local" / "share" / "opencode"


def opencode_db_path(data_root: Path | None = None) -> Path:
    return opencode_data_root(data_root) / "opencode.db"


def opencode_backup_path(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    return output_root / "opencode" / "opencode.db.zst.age"


def snapshot_sqlite(source: Path, target: Path) -> None:
    with closing(sqlite3.connect(source)) as source_conn:
        with closing(sqlite3.connect(target)) as target_conn:
            source_conn.backup(target_conn)


def backup_opencode(
    *,
    db_path: Path,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    recipient_file: Path = DEFAULT_RECIPIENT_FILE,
) -> Path:
    if not db_path.is_file():
        raise SystemExit(f"opencode database not found: {db_path}")
    if not recipient_file.is_file():
        raise SystemExit(f"age recipient file not found: {recipient_file}")

    target = opencode_backup_path(output_root)
    with tempfile.TemporaryDirectory() as temporary_dir:
        snapshot = Path(temporary_dir) / "opencode.db"
        snapshot_sqlite(db_path, snapshot)
        compress_encrypt(snapshot, target, recipient_file)
    return target


def decompress_decrypt(source: Path, target: Path, identity: Path | str) -> None:
    age = require_tool("age")
    zstd = require_tool("zstd")
    target.parent.mkdir(parents=True, exist_ok=True)
    compressed = target.with_name(target.name + ".zst.tmp")
    temporary = target.with_name(target.name + ".tmp")
    temporary_identity: Path | None = None
    try:
        if isinstance(identity, str):
            handle = tempfile.NamedTemporaryFile("w", delete=False)
            handle.write(identity if identity.endswith("\n") else identity + "\n")
            handle.close()
            temporary_identity = Path(handle.name)
            temporary_identity.chmod(0o600)
            identity_path = temporary_identity
        else:
            identity_path = identity
        subprocess.run(
            [age, "-d", "-i", str(identity_path), "-o", str(compressed), str(source)],
            check=True,
        )
        subprocess.run(
            [zstd, "-d", "-q", "-f", str(compressed), "-o", str(temporary)],
            check=True,
        )
        temporary.replace(target)
    finally:
        compressed.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
        if temporary_identity is not None:
            temporary_identity.unlink(missing_ok=True)


def codex_restore_path(backup_root: Path, source: Path, sessions_root: Path) -> Path:
    relative = source.relative_to(backup_root / "codex")
    name = relative.name[: -len(".zst.age")]
    return sessions_root / relative.parent / name


def restore_codex(
    *,
    backup_root: Path = DEFAULT_OUTPUT_ROOT,
    sessions_root: Path,
    identity: Path | str,
) -> list[Path]:
    archives = sorted((backup_root / "codex").rglob("*.zst.age"))
    restored: list[Path] = []
    for archive in archives:
        if not archive.is_file():
            continue
        target = codex_restore_path(backup_root, archive, sessions_root)
        decompress_decrypt(archive, target, identity)
        restored.append(target)
    return restored


def restore_opencode(
    *,
    backup_root: Path = DEFAULT_OUTPUT_ROOT,
    db_path: Path,
    identity: Path | str,
) -> Path:
    archive = opencode_backup_path(backup_root)
    if not archive.is_file():
        raise SystemExit(f"opencode backup not found: {archive}")
    decompress_decrypt(archive, db_path, identity)
    return db_path


def add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--sessions-root", type=Path)
    parser.add_argument("--opencode-db", type=Path)
    parser.add_argument(
        "--only",
        choices=("codex", "opencode", "all"),
        default="all",
        help="Limit the command to one session source (default: all).",
    )


def run_backup(args: argparse.Namespace) -> int:
    if args.only in ("codex", "all"):
        sessions_root = args.sessions_root or codex_sessions_root(args.codex_home)
        for path in backup_codex(
            sessions_root=sessions_root,
            output_root=args.output_root,
            recipient_file=args.recipient,
        ):
            print(path)
    if args.only in ("opencode", "all"):
        db_path = args.opencode_db or opencode_db_path()
        print(
            backup_opencode(
                db_path=db_path,
                output_root=args.output_root,
                recipient_file=args.recipient,
            )
        )
    return 0


def run_restore(args: argparse.Namespace) -> int:
    identity: Path | str
    if args.identity_file is not None:
        identity = args.identity_file
    elif args.identity is not None:
        identity = args.identity
    else:
        identity = resolve_identity()
    if args.only in ("codex", "all"):
        sessions_root = args.sessions_root or codex_sessions_root(args.codex_home)
        for path in restore_codex(
            backup_root=args.backup_root,
            sessions_root=sessions_root,
            identity=identity,
        ):
            print(path)
    if args.only in ("opencode", "all"):
        print(
            restore_opencode(
                backup_root=args.backup_root,
                db_path=args.opencode_db or opencode_db_path(),
                identity=identity,
            )
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="Encrypt sessions into the backup root.")
    add_target_arguments(backup)
    backup.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    backup.add_argument("--recipient", type=Path, default=DEFAULT_RECIPIENT_FILE)
    backup.set_defaults(handler=run_backup)

    restore = subparsers.add_parser(
        "restore", help="Decrypt backups from the backup root."
    )
    add_target_arguments(restore)
    restore.add_argument("--backup-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    restore.add_argument("--identity-file", type=Path)
    restore.add_argument("--identity")
    restore.set_defaults(handler=run_restore)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
