export type InvokeArgs = Record<string, unknown>;

export type Invoke = <T>(
  command: string,
  args?: InvokeArgs
) => Promise<T>;

type TauriInternals = {
  readonly invoke?: <T>(
    command: string,
    args?: InvokeArgs
  ) => Promise<T>;
};

declare global {
  interface Window {
    readonly __TAURI_INTERNALS__?: TauriInternals;
  }
}

export function isTauriRuntimeAvailable(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.__TAURI_INTERNALS__?.invoke === "function"
  );
}

export const tauriInvoke: Invoke = async (command, args) => {
  const invoke =
    typeof window === "undefined" ? undefined : window.__TAURI_INTERNALS__?.invoke;

  if (invoke === undefined) {
    throw new Error("Tauri runtime required.");
  }

  return invoke(command, args);
};
