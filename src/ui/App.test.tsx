import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { App } from "./App";

afterEach(() => {
  cleanup();
});

describe("App", () => {
  it("renders the matrix quadrants", () => {
    render(<App />);

    expect(screen.getByText("Do")).toBeTruthy();
    expect(screen.getByText("Schedule")).toBeTruthy();
    expect(screen.getByText("Delegate")).toBeTruthy();
    expect(screen.getByText("Eliminate")).toBeTruthy();
  });

  it("renders the terminal drop areas", () => {
    render(<App />);

    expect(screen.getByText("Skipped")).toBeTruthy();
    expect(screen.getByText("Done")).toBeTruthy();
  });
});
