# Release

Release はリポジトリ変更の配布単位であり、Cloudflare Workers デプロイとは別に判断する。基準は [ADR 0034](../adr/0034-separate-release-and-worker-deployment.md) に従う。

## 対象の判断

- Worker 実行成果物、D1 migration、本番 secrets・設定に影響する変更は Release と Worker デプロイを行う。
- taqt、開発環境、CI、文書のみの変更は Release-only とし、Worker をデプロイしない。
- 複数の変更を一つの Release にまとめられる。Release Notes に含めた変更と対象 SHA を記録する。

## バージョン

`0.x` では次を基準にする。

- patch: バグ修正、本来の挙動の補完、利用者に新しい操作を要求しない修正。
- minor: 後方互換な利用者向け新機能。

## 手順

1. Release に含める SHA、変更一覧、Worker・migration・本番設定への影響を確認する。
2. 対象 SHA を checkout した clean な専用 worktree を用意する。
3. CI を確認し、D1 migration がある場合は remote の適用状況を確認する。
4. 対象 SHA にタグを固定し、GitHub Release を作成する。
5. デプロイ対象なら、同じタグの worktree から [デプロイ手順](deployment.md) を実行する。Release-only なら Worker をデプロイしない。
6. Release Notes に対象 SHA、デプロイ有無、migration の実施・確認、本番スモーク結果を記録する。

## Task コマンド

- `task release:plan -- --version vX.Y.Z --ref <sha> --base <tag>` は候補を読み取り専用で分類する。
- `task release:version -- --version vX.Y.Z --execute` は `package.json` の version を更新する。差分を確認して release commit に含める。
- `task release:create -- --version vX.Y.Z --ref HEAD --execute` は version 一致済みの clean worktree を注釈付きタグとして push する。
- Worker デプロイは、タグを checkout した worktree で `task deploy:release -- --tag vX.Y.Z --execute` を実行する。

`--execute` を付けない操作は外部状態を変更しない。タグ push、remote migration、Worker デプロイの直前には明示承認を得る。

## 本番確認

デプロイ対象では、未認証時のログイン画面、ログイン後の主要な作成・更新操作、DnD を確認する。認証情報が必要な確認は、認証可能な担当者が実施結果を Release Notes に記録する。
