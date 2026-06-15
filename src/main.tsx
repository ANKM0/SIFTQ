import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { createStartupSettingsRepository } from "./bootstrap/settingsRepository";
import { App } from "./ui/App";

const settingsRepository = createStartupSettingsRepository();

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App settingsRepository={settingsRepository} />
  </StrictMode>
);
