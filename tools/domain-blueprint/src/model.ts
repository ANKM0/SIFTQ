export type Domain = { kind: string; logical?: string; values?: (string | number)[] };
export type Attribute = { domain: string; pk?: boolean; note?: string; rules?: string[] };
export type Transition = { on: string; domain?: string; from: string | string[]; to: string };
export type Entity = {
  description?: string;
  table?: string;
  attributes: Record<string, Attribute>;
  transitions?: Transition[];
  rules?: string[];
};
export type Relation = { from: string; to: string; kind: string; on?: string };
export type Step = {
  name: string;
  entity?: string;
  changes?: Record<string, string | number | boolean | (string | number | boolean)[]>;
  when?: string;
};
export type Flow = { name: string; actor?: string; steps: Step[] };
export type Screen = { name: string; entities: string[]; onLoad?: string; references?: string[]; actions?: string[] };
export type NavigationItem = { from: string; on: string; to: string; call?: string };
export type ScreenCall = { screen: string; trigger: "GET" | "POST"; view: string; gateway: string; api: string };
export type ApiError = { status: number; code?: string };
export type ApiOperation = {
  kind: string;
  method: string;
  path: string;
  operation: string;
  entity?: string;
  entities?: string[];
  references?: string[];
  consumer?: string;
  external?: boolean;
  success: number;
  errors?: ApiError[];
};
export type PersistedColumn = {
  attribute: string;
  type: string;
  logicalType: string;
  nullable: boolean;
  primaryKey: boolean;
  unique: boolean;
  references?: string;
  onDelete?: string;
};
export type Persistence = {
  source: string;
  alembicHead?: string;
  tables: Record<string, { name: string; columns: Record<string, PersistedColumn>; uniqueGroups?: string[][] }>;
};
export type Model = {
  domains: Record<string, Domain>;
  entities: Record<string, Entity>;
  relations?: Relation[];
  flows?: Record<string, Flow>;
  screens?: Record<string, Screen>;
  navigation?: NavigationItem[];
  screenCalls?: ScreenCall[];
  api?: Record<string, ApiOperation>;
  persistence?: Persistence;
};

export type ValidateFn = (model: unknown, schema: object) => string[];
