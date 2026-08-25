/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-circular",
      severity: "error",
      comment: "src 内の循環依存を禁止する。",
      from: { path: "^src" },
      to: { path: "^src", circular: true },
    },
    {
      name: "src-not-to-tests",
      severity: "error",
      comment: "src は tests レイヤーへ依存しない。",
      from: { path: "^src" },
      to: { path: "^tests" },
    },
    {
      name: "domain-no-upward-dependency",
      severity: "error",
      comment: "domain は presentation / repository へ依存しない。",
      from: { path: "^src/task\\.ts$" },
      to: { path: "^src/(index|task-repository)\\." },
    },
    {
      name: "repository-no-presentation-dependency",
      severity: "error",
      comment: "repository は presentation へ依存しない。",
      from: { path: "^src/task-repository\\.ts$" },
      to: { path: "^src/index\\." },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsPreCompilationDeps: true,
    tsConfig: { fileName: "tsconfig.json" },
  },
};
