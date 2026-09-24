import type { Idea } from "../idea";

type PreviewIdea = Idea & { pinned: boolean };

export const PREVIEW_IDEAS: readonly PreviewIdea[] = [
  {
    id: "1",
    owner_id: "local",
    title: "毎朝の振り返りを1分で終える",
    description: "昨日できたことを一つだけ記録する習慣を試す。",
    order: 1,
    pinned: true,
  },
  {
    id: "2",
    owner_id: "local",
    title: "あとで読みたい記事を集める",
    description: "読みたい理由も一緒に残せるIdeasカードを作る。",
    order: 2,
    pinned: false,
  },
  {
    id: "3",
    owner_id: "local",
    title: "週末の小さな実験を記録する",
    description: "結果ではなく、試してみたいことを気軽に書き留める。",
    order: 3,
    pinned: false,
  },
  {
    id: "4",
    owner_id: "local",
    title: "朝の集中時間を守る仕組み",
    description: "最初の30分だけ通知を切って、考える時間を確保する。",
    order: 4,
    pinned: true,
  },
  {
    id: "5",
    owner_id: "local",
    title: "チームの小さな成功を残す",
    description: "週末に一つだけ、うまくいった工夫を振り返る。",
    order: 5,
    pinned: false,
  },
  {
    id: "6",
    owner_id: "local",
    title: "読み返したいメモの整理方法",
    description: "あとから探しやすい名前と短い要約を残しておく。",
    order: 6,
    pinned: false,
  },
  {
    id: "7",
    owner_id: "local",
    title: "新しい道具を試す日",
    description: "気になっていた道具を一つだけ選んで触ってみる。",
    order: 7,
    pinned: true,
  },
  {
    id: "8",
    owner_id: "local",
    title: "今月やめてよかったこと",
    description: "続けなくても困らなかった習慣をメモする。",
    order: 8,
    pinned: false,
  },
  {
    id: "9",
    owner_id: "local",
    title: "次の旅行で試したいこと",
    description: "場所ではなく、そこでやりたい小さな体験を書く。",
    order: 9,
    pinned: false,
  },
  {
    id: "10",
    owner_id: "local",
    title: "毎週ひとつ質問を残す",
    description: "答えを急がず、考え続けたい問いを集める。",
    order: 10,
    pinned: true,
  },
  {
    id: "11",
    owner_id: "local",
    title: "資産の種類と共通点",
    description: `金融資産
- 株式・債券・不動産など。
- 資本そのものが収益を生み、自分の労働時間から切り離せる。

ソフトウェア / プロダクト
- SaaS、アプリ、ツールなど。
- 一度作ったものを限界費用を低くして多数へ提供できる。

コンテンツ / 知的資産
- YouTube、記事、書籍、教材、データベースなど。
- 過去に作ったものが継続的に閲覧・販売される。

Distribution（販路）
- SEO、SNS、メルマガ、顧客リストなど。
- 「作ったものを継続的に人へ届けられる経路」そのものが資産になる。

ブランド / 信用
- 指名、評判、専門性への認知など。
- 蓄積するほど次の商品・サービスを売りやすくなる。

コミュニティ / ネットワーク
- 人と人の関係そのものが価値を生む。
- 自分だけが価値提供者ではない構造を作れる。

組織 / 仕組み
- 従業員、外注、AI、自動化、標準化された業務プロセスなど。
- 他者・システムによって価値提供を複製できる。

共通するのは、「自分の1時間を1回売って終わり」ではなく、資本・コード・情報・販路・信用・人・仕組みのいずれかを蓄積し、将来も働かせること。`,
    order: 11,
    pinned: false,
  },
];
