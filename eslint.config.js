import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import sonarjs from "eslint-plugin-sonarjs";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage", "report", "target", "tmp"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  sonarjs.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/consistent-type-assertions": [
        "error",
        { assertionStyle: "never" }
      ],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-non-null-assertion": "error",
      complexity: ["error", 15],
      "max-depth": ["error", 4],
      "max-lines-per-function": [
        "error",
        { max: 60, skipBlankLines: true, skipComments: true }
      ],
      "max-nested-callbacks": ["error", 4],
      "max-params": ["error", 6],
      "react-refresh/only-export-components": [
        "error",
        { allowConstantExport: true }
      ],
      "sonarjs/cognitive-complexity": ["error", 15],
      "sonarjs/no-ignored-exceptions": "error"
    }
  }
);
