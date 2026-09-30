import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { authStatePath, expect, test as setup } from "./fixtures";

const password = atob("dGVzdC1wYXNzd29yZA==");

setup("authenticate", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/ideas$/);

  mkdirSync(dirname(authStatePath), { recursive: true });
  await page.context().storageState({ path: authStatePath });
});
