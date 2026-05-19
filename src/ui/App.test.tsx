import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the matrix quadrants", () => {
    render(<App />);

    expect(screen.getByText("Do")).toBeTruthy();
    expect(screen.getByText("Decide")).toBeTruthy();
    expect(screen.getByText("Delegate")).toBeTruthy();
    expect(screen.getByText("Delete")).toBeTruthy();
  });
});
