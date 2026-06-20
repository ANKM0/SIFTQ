---
codd:
  node_id: design:codd-foundation
  type: design
  status: draft
  depends_on:
    - id: req:siftq-system
      relation: depends_on
      semantic: governance
  depended_by:
    - id: design:ci-cd-foundation
      relation: depends_on
      semantic: verification
---

# CoDD 基盤設計

SIFTQでは、プロジェクトローカルの`.codd/codd.yaml`でCoDDのscan対象と
検証defaultを定義する。この設計書は、requirements、design、ADR、実装、
testを追跡可能にするためのCoDD基盤を記録する。

## 設定

- 実装root: `src/`
- test root: `tests/`
- document root: `docs/`
- tooling設定: `aqua.yaml`
- graph出力: `.codd/scan`

## 検証

repositoryにapplication source codeが存在しない初期段階では、言語固有の
typecheckやtest commandを設定しない。runtime stackを導入した時点で、
具体的なcommandを`.codd/codd.yaml`に追加する。

## 依存関係管理

developer toolはaquaでinstallする。`codd-dev`を含むPython packageは
`pyproject.toml`で宣言し、uvでinstallする。
