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

v1のマトリックスUI検証後、Yoriwakeはローカルアプリケーションへ発展する
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

## Consequences

- 後続マイルストーンで、GUIとCLIの振る舞いをRust application logicで
  共有できる。
- SQLiteとGitHub integrationをbrowser sandboxの外側で実装できる。
- v1 SPAは、target architectureより意図的に狭い範囲に留める。
- v1 frontendでは、Tauri migrationを難しくする前提を避ける。
