import argparse
import subprocess
from pathlib import Path

VERSION_PLACEHOLDER = "vX.Y.Z"
REF_PLACEHOLDER = "<sha>"
BASE_PLACEHOLDER = "<tag>"


def build_plan_command(*, version: str, ref: str, base: str) -> list[str]:
    return [
        "task",
        "release:plan",
        "--",
        "--version",
        version,
        "--ref",
        ref,
        "--base",
        base,
    ]


def decision_checklist() -> str:
    return (
        "ADR 0034: Worker成果物・D1 migration・本番設定変更あり=Release+deploy、それ以外=Release-only。\n"
        "Release-onlyではWorkerをデプロイしない。\n"
        "タグpush・remote migration・Workerデプロイは明示承認なしに実行しない。\n"
        "判断結果（対象SHA・デプロイ有無・migration確認方針）をRelease Notes記録方針に沿って残す。"
    )


def render_reminder(*, version: str, ref: str, base: str) -> str:
    command = " ".join(build_plan_command(version=version, ref=ref, base=base))
    return f"{command}\n{decision_checklist()}"


def is_concrete(*, version: str, ref: str, base: str) -> bool:
    return version not in (VERSION_PLACEHOLDER, "") and ref != REF_PLACEHOLDER and base != BASE_PLACEHOLDER


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-release-decision")
    parser.add_argument("task", nargs="?")
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--version", default=VERSION_PLACEHOLDER)
    parser.add_argument("--ref", default=REF_PLACEHOLDER)
    parser.add_argument("--base", default=BASE_PLACEHOLDER)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    print(render_reminder(version=args.version, ref=args.ref, base=args.base))
    if not args.execute or not is_concrete(version=args.version, ref=args.ref, base=args.base):
        return 0
    completed = subprocess.run(
        build_plan_command(version=args.version, ref=args.ref, base=args.base),
        cwd=args.workspace,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
