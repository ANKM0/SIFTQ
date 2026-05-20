import { useEffect, useRef, useState } from "react";

import { InMemoryTaskRepository } from "../adapters/inMemoryTaskRepository";
import { createTask, listTasks } from "../application/taskOperations";
import { MATRIX_AREAS, TERMINAL_AREAS, type MatrixAreaId } from "../domain/area";
import { isTaskVisibleInMatrix, type Task } from "../domain/task";
import { type TaskRepository } from "../ports/taskRepository";

type AppProps = {
  repository?: TaskRepository;
};

export function App({ repository }: AppProps) {
  const ownedRepository = useRef(new InMemoryTaskRepository());
  const activeRepository = repository ?? ownedRepository.current;
  const [tasks, setTasks] = useState<readonly Task[]>([]);
  const nextTaskNumber = useRef(1);

  useEffect(() => {
    void refreshTasks(activeRepository, setTasks);
  }, [activeRepository]);

  async function handleCreateTask(areaId: MatrixAreaId) {
    await createTask(activeRepository, {
      areaId,
      title: `Task ${nextTaskNumber.current++}`
    });
    await refreshTasks(activeRepository, setTasks);
  }

  return (
    <main>
      <h1>SIFTQ</h1>
      <section aria-label="Task matrix">
        {MATRIX_AREAS.map((area) => (
          <article key={area.id}>
            <h2>{area.label}</h2>
            <button
              aria-label={`Add task to ${area.label}`}
              type="button"
              onClick={() => void handleCreateTask(area.id)}
            >
              +
            </button>
            <ul aria-label={`${area.label} tasks`}>
              {tasksForArea(tasks, area.id).map((task) => (
                <li key={task.id}>{task.title}</li>
              ))}
            </ul>
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

async function refreshTasks(
  repository: TaskRepository,
  setTasks: (tasks: readonly Task[]) => void
) {
  setTasks(await listTasks(repository));
}

function tasksForArea(tasks: readonly Task[], areaId: MatrixAreaId): Task[] {
  return tasks
    .filter((task) => task.areaId === areaId && isTaskVisibleInMatrix(task))
    .sort((left, right) => left.order - right.order);
}
