import { useEffect, useRef, useState } from "react";
import {
  DndContext,
  type DragEndEvent,
  useDraggable,
  useDroppable
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

import { InMemoryTaskRepository } from "../adapters/inMemoryTaskRepository";
import {
  createTask,
  listTasks,
  moveTask,
  reorderTask
} from "../application/taskOperations";
import { MATRIX_AREAS, TERMINAL_AREAS, type MatrixAreaId } from "../domain/area";
import { isTaskVisibleInMatrix, type Task } from "../domain/task";
import { type TaskRepository } from "../ports/taskRepository";
import {
  areaDropId,
  resolveTaskDropOperation,
  taskDropId
} from "./dragDrop";

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

  async function handleDragEnd(event: DragEndEvent) {
    const operation = resolveTaskDropOperation(
      tasks,
      String(event.active.id),
      event.over === null ? null : String(event.over.id)
    );

    if (operation === null) {
      return;
    }

    if (operation.type === "move") {
      await moveTask(activeRepository, operation);
    } else {
      await reorderTask(activeRepository, operation);
    }

    await refreshTasks(activeRepository, setTasks);
  }

  return (
    <DndContext onDragEnd={(event) => void handleDragEnd(event)}>
      <main>
        <h1>SIFTQ</h1>
        <section aria-label="Task matrix">
          {MATRIX_AREAS.map((area) => (
            <MatrixArea
              key={area.id}
              areaId={area.id}
              label={area.label}
              tasks={tasksForArea(tasks, area.id)}
              onCreateTask={() => void handleCreateTask(area.id)}
            />
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
    </DndContext>
  );
}

type MatrixAreaProps = {
  readonly areaId: MatrixAreaId;
  readonly label: string;
  readonly tasks: readonly Task[];
  readonly onCreateTask: () => void;
};

function MatrixArea({ areaId, label, tasks, onCreateTask }: MatrixAreaProps) {
  const { setNodeRef } = useDroppable({ id: areaDropId(areaId) });

  return (
    <article>
      <h2>{label}</h2>
      <button aria-label={`Add task to ${label}`} type="button" onClick={onCreateTask}>
        +
      </button>
      <ul ref={setNodeRef} aria-label={`${label} tasks`} style={{ minHeight: 32 }}>
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </ul>
    </article>
  );
}

type TaskCardProps = {
  readonly task: Task;
};

function TaskCard({ task }: TaskCardProps) {
  const draggable = useDraggable({ id: taskDropId(task.id) });
  const droppable = useDroppable({ id: taskDropId(task.id) });
  const style = {
    cursor: "grab",
    opacity: draggable.isDragging ? 0.6 : 1,
    transform: CSS.Translate.toString(draggable.transform)
  };

  return (
    <li
      ref={(node) => {
        draggable.setNodeRef(node);
        droppable.setNodeRef(node);
      }}
      style={style}
      {...draggable.listeners}
      {...draggable.attributes}
    >
      {task.title}
    </li>
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
