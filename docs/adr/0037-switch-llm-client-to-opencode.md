# ADR 0037: LLMクライアントをcodexからopencodeに変更する

## 決定

- LLMクライアントをcodexからopencodeに変更する。

### 決定の理由

- opencodeからはcodexサブスクを使えるため、当初の目的である、「codexサブスクと中華LLMを1つの環境で扱う」が達成できるから。
  - 裏付けとしてmuse・deepseekの直呼び動作を確認済みである。
- 既存資産をそのまま使えるため、移行コストが低いから。
  - `.agents/skills/` 配下のskillsと `AGENTS.md` はopencodeがネイティブに読む。
  - それ以外の `.codex/skills/` の2件もfrontmatter有効のため移動のみで使える。

## 不採用

- codex継続
  - サブスクは温存できるが、応答差異・不安定・再試行なしの不満が残る。
- codex以外のCLI
  - サブスクが使えず当初目的を満たさない。

## 補足情報

### 背景

- codexサブスクと中華LLMを1つの環境で扱うことを目的に、codex経由で中華LLMを呼び分け、codex/中華LLMを切り替えて運用していた。
- 上記環境には、モデルによってcodexとのAPI応答が異なり、通信が不安定で止まる・fetchで429/5xxになっても再試行の仕組みがないなどの不満があった。

### 制約事項

- codexの資産(skillsなど)を可能な限りそのままで使いたい

## 参考リンク

- https://opencode.ai/docs/permissions/
- https://opencode.ai/docs/skills/
