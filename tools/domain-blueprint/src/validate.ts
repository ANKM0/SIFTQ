import Ajv from "ajv";

export function validate(model: unknown, schema: object): string[] {
  const ajv = new Ajv({ allErrors: true, allowUnionTypes: true });
  const check = ajv.compile(schema);
  if (check(model)) return [];
  return (check.errors ?? []).map((e) => `${e.instancePath || "/"} ${e.message ?? ""}`.trim());
}
