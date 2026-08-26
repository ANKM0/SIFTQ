import type { FC } from "hono/jsx";

export const OptionMenu: FC<{
  title: string;
  values: readonly (string | number)[];
  postPath: string;
  valueKey: string;
  cancelPath: string;
  version: number;
}> = ({ title, values, postPath, valueKey, cancelPath, version }) => (
  <aside id="task-meta">
    <p class="menu-title">{title}</p>
    {values.map((value) => (
      <button
        key={String(value)}
        class="menu-option"
        type="button"
        hx-post={postPath}
        hx-vals={JSON.stringify({ [valueKey]: value, version })}
        hx-target="#task-meta"
        hx-swap="innerHTML"
      >
        {value}
      </button>
    ))}
    <a href={cancelPath}>Cancel</a>
  </aside>
);
