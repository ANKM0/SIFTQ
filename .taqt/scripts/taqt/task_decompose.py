import argparse
from pathlib import Path

from loop.schema import write_document

from .task_store import (
    DEFAULT_SLICE_MINUTES,
    DEFAULT_TASK_ROOT,
    build_slice_task,
    decompose_issue_body,
    load_task,
    list_tasks,
    save_task,
    slice_task_id,
    task_path,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-task-decompose")
    parser.add_argument("task", nargs="?")
    parser.add_argument("--task-root", type=Path, default=DEFAULT_TASK_ROOT)
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--max-minutes", type=int, default=DEFAULT_SLICE_MINUTES)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    selected = [load_task(args.task, args.task_root)] if args.task else list_tasks(args.task_root)
    planned = 0
    for parent_path, parent in selected:
        if parent.get("slice"):
            continue
        slices = decompose_issue_body(parent, workspace=args.workspace, max_minutes=args.max_minutes)
        if len(slices) <= 1:
            print(f"{parent['id']}: already 1 slice or less")
            continue

        child_ids = [slice_task_id(parent, index) for index in range(1, len(slices) + 1)]
        print(f"{parent['id']}: decompose into {len(slices)} slices capped at {args.max_minutes} minutes")
        for child_id, slice_item in zip(child_ids, slices, strict=True):
            print(f"  {child_id}: {slice_item['title']}")
        planned += 1
        if not args.execute:
            continue

        for index, slice_item in enumerate(slices, start=1):
            child = build_slice_task(parent, slice_item, index=index, total=len(slices))
            write_document(task_path(str(child["id"]), args.task_root), child)
        parent["phase"] = "decomposed"
        parent["plan"] = {
            "max_slice_minutes": args.max_minutes,
            "slices": [
                {
                    "task_id": child_id,
                    "title": slice_item["title"],
                    "source_section": slice_item["source_section"],
                    "estimate_minutes": slice_item["estimate_minutes"],
                }
                for child_id, slice_item in zip(child_ids, slices, strict=True)
            ],
        }
        parent["blocked_reason"] = None
        save_task(parent_path, parent)

    if planned == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
