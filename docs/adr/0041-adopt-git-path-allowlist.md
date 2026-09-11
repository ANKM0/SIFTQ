# ADR 0041: Git の untracked ファイルを deny-by-default の path allowlist で管理する

## 決定

- セキュリティ上の理由から、Git の追跡対象を個別に除外するdeny-list方式から、追跡を許可するパスを明示する allowlist 方式へ変更する。

### 決定の理由

- allowlist により、明示的に追跡対象を指定できるため。

## 不採用

- 個別の deny-list を維持する方式
  - 新しいローカル生成物やエージェント用ファイルを ignore し忘れる余地が残るため。
- 拡張子だけで許可する方式
  - 許可された拡張子の秘密情報や生成物まで許可する可能性があり、path 単位の境界を表現できないため。
- `.learnings/`、`.agents/`、`.codex/` をまとめて ignore する方式
  - 共有成果物や開発環境の正本を Git の追跡対象から外すため。

## 補足情報

### 背景

gitの指定がdeny-list方式のため意図しないファイルがコミットされる恐れがあった

### 制約事項

- `.gitignore` は既に追跡済みのファイルには適用されないため、既存の秘密情報や履歴の除去はこの ADR の対象外とする。
- `git add -f` などの強制操作は `.gitignore` で禁止できないため、別の権限制御や CI 検査が必要な場合は別途判断する。
- 新しい共有成果物を追加する場合は、`.gitignore` の allowlist と対応する検証を同時に更新する。
- 親ディレクトリを許可しないと Git が配下を評価できないため、allowlist の順序と親ディレクトリの再許可を検証する。

## 参考リンク

- [記事: .gitignore everything by default](https://packagemain.tech/p/gitignore-everything-by-default)
