# ADR 0033: md2idx は Bun の devDependency として導入する

## 決定

- `md2idx` は `package.json` の `devDependencies` に `^0.3.0` として追加し、`bun.lock` で version を固定する。
- 実行は `bun x md2idx <file> [--pretty]` とし、`md2idx` を PATH に置かない。
- 開発環境への導入は既存の `task setup` -> `setup:frontend` の `bun install` に含め、専用の setup 手順を追加しない。

### 決定の理由

- この repository は ADR 0010 で Bun を package manager と定めており、npm package は devDependency + lockfile で管理するのが既存の依存管理と一致する。
- `bun x` は local の `node_modules/.bin` を参照するため、利用者 global 環境を変更せず、再現可能な実行方法になる。
- 既存の `task setup` がそのまま導入経路になるため、slice 01 の「開発環境で実行できる」を最小変更で満たす。

## 不採用

- aqua で管理する。
  - `md2idx` は npm package であり、aqua standard registry に該当エントリが無い。aqua 側へ npm package の導入方法を追加すると、現在 standalone binary 中心の `aqua.yaml` 運用から外れる。
- `npx md2idx` を都度実行する。
  - 実行のたびに network へ依存し、lockfile で version を固定できない。
- `npm install -g md2idx` で global install する。
  - 利用者 global 環境を変更し、repository の lockfile で再現できない。

## 補足情報

### 背景

- 長い Markdown を読む際に、index を先に取得して必要な section だけ読むため `md2idx` を導入する。
- Issue #243 の slice 01 では、まず「リポジトリの開発環境で md2idx を実行できる」ことだけを確定する。section 取得手順・fallback の文書化は後続 slice で扱う。

### 制約事項

- `package.json` と `bun.lock` の変更は implement step で行う。
- slice 01 の検証は implement step で `bun x md2idx README.md --pretty` を実行し、`index` と `sections` を含む JSON が返ることを確認する。
- 後続 slice で `AGENTS.md` / skill への利用手順と fallback を追加する。

## 参考リンク

- [Issue #243](https://github.com/ANKM0/SIFTQ/issues/243)
- [md2idx - npm](https://www.npmjs.com/package/md2idx)
- [ADR 0010](0010-adopt-vite-plus-and-bun-toolchain.md)
