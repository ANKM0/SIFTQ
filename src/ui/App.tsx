import { MATRIX_AREAS, TERMINAL_AREAS } from "../domain/area";

export function App() {
  return (
    <main>
      <h1>SIFTQ</h1>
      <section aria-label="Task matrix">
        {MATRIX_AREAS.map((area) => (
          <article key={area.id}>
            <h2>{area.label}</h2>
          </article>
        ))}
      </section>
      <section aria-label="Task status drop areas">
        {TERMINAL_AREAS.map((area) => (
          <article key={area.id}>
            <h2>{area.label}</h2>
          </article>
        ))}
      </section>
    </main>
  );
}
