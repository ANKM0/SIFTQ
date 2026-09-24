from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TASK_ROOT = Path(".taqt/tasks")
DEFAULT_WORKTREE_ROOT = REPOSITORY_ROOT / "tmp" / "worktrees"
DEFAULT_SLICE_MINUTES = 5
PRIORITY_ORDER = {"high": 0, "normal": 1, "low": 2}
FEATURE_REQUIRED_SECTIONS = {
    "AC": ("ac", "acceptance criteria", "受け入れ条件", "受入条件"),
    "DoD": ("dod", "definition of done", "完了の定義"),
}
RESEARCH_REQUIRED_SECTIONS = {
    "調べたいこと": ("調べたいこと", "research questions"),
    "完了条件": ("完了条件", "completion criteria", "done criteria"),
}
BUG_REQUIRED_SECTIONS = {
    "概要": ("概要", "summary"),
}
BUG_WARNING_SECTIONS = {
    "再現手順": ("再現手順", "steps to reproduce", "reproduction"),
}
DECOMPOSITION_SECTION_GROUPS = (
    ("AC", FEATURE_REQUIRED_SECTIONS["AC"]),
    ("task", ("task", "tasks", "todo", "やること")),
    ("調べたいこと", RESEARCH_REQUIRED_SECTIONS["調べたいこと"]),
    ("再現手順", BUG_WARNING_SECTIONS["再現手順"]),
    ("概要", BUG_REQUIRED_SECTIONS["概要"]),
)
