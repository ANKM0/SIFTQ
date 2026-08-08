# SIFTQ Issue Templates

Do not duplicate issue templates here.

See `docs/contributing/issue.md`. Use `.github/ISSUE_TEMPLATE/*.md` through
`scripts/create_issue.py`.

```bash
uv run python scripts/create_issue.py --type feature --title "..." --dry-run
```

Drafted body: `--body-source <path>`.

Skill decides and drafts. Script reads template, writes body file, builds labels,
rejects forbidden taqt labels, and prints or runs `gh issue create --body-file`.
