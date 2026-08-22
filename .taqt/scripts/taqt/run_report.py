import argparse
from pathlib import Path
from typing import Any

from loop.state import load_events, load_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taqt-run-report")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)

    state = load_state(args.run_dir)
    if state is None:
        print(f"No state.json found in {args.run_dir}")
        return 1
    events = load_events(args.run_dir)
    print(render_report(state, events))
    return 0


def render_report(state: dict[str, Any], events: list[dict[str, Any]]) -> str:
    lines = [
        f"# taqt run {state.get('task_id')}",
        "",
        f"- status: `{state.get('status')}`",
        f"- current step: `{state.get('current_step')}`",
        f"- iteration: `{state.get('iteration')}`",
        f"- last feedback: `{state.get('last_feedback')}`",
    ]
    if state.get("blocked_reason"):
        lines.append(f"- blocked reason: `{state.get('blocked_reason')}`")
    lines.extend(["", "## Recent events"])
    for event in events[-10:]:
        lines.append(_event_line(event))
    return "\n".join(lines) + "\n"


def _event_line(event: dict[str, Any]) -> str:
    event_type = event.get("type")
    if event_type == "observation":
        observation = event.get("observation", {})
        return (
            f"- observation `{event.get('step')}`: "
            f"{observation.get('status')} / {observation.get('feedback')}"
        )
    if event_type == "decision":
        return (
            f"- decision `{event.get('step')}`: "
            f"{event.get('feedback')} -> {event.get('next')}"
        )
    if event_type == "agent_response":
        response = event.get("response", {})
        return (
            f"- agent `{event.get('step')}`: "
            f"{response.get('status')} ({response.get('mode')})"
        )
    if event_type == "design_artifact":
        artifact_path = event.get("artifact_path")
        return (
            f"- design artifact `{event.get('step')}`: "
            f"[{artifact_path}]({artifact_path}) "
            f"({event.get('status')}) / {event.get('summary')}"
        )
    if event_type == "terminal":
        return f"- terminal `{event.get('step')}`"
    return f"- {event_type}: `{event.get('step') or event.get('reason')}`"


if __name__ == "__main__":
    raise SystemExit(main())
