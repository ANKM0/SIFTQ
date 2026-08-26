import { describe, expect, it } from "vite-plus/test";
import {
  TASK_TITLE_MAX_CODE_POINTS,
  isTaskArea,
  isTaskStatus,
  isTaskTitleValid,
  titleCodePointLength,
} from "../src/task";

describe("task title validation", () => {
  it("counts Unicode code points", () => {
    expect(titleCodePointLength("a😀")).toBe(2);
  });

  it("accepts 1 to 256 Unicode code points", () => {
    expect(isTaskTitleValid("a")).toBe(true);
    expect(isTaskTitleValid("a".repeat(TASK_TITLE_MAX_CODE_POINTS))).toBe(true);
    expect(isTaskTitleValid("😀".repeat(TASK_TITLE_MAX_CODE_POINTS))).toBe(true);

    expect(isTaskTitleValid("")).toBe(false);
    expect(isTaskTitleValid("a".repeat(TASK_TITLE_MAX_CODE_POINTS + 1))).toBe(false);
    expect(isTaskTitleValid("😀".repeat(TASK_TITLE_MAX_CODE_POINTS + 1))).toBe(false);
  });
});

describe("task enums", () => {
  it("recognizes valid status and area values", () => {
    expect(isTaskStatus("do")).toBe(true);
    expect(isTaskStatus("done")).toBe(true);
    expect(isTaskStatus("skip")).toBe(true);
    expect(isTaskStatus("unknown")).toBe(false);

    expect(isTaskArea(1)).toBe(true);
    expect(isTaskArea(4)).toBe(true);
    expect(isTaskArea(0)).toBe(false);
    expect(isTaskArea(5)).toBe(false);
  });
});
