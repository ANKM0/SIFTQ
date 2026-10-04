import { bindings, defineConfig } from "cf/config";

export default defineConfig({
	worker: {
		name: "app",
		compatibilityDate: "2025-06-01",
		entrypoint: "./src/index.tsx",
		env: {
			DB: bindings.d1({
				name: "siftq",
				id: "20ca1496-cadc-4b40-9265-1d59d55d5b82",
			}),
			AUTH_PASSWORD: bindings.secret(),
			SESSION_SECRET: bindings.secret(),
			PREVIEW_MODE: bindings.text(process.env["PREVIEW_MODE"] ?? "false"),
		},
	},
});
