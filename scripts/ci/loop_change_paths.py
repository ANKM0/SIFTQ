PREFIXES = (".taqt/loops/", ".taqt/scripts/loop/")


def is_loop_change_path(path: str) -> bool:
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:].strip()
    return normalized.startswith(PREFIXES)
