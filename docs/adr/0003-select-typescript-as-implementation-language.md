# ADR 0003: 実装言語として、TypeScriptを採用する

## 決定
<!-- 決定事項、採用した内容とその理由を記載 -->

- 実装言語として、TypeScriptを採用する

### 決定の理由
<!-- 決定事項、採用した内容の理由を記載 -->

- React / Vite / TanStack / Cloudflare との相性がよく、MVP の Web UI を最短で作れるため。
- 別プロジェクトで使用したことがあり、学習コストが低いため。
- 今回はAPI中心で、IO boundな処理がネックになると思われるため、
  - CPU boundな処理が得意な言語より開発者体験を取った方がよいと考えたため

## 不採用
<!-- 採用しなかった内容とその理由を記載 -->

- Rust
  - このプロジェクトで重要になるのは、UI 操作の軽さと API 応答であり、CPU bound な重い処理が中心ではないため
- Python
  - Pythonを採用すると、frontendとbackendの2言語を管理する必要があるため
    - Pythonのみでやる方法もあるが成熟していないので今回は考慮しない
  - Cloudflare/TanStack へ寄せる前提では、TypeScript の方が React / Vite / TanStack / Workers との一貫性が高いため
    - Cloudflare Workers は Python もサポートしているが、Python Workers は beta であり、Pyodide により V8 isolate 上で実行されるため
- Go / Kotlin / Java / C 系言語
  - native binary、成熟した server runtime、並行処理、CPU bound 処理で有利になる場合がある。
  - 一方で、現時点で使用経験が薄く、MVP の中心は browser frontend と DnD である。
  - Cloudflare/TanStack へ寄せる前提でも TypeScript の方が実装効率と一貫性が高いため却下。

## 補足情報

### 背景
<!-- 解決する問題の背景やチームの状況などの戦略。 -->

- このプロジェクトは個人利用のためかつ1人開発。そのため、ある程度冒険的な言語選択が可能。
- LLMを使用して開発を実施するため、バグを機械的に検出するために、静的型付け or 型がある動的言語が必要。

### 制約事項
<!-- ライブラリや設計の変更におけるトレードオフやできない事とその理由。 -->

- 制約
  - Web UIの応答速度が最優先。
  - このプロジェクトの特性は、CPU boundな重い処理はほぼなく、実行環境、データストア、ネットワーク距離の影響が大きくなる想定。
  - 上記特性から、ネット環境の影響を軽減するために Cloudflare/TanStackへ移行する予定。その前提で、実装・スタック決めを行う。
- トレードオフ(以下割と根拠なく偏見で記載)
  - Python
    - 学習負担が少ない. (開発者体験: 中)
    - 型のシステムがあまりよくない.
  - TypeScript
    - フロントエンド・バックエンドを1つの言語で実装できる。TanStack / Cloudflare との相性が良い。(開発者体験: 高)
    - CPU bound な処理、ネイティブ統合、単体バイナリ配布、低レベル制御では Rust / Go / Kotlin / Java / C系 などが有利
  - Rust
    - コンパイルが遅いので開発者経験は悪い。ただ、cargoが良き (開発者体験: 中)
    - GCがないので、CPU boundな処理を高速化できる。
  - Go
    - 処理が冗長(開発者体験: 中)
    - コールドスタート、マルチスレッド処理が強かったはず

## 参考リンク
<!-- ADRに関連する情報や参考にした資料へのリンク。 -->

- [コールドスタート/ウォームスタート、メモリ別、言語別のパフォーマンス比較](https://filia-aleks.medium.com/aws-lambda-battle-2021-performance-comparison-for-all-languages-c1b441005fd1)
- [Task Management 要求分析](../requirements/requirements-analysis.md)
- [Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/)
- [Cloudflare Python Workers の実行方式](https://developers.cloudflare.com/workers/languages/python/how-python-workers-work/)
- [TypeScript7で10倍速度が上がる！](https://cx.genech.co.jp/column/20250620)
