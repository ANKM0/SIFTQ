---
codd:
  node_id: design:rust-tauri-v2-local-application-adr
  type: design
  status: draft
  depends_on:
    - id: req:matrix-mvp-functional
      relation: depends_on
      semantic: target-architecture
    - id: req:matrix-mvp-non-functional
      relation: depends_on
      semantic: target-architecture
  depended_by:
    - id: design:issue-6-matrix-mvp-tech-selection
      relation: depends_on
      semantic: decision
---

# ADR 0003: Rust and Tauri for v2 Local Application

## Status

Accepted.

## Context

v1のマトリックスUI検証後、SIFTQはローカルアプリケーションへ発展する
想定である。後続のアプリケーションでは、GUIとCLIのインターフェース、
local database storage、GitHub integrationを扱う必要がある。これらの要件は、
複数のinterfaceから利用でき、browser-only runtimeに依存しないshared core
と相性がよい。

## Decision

v2 MVP以降のローカルアプリケーション作業では、RustとTauriをtarget
architectureとして使用する。

Rustは、shared application behavior、infrastructure integrations、将来の
CLI supportを担う優先言語とする。Tauriは、browser-only UI validationを
越えた段階でGUIのdesktop shellとして優先する。

Tauriを選ぶ理由は、v1のReact frontendを活かしながら、Rustでlocal database、
filesystem、credential storage、GitHub synchronization、CLI shared coreを
実装できるためである。Electronと比べると、TauriはOS native webviewとRust
backendを前提にでき、配布size、memory usage、startup overheadを小さく保つ
方向に寄せやすい。

このprojectは個人開発であり、実装支援にはLLMを前提にできる。そのため、
frontend、backend、CLIをすべてTypeScriptで統一することによる開発体験上の
利点は、team developmentほど大きく見積もらない。加えて、Tauri commandや
IPC、database schema、API responseなどの境界では、TypeScriptだけで統一しても
型定義や変換層を完全には避けられない。

## Alternatives Considered

- TypeScript backendは、静的型付けと小規模local applicationに十分な実行速度を
  提供できる。frontendとlanguageを揃えられる点も利点である。一方で、Node.js、
  Bun、Denoなどのruntimeをlocal appに同梱または前提化する必要があり、Tauriの
  Rust command modelとの境界も増える。処理速度だけを理由にRustが常に必要な
  わけではないが、local app core、CLI、SQLite、filesystem、credential storageを
  一つのnative coreに寄せる方針ではRustを優先する。
- Electronは、TypeScript backendとnpm ecosystemを活かしやすく、Chromiumを
  同梱するためrendering behaviorも揃えやすい。一方で、ChromiumとNode.jsを
  appごとに含めるため、配布size、memory usage、startup overheadが増えやすい。
  SIFTQでは軽量なlocal appを重視するため、Electronは優先しない。
- Neutralinojsは、JavaScript frontendで軽量なdesktop appを作る選択肢である。
  ただし、Rust core、Tauri plugin ecosystem、Rust command modelを利用する
  方針とは合いにくく、native integrationの設計を別途組み立てる必要がある。
- Wailsは、Go backendとweb frontendでlocal appを作る選択肢である。Goを採用する
  強い理由がある場合は有力だが、このprojectではTypeScript frontendとRust/Tauri
  の比較が中心であり、追加でGo ecosystemを導入する理由は薄い。
- Flutterやnative UIは、web frontendを使わないlocal appとして有力である。
  ただし、v1で検証するReact frontendを活かしにくく、UI実装を作り直すcostが
  大きいため選ばない。

## Consequences

- 後続マイルストーンで、GUIとCLIの振る舞いをRust application logicで
  共有できる。
- SQLiteとGitHub integrationをbrowser sandboxの外側で実装できる。
- v1 SPAは、target architectureより意図的に狭い範囲に留める。
- v1 frontendでは、Tauri migrationを難しくする前提を避ける。
