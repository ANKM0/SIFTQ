import { TASK_STATUSES } from "../task";
import type { Task, TaskStatus } from "../task";
import { pageNavItems } from "../task-list";
import { TaskRow } from "../components/TaskRow";
import { NewTaskLink } from "./navigation";

const TASK_STATUS_OPTIONS: { status: TaskStatus; label: string }[] = TASK_STATUSES.map((status) => ({
  status,
  label: status,
}));

function TaskStatusFilter({ status, workingOnly }: { status: TaskStatus; workingOnly: boolean }) {
  const workingParam = workingOnly ? "&working=only" : "";
  return (
    <>
      <nav
        class="task-status-filter task-status-filter--toolbar"
        aria-label="Filter tasks by status"
        data-task-status-tabs
      >
        {TASK_STATUS_OPTIONS.map((option) => (
          <a
            key={option.status}
            class={option.status === status ? "button small is-active" : "button small"}
            aria-current={option.status === status ? "true" : undefined}
            href={`/tasks?status=${option.status}${workingParam}`}
          >
            {option.label}
          </a>
        ))}
      </nav>
      <p
        class="task-selection-summary task-selection-summary--toolbar"
        data-task-selection-summary
        aria-live="polite"
        hidden
      >
        0 of 0 selected
      </p>
    </>
  );
}

function PageNavLink({
  status,
  page,
  workingOnly,
  query,
}: {
  status: TaskStatus;
  page: number;
  workingOnly: boolean;
  query: string | undefined;
}) {
  const workingParam = workingOnly ? "&working=only" : "";
  const queryParam = query === undefined ? "" : `&q=${encodeURIComponent(query)}`;
  return (
    <a
      class="button small"
      href={`/tasks?status=${status}${workingParam}${queryParam}&page=${page}`}
      aria-label={`Page ${page}`}
    >
      {page}
    </a>
  );
}

function PageNavItem({
  item,
  index,
  status,
  currentPage,
  workingOnly,
  query,
}: {
  item: number | "ellipsis";
  index: number;
  status: TaskStatus;
  currentPage: number;
  workingOnly: boolean;
  query: string | undefined;
}) {
  if (item === "ellipsis") {
    return (
      <span key={`ellipsis-${index}`} class="pagination-ellipsis" aria-hidden="true">
        …
      </span>
    );
  }
  if (item === currentPage) {
    return (
      <span key={item} class="button small is-active" aria-current="page">
        {item}
      </span>
    );
  }
  return <PageNavLink key={item} status={status} page={item} workingOnly={workingOnly} query={query} />;
}

function PageNav({
  status,
  currentPage,
  totalPages,
  workingOnly,
  query,
}: {
  status: TaskStatus;
  currentPage: number;
  totalPages: number;
  workingOnly: boolean;
  query: string | undefined;
}) {
  if (totalPages <= 1) return null;
  const workingParam = workingOnly ? "&working=only" : "";
  const queryParam = query === undefined ? "" : `&q=${encodeURIComponent(query)}`;
  const href = (page: number) => `/tasks?status=${status}${workingParam}${queryParam}&page=${page}`;
  return (
    <nav class="pagination" aria-label="Task list pages">
      {currentPage > 1 ? (
        <a class="button small" href={href(currentPage - 1)} aria-label="Previous page">
          前へ
        </a>
      ) : (
        <span class="button small is-disabled" aria-disabled="true">
          前へ
        </span>
      )}
      {pageNavItems(currentPage, totalPages).map((item, index) => (
        <PageNavItem
          key={index}
          item={item}
          index={index}
          status={status}
          currentPage={currentPage}
          workingOnly={workingOnly}
          query={query}
        />
      ))}
      {currentPage < totalPages ? (
        <a class="button small" href={href(currentPage + 1)} aria-label="Next page">
          次へ
        </a>
      ) : (
        <span class="button small is-disabled" aria-disabled="true">
          次へ
        </span>
      )}
    </nav>
  );
}

function queryWithWorkingLabel(query: string, workingOnly: boolean): string {
  const tokens = query.trim().split(/\s+/).filter((token) => token !== "label:working");
  if (workingOnly) tokens.push("label:working");
  return tokens.join(" ");
}

function TaskLabelsFilter({
  status,
  workingOnly,
  query,
}: {
  status: TaskStatus;
  workingOnly: boolean;
  query: string | undefined;
}) {
  const allLabelsQuery = query === undefined ? undefined : queryWithWorkingLabel(query, false);
  const workingQuery = query === undefined ? undefined : queryWithWorkingLabel(query, true);
  const queryParam = (value: string | undefined) => (value === undefined ? "" : `&q=${encodeURIComponent(value)}`);
  return (
    <details class={workingOnly ? "task-label-filter is-active" : "task-label-filter"}>
      <summary class="button small">Labels</summary>
      <div class="task-label-menu">
        <a
          class={!workingOnly ? "is-selected" : undefined}
          href={`/tasks?status=${status}${queryParam(allLabelsQuery)}`}
        >
          All labels
        </a>
        <a
          class={workingOnly ? "is-selected" : undefined}
          href={`/tasks?status=${status}&working=only${queryParam(workingQuery)}`}
        >
          working only
        </a>
      </div>
    </details>
  );
}

function TaskListSearch({
  status,
  workingOnly,
  query,
}: {
  status: TaskStatus;
  workingOnly: boolean;
  query: string;
}) {
  return (
    <form class="task-search" action="/tasks" method="get">
      <input type="hidden" name="status" value={status} />
      {workingOnly ? <input type="hidden" name="working" value="only" /> : null}
      <input
        type="search"
        name="q"
        aria-label="Search tasks"
        value={query}
        placeholder="is:issue state:closed"
      />
      <button class="button small task-search-button" type="submit" aria-label="Submit search" title="Search">
        <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <circle cx="8.5" cy="8.5" r="5.5" />
          <path d="m13 13 4 4" />
        </svg>
      </button>
    </form>
  );
}

function TaskListToolbar({
  hasTasks,
  status,
  workingOnly,
  query,
}: {
  hasTasks: boolean;
  status: TaskStatus;
  workingOnly: boolean;
  query: string | undefined;
}) {
  return (
    <>
      <div class="task-list-toolbar">
        <label class="task-select-all">
          <input
            type="checkbox"
            aria-label="Select all tasks on this page"
            data-task-select-all
            disabled={!hasTasks}
          />
        </label>
        <TaskStatusFilter status={status} workingOnly={workingOnly} />
        <div class="task-bulk-actions">
          <div data-task-bulk-actions>
            <details class="task-bulk-menu">
              <summary class="button small">Mark as</summary>
              <div class="task-bulk-menu-items">
                <button type="button" data-task-action="do">do</button>
                <button type="button" data-task-action="done">done</button>
                <button type="button" data-task-action="skip">skip</button>
              </div>
            </details>
          </div>
          <TaskLabelsFilter status={status} workingOnly={workingOnly} query={query} />
          <button
            class="button small button--danger"
            type="button"
            data-task-action="delete"
            data-task-bulk-delete
            disabled
          >
            delete
          </button>
        </div>
      </div>
      <p class="task-selection-feedback" data-task-selection-feedback role="status" hidden></p>
    </>
  );
}

function TaskListRows({ tasks, pageOffset }: { tasks: readonly Task[]; pageOffset: number }) {
  return (
    <div class="list" aria-label="Task list">
      {tasks.length === 0 ? (
        <p class="task-list-empty">該当するtaskはありません。</p>
      ) : (
        tasks.map((task, index) => (
          <TaskRow key={task.id} task={task} issueNumber={pageOffset + index + 1} />
        ))
      )}
    </div>
  );
}

export function TaskListPage({
  tasks,
  status,
  workingOnly,
  query,
  currentPage,
  totalPages,
  pageOffset,
  queryInUrl,
}: {
  tasks: readonly Task[];
  status: TaskStatus;
  workingOnly: boolean;
  query: string;
  currentPage: number;
  totalPages: number;
  pageOffset: number;
  queryInUrl: string | undefined;
}) {
  return (
    <div class="page page--list" data-state="normal">
      <div class="page-header">
        <div>
          <h1 class="page-title">Tasks</h1>
          <p class="muted">GitHub Issues-like task list.</p>
        </div>
        <NewTaskLink from="tasks" />
      </div>
      <div class="task-list-shell" data-task-list>
        <TaskListSearch status={status} workingOnly={workingOnly} query={query} />
        <TaskListToolbar
          hasTasks={tasks.length > 0}
          status={status}
          workingOnly={workingOnly}
          query={queryInUrl}
        />
        <TaskListRows tasks={tasks} pageOffset={pageOffset} />
      </div>
      <PageNav
        status={status}
        currentPage={currentPage}
        totalPages={totalPages}
        workingOnly={workingOnly}
        query={queryInUrl}
      />
    </div>
  );
}
