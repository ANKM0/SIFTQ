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
import "./App.css";

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
      <MatrixPage tasks={tasks} onCreateTask={handleCreateTask} />
    </DndContext>
  );
}

type MatrixPageProps = {
  readonly tasks: readonly Task[];
  readonly onCreateTask: (areaId: MatrixAreaId) => void;
};

function MatrixPage({ tasks, onCreateTask }: MatrixPageProps) {
  return (
    <main className="matrix-page">
      <header className="matrix-page__header">
        <h1>SIFTQ</h1>
      </header>
      <section aria-label="Matrix workspace" className="matrix-workspace">
        <div className="matrix-workspace__status matrix-workspace__status--skipped">
          {TERMINAL_AREAS.filter((area) => area.id === "skipped").map((area) => (
            <StatusDropArea key={area.id} label={area.label} />
          ))}
        </div>
        <section aria-label="Task matrix" className="matrix-grid">
          {MATRIX_AREAS.map((area) => (
            <AreaPanel
              key={area.id}
              areaId={area.id}
              label={area.label}
              tasks={tasksForArea(tasks, area.id)}
              onCreateTask={() => onCreateTask(area.id)}
            />
          ))}
        </section>
        <div className="matrix-workspace__status matrix-workspace__status--done">
          {TERMINAL_AREAS.filter((area) => area.id === "done").map((area) => (
            <StatusDropArea key={area.id} label={area.label} />
          ))}
        </div>
      </section>
    </main>
  );
}

type AreaPanelProps = {
  readonly areaId: MatrixAreaId;
  readonly label: string;
  readonly tasks: readonly Task[];
  readonly onCreateTask: () => void;
};

function AreaPanel({ areaId, label, tasks, onCreateTask }: AreaPanelProps) {
  const { setNodeRef } = useDroppable({ id: areaDropId(areaId) });

  return (
    <article className={`area-panel area-panel--${areaId}`}>
      <header className="area-panel__header">
        <div>
          <h2>{label}</h2>
          <p aria-label={`${label} task count`}>{tasks.length} cards</p>
        </div>
        <button
          aria-label={`Add task to ${label}`}
          className="area-panel__add"
          type="button"
          onClick={onCreateTask}
        >
          +
        </button>
      </header>
      <ul ref={setNodeRef} aria-label={`${label} tasks`} className="area-panel__tasks">
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
      className="task-card"
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

type StatusDropAreaProps = {
  readonly label: string;
};

function StatusDropArea({ label }: StatusDropAreaProps) {
  return (
    <article className="status-drop-area">
      <h2>{label}</h2>
      <p>0 cards</p>
    </article>
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
