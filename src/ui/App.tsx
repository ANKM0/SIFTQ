const quadrants = ["Do", "Decide", "Delegate", "Delete"] as const;

export function App() {
  return (
    <main>
      <h1>SIFTQ</h1>
      <section aria-label="Task matrix">
        {quadrants.map((quadrant) => (
          <article key={quadrant}>
            <h2>{quadrant}</h2>
          </article>
        ))}
      </section>
    </main>
  );
}
