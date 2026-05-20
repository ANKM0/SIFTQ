export type MatrixAreaId = "do" | "schedule" | "delegate" | "eliminate";
export type TerminalAreaId = "done" | "skipped";
export type AreaId = MatrixAreaId | TerminalAreaId;

export type AreaRole = AreaId;
export type AreaKind = "matrix" | "terminal";

export type Area = {
  readonly id: AreaId;
  readonly label: string;
  readonly kind: AreaKind;
  readonly role: AreaRole;
};

export const INITIAL_AREAS = [
  { id: "do", label: "Do", kind: "matrix", role: "do" },
  { id: "schedule", label: "Schedule", kind: "matrix", role: "schedule" },
  { id: "delegate", label: "Delegate", kind: "matrix", role: "delegate" },
  { id: "eliminate", label: "Eliminate", kind: "matrix", role: "eliminate" },
  { id: "skipped", label: "Skipped", kind: "terminal", role: "skipped" },
  { id: "done", label: "Done", kind: "terminal", role: "done" }
] as const satisfies readonly Area[];

export const MATRIX_AREAS = INITIAL_AREAS.filter(
  (area) => area.kind === "matrix"
);

export const TERMINAL_AREAS = INITIAL_AREAS.filter(
  (area) => area.kind === "terminal"
);

export function findArea(areaId: AreaId): Area {
  const area = INITIAL_AREAS.find((candidate) => candidate.id === areaId);

  if (area === undefined) {
    throw new Error(`Unknown area: ${areaId}`);
  }

  return area;
}

export function isMatrixArea(areaId: AreaId): areaId is MatrixAreaId {
  return findArea(areaId).kind === "matrix";
}

export function isTerminalArea(areaId: AreaId): areaId is TerminalAreaId {
  return findArea(areaId).kind === "terminal";
}
