# セッションの暗号化バックアップと復元

Codex と opencode の会話セッションを公開リポジトリへ保存する手順を定める。判断の理由は [ADR 0069](../adr/0069-encrypt-session-backup-with-age.md) に従う。

## 方針

- セッションはクライアント側で zstd 圧縮してから age（X25519）で暗号化し、`sessions/` 配下へ出力する。
- 秘密鍵はリポジトリ外に置き、追跡するのは recipient 公開鍵だけにする。
- バックアップと復元は自動化せず、必要なタイミングで手動実行する。
- 暗号文は git 履歴へ永続する。日付・ファイル名・サイズなどのメタデータは公開される。

## 鍵管理

バックアップに使う age 鍵ペアを 1 組用意する。

```bash
mkdir -p ~/.config/age
age-keygen -o ~/.config/age/session.key
chmod 600 ~/.config/age/session.key
age-keygen -y ~/.config/age/session.key > .taqt/session-backup/recipient.pub
```

- 秘密鍵 `~/.config/age/session.key` はリポジトリ外に置き、`.gitignore` により追跡しない。
- 追跡するのは `.taqt/session-backup/recipient.pub`（recipient 公開鍵）だけとする。
- 秘密鍵はパスワードマネージャなど別経路でも保管する。失うと履歴を復元できない。
- 鍵を替えると以前のアーカイブとは別の identity になる。切り替えは既存履歴の扱いを決めてから行う。

## 復号鍵の注入

復号に使う identity は次の優先順で解決する。

1. `AGE_IDENTITY_FILE`: 鍵ファイルのパス。
2. `AGE_IDENTITY`: 鍵素材そのもの。
3. 既定の `~/.config/age/session.key`。

通常は鍵ファイルを指定する。

```bash
export AGE_IDENTITY_FILE=~/.config/age/session.key
```

秘密鍵の内容をログや実行記録へ残さない。CI へ復号鍵を供給しない。

## バックアップ

```bash
task -t .config/Taskfile.yml session:backup
```

- Codex の `*.jsonl` を 1 ファイルずつ `sessions/codex/<YYYY>/<MM>/<DD>/<name>.jsonl.zst.age` へ保存する。
- opencode の `opencode.db` を整合性のあるスナップショットとして `sessions/opencode/opencode.db.zst.age` へ保存する。
- 入力が変わっていないアーカイブは再作成しない。
- 対象を限定する場合は `task -t .config/Taskfile.yml session:backup -- --only codex` のように `--only` を渡す。

## `event` 包含範囲

opencode の標準 export には `event` テーブルが含まれない。そのためバックアップは `opencode.db` 全体のスナップショットを採用し、`event` を含む全テーブルを保存する。codex は元の `*.jsonl` をそのまま保存する。

## 復元

```bash
task -t .config/Taskfile.yml session:restore
```

- Codex は `sessions/codex/` を展開して元のディレクトリ構成へ戻す。
- opencode は `sessions/opencode/opencode.db.zst.age` を `opencode.db` へ戻す。
- 対象を限定する場合は `--only` を渡す。復元先を変える場合は `--sessions-root` や `--opencode-db` を指定する。
- 復元後に opencode の DB は `PRAGMA integrity_check` が `ok` になることを確認する。

```bash
sqlite3 ~/.local/share/opencode/opencode.db 'PRAGMA integrity_check;'
```

## 初回サイズと増加

- 初回のバックアップは codex 約 76MB と opencode 約 130–150MB を合わせて約 200–230MB になる見込み。
- 以降の増加量はバックアップ頻度に比例する。実行頻度をそのままリポジトリ増加量として扱う。

## 履歴永続の限界

- 一度 push した暗号文は git 履歴に残り、削除しても履歴から取り消しにくい。
- 公開されるのは暗号文とメタデータ（日付・ファイル名・サイズ）である。内容は復号鍵がない限り読めない。
- 秘匿性は鍵保管に依存する。鍵のローテーションと別経路バックアップを維持する。
