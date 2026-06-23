## 概要
<!-- この PR で何を解決するのかを 2-3 行で要約してください -->

## 行ったこと
<!-- この PR で実施した変更を箇条書きで記載してください -->

## 行っていないこと (Optional)
<!-- あえて含めなかった内容や後続 PR で対応する内容があれば記載してください -->

## 動作確認結果
<!-- 実行したテスト、lint、手動確認結果を記載してください -->
- ローカルでの確認
- テスト / lint / 手動確認
- UI 変更がある場合は wireframe HTML を更新し、`tests/docs/wireframeContract.test.ts` の確認結果を記載する
- Matrix browser storage の永続化に影響する変更では、browser reload 後の復元結果を記載する

```bash
```

Matrix browser storage manual smoke evidence (browser storage の永続化に影響する場合は必須):

- Browser-only scope note:
  - Tauri WebView reload / F5 and `task tauri:dev` app restart persistence checks are not applicable when the change follows ADR 0018. If stale issue history adds those result lines, mark them N/A instead of leaving them pending.
- Browser reload result:
  - [ ] task title、area、status、order が browser storage から復元される
  - Result / environment / notes:

## 影響範囲
<!-- 影響を受ける画面、API、運用フローなどを記載してください -->

## Rvしてほしい箇所(Optional)
<!-- レビュワーに特に見てほしい観点があれば記載してください -->
