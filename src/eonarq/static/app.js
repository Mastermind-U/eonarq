const $ = id => document.getElementById(id);
const state = { board: null, projects: [], project: new URL(location.href).searchParams.get('project'), projectEditor: null, grouped: localStorage.getItem('eonarq-group-epics') === 'true', byId: new Map(), epic: new URL(location.href).searchParams.get('epic'), editor: null, hovered: null, focused: null, loading: null, fingerprint: null, dragged: null, pending: new Set() };
const statusLabels = { todo: 'To do', in_progress: 'In progress', blocked: 'Blocked', done: 'Done', cancelled: 'Cancelled' };
const kindLabels = { epic: 'epic', master: 'master task', subtask: 'subtask' };
let toastTimer;
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function button(text, className, action, label) {
  const element = node('button', className, text); element.type = 'button';
  if (label) element.setAttribute('aria-label', label);
  element.addEventListener('click', () => run(action)); return element;
}
function toast(message) {
  clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 6000);
}
async function run(action) { try { await action(); } catch (error) { toast(error.message); } }
async function api(path, data) {
  const response = await fetch('/api/planning/' + path, data === undefined ? { cache: 'no-store' } : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  const result = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(result.detail) ? result.detail.map(item => item.msg).join('; ') : result.detail;
    throw new Error(detail || 'The request could not be completed.');
  }
  return result;
}
function children(id) {
  return state.board.tasks.filter(task => task.parent_id === id).sort((a, b) => a.position - b.position || a.id.localeCompare(b.id));
}
function roots() { return children(null); }
function percent(value) { return new Intl.NumberFormat('en', { maximumFractionDigits: 1 }).format(value) + '%'; }
function currentEpic() { return state.byId.get(state.epic); }
async function loadBoard(force = false) {
  if (state.loading) {
    if (force) { await state.loading; return loadBoard(true); }
    return;
  }
  state.loading = (async () => {
    const projects = await api('q/projects');
    if (!state.project && state.epic) {
      try { state.project = (await api('q/tasks/' + state.epic)).project_id; } catch { state.epic = null; }
    }
    if (!projects.some(project => project.id === state.project)) { state.project = projects[0]?.id || null; state.epic = null; }
    const board = await api('q/board' + (state.project ? '?project_id=' + state.project : '')), fingerprint = JSON.stringify([projects, board]);
    if (!force && state.fingerprint === fingerprint) return;
    state.projects = projects;
    state.board = board; state.fingerprint = fingerprint; state.byId = new Map(board.tasks.map(task => [task.id, task]));
    if (state.epic && !state.byId.has(state.epic)) state.epic = null;
    syncUrl(); render();
  })();
  try { await state.loading; } finally { state.loading = null; }
}
function selectEpic(id) {
  state.epic = id;
  syncUrl(); render();
}
function syncUrl() {
  const url = new URL(location.href);
  if (state.epic) url.searchParams.set('epic', state.epic); else url.searchParams.delete('epic');
  if (state.project) url.searchParams.set('project', state.project); else url.searchParams.delete('project');
  history.replaceState(null, '', url);
}
async function selectProject(id) {
  if (state.loading) await state.loading;
  state.project = id; state.epic = null; state.fingerprint = null;
  await loadBoard(true);
}
function renderSidebar() {
  const picker = $('project-select'); picker.replaceChildren();
  if (!state.projects.length) { const option = node('option', '', 'Create a project'); option.value = ''; picker.append(option); }
  for (const project of state.projects) { const option = node('option', '', project.title); option.value = project.id; picker.append(option); }
  picker.value = state.project || ''; picker.disabled = !state.projects.length;
  $('edit-project').hidden = !state.project;
  const nav = $('epic-nav'); nav.replaceChildren(); $('epic-count').textContent = roots().length;
  $('overview').classList.toggle('active', !state.epic);
  for (const epic of roots()) {
    const link = button('', 'epic-link' + (state.epic === epic.id ? ' active' : ''), () => selectEpic(epic.id), epic.title);
    link.append(node('span', 'status-dot ' + epic.status), node('span', 'epic-label', epic.title)); nav.append(link);
  }
}
function scopedCells() { return state.board.cells.filter(cell => !state.epic || cell.epic_id === state.epic); }
function groups() {
  if (!state.epic) return roots();
  const masters = children(state.epic); return masters.length ? masters : [currentEpic()];
}
function render() {
  state.hovered = null; state.focused = null;
  renderSidebar();
  const epic = currentEpic(), cells = scopedCells(), activeCells = cells.filter(cell => cell.status !== 'cancelled'), done = activeCells.filter(cell => cell.status === 'done').length;
  const flow = epic ? epic.flow : state.board.flow;
  $('breadcrumb').textContent = epic ? 'WORKSPACE / EPIC' : 'WORKSPACE / OVERVIEW';
  $('page-title').textContent = epic ? epic.title : state.projects.find(project => project.id === state.project)?.title || 'Your work, in view.';
  $('page-description').textContent = epic ? statusLabels[epic.status] + ' · Master tasks, subtasks and prompts for this epic.' : 'All project tasks, from epics to subtasks, in one workflow.';
  $('add-task').textContent = !state.project ? '+ New project' : epic ? '+ Add master task' : '+ New epic'; $('edit-epic').hidden = !epic;
  $('clear-cancelled').hidden = !state.board.tasks.some(task => task.status === 'cancelled');
  $('group-control').hidden = !!epic; $('group-epics').checked = state.grouped;
  $('metric-percent').textContent = percent(activeCells.length ? done / activeCells.length * 100 : 0);
  $('metric-leaves').textContent = done + ' / ' + activeCells.length;
  $('metric-masters').textContent = flow.done + ' / ' + flow.total;
  $('metric-closed-label').textContent = epic ? 'master tasks closed' : 'tasks closed';
  $('metric-wip').textContent = flow.wip;
  $('metric-wip-note').textContent = 'In progress + blocked ' + (epic ? 'masters' : 'tasks');
  $('metric-blocked').textContent = flow.blocked;
  $('metric-blocked-label').textContent = epic ? 'blocked master tasks' : 'blocked tasks';
  $('epic-chart').hidden = !epic;
  $('board-hint').hidden = !!epic;
  $('board-viewport').classList.toggle('epic-view', !!epic);
  $('board-viewport').setAttribute('aria-label', epic ? 'Master tasks' : 'Agile board');
  $('tasks-title').textContent = epic ? 'Master tasks' : 'Agile board';
  $('tasks-count').textContent = flow.total + (epic ? ' master tasks' : ' tasks');
  if (epic) renderChart(cells); else $('waffle').replaceChildren();
  renderTasks();
}
function highlightBoundary() {
  const active = state.hovered ?? state.focused;
  document.querySelectorAll('.task-boundary').forEach(path => path.classList.toggle('active', path.dataset.group === active));
}
function renderChart(cells) {
  const grid = $('waffle'); grid.replaceChildren();
  for (const item of cells) {
    const group = state.epic ? item.master_id || item.epic_id : item.epic_id;
    const title = state.byId.get(group).title + ' · ' + item.title + ' · ' + statusLabels[item.status];
    const cell = button('', 'cell ' + item.status, () => openEditor(item.id), title);
    cell.title = title; cell.dataset.task = item.id; cell.dataset.group = group;
    cell.addEventListener('pointerenter', () => { state.hovered = group; $('cell-hint').textContent = title; highlightBoundary(); });
    cell.addEventListener('pointerleave', () => { state.hovered = null; highlightBoundary(); });
    cell.addEventListener('focus', () => { state.focused = group; $('cell-hint').textContent = title; highlightBoundary(); });
    cell.addEventListener('blur', () => { state.focused = null; highlightBoundary(); }); grid.append(cell);
  }
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'task-boundaries'); svg.setAttribute('aria-hidden', 'true'); grid.append(svg);
  $('cell-hint').textContent = cells.length ? 'Hover a square to see its task; click to edit its prompt.' : 'Create an epic to start your plan.';
  $('chart-clarification').textContent = 'Each square is a leaf task. Hover to outline its ' + (state.epic ? 'master task.' : 'epic.') + ' A task without children counts as one leaf. Cancelled tasks are excluded from progress.';
  const legend = $('group-legend'); legend.replaceChildren(); legend.hidden = !cells.length;
  groups().forEach((group, index) => {
    const item = button('', 'group-item', () => state.epic ? openEditor(group.id) : selectEpic(group.id), group.title);
    item.append(node('span', 'group-number', String(index + 1).padStart(2, '0')), node('span', 'group-title', group.title), node('span', 'group-percent', percent(group.percent)));
    item.addEventListener('pointerenter', () => { state.hovered = group.id; highlightBoundary(); });
    item.addEventListener('pointerleave', () => { state.hovered = null; highlightBoundary(); }); legend.append(item);
  });
  drawBoundaries();
}
function drawBoundaries() {
  const grid = $('waffle'), svg = grid.querySelector('.task-boundaries'); if (!svg) return;
  const cells = [...grid.querySelectorAll('.cell')]; svg.replaceChildren(); if (!cells.length) return;
  const gap = parseFloat(getComputedStyle(grid).columnGap), rowGap = parseFloat(getComputedStyle(grid).rowGap);
  const rows = [...new Set(cells.map(cell => cell.offsetTop))].sort((a, b) => a - b);
  const columns = [...new Set(cells.map(cell => cell.offsetLeft))].sort((a, b) => a - b);
  const byPosition = new Map(), edges = new Map();
  const tiles = cells.map(cell => {
    const tile = { row: rows.indexOf(cell.offsetTop), column: columns.indexOf(cell.offsetLeft), group: cell.dataset.group };
    byPosition.set(tile.row + ':' + tile.column, tile.group); if (!edges.has(tile.group)) edges.set(tile.group, []); return tile;
  });
  for (const { row, column, group } of tiles) {
    const lines = edges.get(group), edge = (from, to) => lines.push({ from, to, used: false });
    if (byPosition.get((row - 1) + ':' + column) !== group) edge([column, row], [column + 1, row]);
    if (byPosition.get(row + ':' + (column + 1)) !== group) edge([column + 1, row], [column + 1, row + 1]);
    if (byPosition.get((row + 1) + ':' + column) !== group) edge([column + 1, row + 1], [column, row + 1]);
    if (byPosition.get(row + ':' + (column - 1)) !== group) edge([column, row + 1], [column, row]);
  }
  for (const [id, lines] of edges) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('class', 'task-boundary'); path.dataset.group = id;
    path.setAttribute('d', roundedContour(lines, cells[0].offsetLeft - gap / 2, cells[0].offsetTop - rowGap / 2, cells[0].offsetWidth + gap, cells[0].offsetHeight + rowGap)); svg.append(path);
  }
  highlightBoundary();
}
    function roundedContour(edges, originX, originY, stepX, stepY) {
      const key = point => point[0] + ':' + point[1], outgoing = new Map();
      for (const edge of edges) {
        const start = key(edge.from);
        if (!outgoing.has(start)) outgoing.set(start, []);
        outgoing.get(start).push(edge);
      }
      const direction = edge => edge.to[0] > edge.from[0] ? 0 : edge.to[1] > edge.from[1] ? 1 : edge.to[0] < edge.from[0] ? 2 : 3;
      const turnRank = [1, 0, 3, 2], paths = [];
      for (const first of edges) {
        if (first.used) continue;
        const points = []; let edge = first;
        while (edge && !edge.used) {
          edge.used = true; points.push(edge.from);
          if (key(edge.to) === key(first.from)) break;
          const directionIn = direction(edge);
          edge = (outgoing.get(key(edge.to)) || []).filter(candidate => !candidate.used)
            .sort((a, b) => turnRank[(direction(a) - directionIn + 4) % 4] - turnRank[(direction(b) - directionIn + 4) % 4])[0];
        }
        const corners = points.filter((point, index) => {
          const previous = points[(index + points.length - 1) % points.length], next = points[(index + 1) % points.length];
          return (point[0] - previous[0]) * (next[1] - point[1]) !== (point[1] - previous[1]) * (next[0] - point[0]);
        }).map(([x, y]) => [originX + x * stepX, originY + y * stepY]);
        if (corners.length < 3) continue;
        let path = '';
        for (let index = 0; index < corners.length; index++) {
          const point = corners[index], previous = corners[(index + corners.length - 1) % corners.length], next = corners[(index + 1) % corners.length];
          const beforeLength = Math.hypot(previous[0] - point[0], previous[1] - point[1]), afterLength = Math.hypot(next[0] - point[0], next[1] - point[1]);
          const radius = Math.min(4, beforeLength / 2, afterLength / 2);
          const before = point.map((value, axis) => value + (previous[axis] - value) * radius / beforeLength);
          const after = point.map((value, axis) => value + (next[axis] - value) * radius / afterLength);
          path += (index ? 'L' : 'M') + before.join(' ') + 'Q' + point.join(' ') + ' ' + after.join(' ');
        }
        paths.push(path + 'Z');
      }
      return paths.join('');
    }

function badge(task) { return node('span', 'badge ' + task.status, statusLabels[task.status]); }
function progress(task) {
  const track = node('div', 'progress-track'), fill = node('span'); track.setAttribute('aria-hidden', 'true');
  fill.style.width = task.percent + '%'; track.append(fill); return track;
}
function checkbox(task) {
  const input = node('input', 'task-check'); input.type = 'checkbox'; input.checked = task.status === 'done';
  input.setAttribute('aria-label', 'Mark ' + task.title + ' as ' + (input.checked ? 'open' : 'done'));
  input.addEventListener('change', () => run(async () => {
    input.disabled = true;
    try { await api('c/update', { task_id: task.id, expected_version: task.version, status: input.checked ? 'done' : 'todo' }); }
    catch (error) { input.checked = !input.checked; throw error; }
    finally { input.disabled = false; await loadBoard(true); }
  })); return input;
}
function emptyState(title, description) {
  const empty = node('div', 'empty-state'); empty.append(node('strong', '', title), node('span', '', description)); return empty;
}
function setCardBusy(id, busy) {
  const card = $('task-list').querySelector('.kanban-card[data-task="' + id + '"]');
  if (!card) return;
  card.setAttribute('aria-busy', String(busy)); card.draggable = !busy;
  card.querySelectorAll('button, select').forEach(control => { control.disabled = busy; });
  if (!busy) card.querySelector('.card-status').value = state.byId.get(id)?.status;
}
async function changeTaskStatus(task, status) {
  if (task.status === status || state.pending.has(task.id)) return;
  if (status === 'cancelled' && descendantCount(task.id) && !confirm('Cancel “' + task.title + '” and all its descendants?')) { setCardBusy(task.id, false); return; }
  state.pending.add(task.id); setCardBusy(task.id, true);
  try {
    await api('c/update', { task_id: task.id, expected_version: task.version, status });
    await loadBoard(true); toast('Moved ' + task.title + ' to ' + statusLabels[status] + '.');
  } catch (error) {
    try { await loadBoard(true); } catch { /* The next refresh retries the read. */ }
    throw error;
  } finally { state.pending.delete(task.id); setCardBusy(task.id, false); }
}
function clearDrag() {
  state.dragged = null;
  document.querySelectorAll('.drag-over, .dragging').forEach(element => element.classList.remove('drag-over', 'dragging'));
}
function epicCard(task, number) {
  const card = node('article', 'epic-card kanban-card'); card.dataset.task = task.id;
  card.setAttribute('role', 'listitem'); card.draggable = !state.pending.has(task.id);
  const kicker = node('div', 'card-kicker'), handle = node('span', 'drag-handle', '⠿'); handle.setAttribute('aria-hidden', 'true'); handle.title = 'Drag epic';
  kicker.append(handle, node('span', '', kindLabels[task.kind] + ' ' + String(number).padStart(2, '0')), node('span', 'action-badge', task.action));
  const summary = node('div', 'card-progress-copy'); summary.append(node('span', '', task.done + ' / ' + task.total + ' leaf tasks'), node('span', '', percent(task.percent)));
  const controls = node('div', 'card-controls'), select = node('select', 'card-status'); select.setAttribute('aria-label', 'Status for ' + task.title);
  for (const [value, label] of Object.entries(statusLabels)) {
    const option = node('option', '', label); option.value = value; select.append(option);
  }
  select.value = task.status; select.disabled = state.pending.has(task.id);
  select.addEventListener('change', () => run(() => changeTaskStatus(task, select.value)));
  controls.append(select, button('Edit prompt', 'task-edit', () => openEditor(task.id), 'Edit prompt for ' + task.title));
  card.append(kicker, button(task.title, 'title-button', () => task.kind === 'epic' ? selectEpic(task.id) : openEditor(task.id)), summary, progress(task));
  const parent = state.byId.get(task.parent_id);
  if (parent) card.append(button(parent.title, 'card-context', () => openEditor(parent.id), 'Parent: ' + parent.title));
  if (task.kind !== 'subtask') card.append(button(task.kind === 'epic' ? '+ Master task' : '+ Subtask', 'task-edit', () => openNew(task.kind === 'epic' ? 'master' : 'subtask', task.id)));
  card.append(controls);
  if (state.pending.has(task.id)) { card.setAttribute('aria-busy', 'true'); card.querySelectorAll('button').forEach(control => { control.disabled = true; }); }
  card.addEventListener('dragstart', event => {
    if (state.pending.has(task.id) || event.target.closest('button, select, input, textarea, a')) { event.preventDefault(); return; }
    state.dragged = task; event.dataTransfer.setData('text/plain', task.id); event.dataTransfer.effectAllowed = 'move'; card.classList.add('dragging');
  });
  card.addEventListener('dragend', clearDrag);
  return card;
}
function renderKanban() {
  const list = $('task-list'); list.className = 'project-board';
  if (!state.project) { list.append(emptyState('Create your first project.', 'Use the + button above Epics to start.')); return; }
  if (!state.board.tasks.length) { list.append(emptyState('Create your first epic.', 'Add master tasks and subtasks to build your project.')); return; }
  const lanes = state.grouped ? roots().map(epic => ({ epic, tasks: state.board.tasks.filter(task => epicOf(task) === epic.id) })) : [{ epic: null, tasks: state.board.tasks }];
  for (const lane of lanes) {
    if (lane.epic) list.append(button(lane.epic.title, 'lane-heading', () => selectEpic(lane.epic.id)));
    const grid = node('div', 'kanban-board'); grid.dataset.epic = lane.epic?.id || '';
    renderColumns(grid, lane.tasks); list.append(grid);
  }
}
function epicOf(task) {
  while (task.parent_id) task = state.byId.get(task.parent_id);
  return task.id;
}
function renderColumns(list, items) {
  const numbers = new Map(items.map((task, index) => [task.id, index + 1]));
  for (const [status, label] of Object.entries(statusLabels)) {
    const tasks = items.filter(task => task.status === status), column = node('section', 'kanban-column'); column.dataset.status = status;
    const heading = node('div', 'column-heading'), title = node('h3', '', label); title.id = 'column-' + list.dataset.epic + '-' + status; column.setAttribute('aria-labelledby', title.id);
    heading.append(node('span', 'status-dot ' + status), title, node('span', 'column-count', tasks.length));
    const cards = node('div', 'kanban-cards'); cards.setAttribute('role', 'list'); cards.setAttribute('aria-label', label + ' tasks');
    for (const task of tasks) cards.append(epicCard(task, numbers.get(task.id)));
    if (!tasks.length) cards.append(node('p', 'column-empty', 'No tasks. Drop a card here.'));
    column.append(heading, cards);
    column.addEventListener('dragover', event => {
      if (!state.dragged) return;
      event.preventDefault(); event.dataTransfer.dropEffect = 'move'; column.classList.add('drag-over');
      const viewport = $('board-viewport'), bounds = viewport.getBoundingClientRect();
      if (event.clientX < bounds.left + 35) viewport.scrollLeft -= 18;
      else if (event.clientX > bounds.right - 35) viewport.scrollLeft += 18;
    });
    column.addEventListener('dragleave', event => { if (!column.contains(event.relatedTarget)) column.classList.remove('drag-over'); });
    column.addEventListener('drop', event => {
      const task = state.dragged;
      if (!task || event.dataTransfer.getData('text/plain') !== task.id) return;
      event.preventDefault(); clearDrag(); run(() => changeTaskStatus(task, status));
    });
    list.append(column);
  }
}
function renderTasks() {
  const list = $('task-list'); list.replaceChildren();
  if (!state.epic) { renderKanban(); return; }
  list.className = '';
  const tasks = children(state.epic);
  if (!tasks.length) { list.append(emptyState('Break the epic into master tasks.', 'Add a master task, then give it subtasks and a prompt.')); return; }
  tasks.forEach((task, index) => {
    const panel = node('article', 'panel master-panel'), top = node('div', 'master-top'), title = node('div', 'master-title');
    title.append(checkbox(task), node('span', 'task-number', String(index + 1).padStart(2, '0')), button(task.title, 'title-button', () => openEditor(task.id)), node('span', 'action-badge', task.action));
    const actions = node('div', 'master-actions'); actions.append(badge(task), button('+ Subtask', 'button', () => openNew('subtask', task.id)), button('Edit', 'button', () => openEditor(task.id), 'Edit ' + task.title));
    top.append(title, actions); panel.append(top);
    const subtasks = children(task.id);
    if (subtasks.length) {
      const rows = node('div', 'subtask-list');
      for (const subtask of subtasks) {
        const row = node('div', 'subtask-row'); row.append(checkbox(subtask), button(subtask.title, 'title-button' + (subtask.status === 'done' ? ' completed' : ''), () => openEditor(subtask.id)), node('span', 'action-badge', subtask.action), badge(subtask), button('Edit', 'task-edit', () => openEditor(subtask.id), 'Edit ' + subtask.title)); rows.append(row);
      }
      panel.append(rows);
    }
    list.append(panel);
  });
}
function fillEditor(task, kind, parentId) {
  state.editor = { task, kind, parent_id: parentId };
  $('dialog-kind').textContent = kindLabels[kind].toUpperCase(); $('dialog-title').textContent = (task ? 'Edit ' : 'New ') + kindLabels[kind];
  $('task-title').value = task?.title || ''; $('task-prompt').value = task?.prompt || '';
  $('task-report').value = task?.report || '';
  $('task-status').value = task?.status || 'todo'; $('task-status').disabled = !task;
  $('task-action').value = task?.action || 'ACTION';
  $('task-position').value = task?.position ?? children(parentId).length;
  $('delete-task').hidden = !task; $('form-error').textContent = ''; $('save-task').disabled = false;
  $('task-dialog').showModal(); $('task-title').focus();
}
function openNew(kind, parentId = null) { fillEditor(null, kind, parentId); }
async function openEditor(id) {
  const task = await api('q/tasks/' + id); fillEditor(task, task.kind, task.parent_id);
}
async function saveEditor(event) {
  event.preventDefault(); if (!state.editor) return;
  const editor = state.editor, data = { title: $('task-title').value, prompt: $('task-prompt').value, report: $('task-report').value, position: Number($('task-position').value), action: $('task-action').value };
  if (editor.task && $('task-status').value === 'cancelled' && editor.task.status !== 'cancelled' && descendantCount(editor.task.id) && !confirm('Cancel this task and all its descendants?')) return;
  $('save-task').disabled = true; $('form-error').textContent = '';
  let saved = false;
  try {
    const result = editor.task
      ? await api('c/update', { ...data, task_id: editor.task.id, expected_version: editor.task.version, status: $('task-status').value })
      : await api('c/create', { ...data, kind: editor.kind, parent_id: editor.parent_id, project_id: state.project });
    saved = true;
    await loadBoard(true);
    if (!editor.task && editor.kind === 'epic') selectEpic(result.task_id);
    $('task-dialog').close();
    toast(editor.task ? 'Task and prompt saved.' : 'Task created.');
  } catch (error) {
    if (saved) { $('task-dialog').close(); toast('Task saved. Refresh to load the latest state: ' + error.message); }
    else $('form-error').textContent = error.message;
  }
  finally { $('save-task').disabled = false; }
}
function descendantCount(id) { return children(id).reduce((sum, child) => sum + 1 + descendantCount(child.id), 0); }
async function deleteEditorTask() {
  const task = state.editor?.task; if (!task) return;
  const count = descendantCount(task.id);
  if (!confirm('Delete “' + task.title + '”' + (count ? ' and its ' + count + ' descendants' : '') + '? This cannot be undone.')) return;
  await api('c/delete', { task_id: task.id, expected_version: task.version, recursive: count > 0 });
  $('task-dialog').close(); await loadBoard(true); toast('Task deleted.');
}
function openProjectEditor(edit = false) {
  const project = edit ? state.projects.find(item => item.id === state.project) : null;
  state.projectEditor = project;
  $('project-dialog-title').textContent = project ? 'Edit project' : 'New project';
  $('project-title').value = project?.title || ''; $('project-prompt').value = project?.prompt || '';
  $('project-error').textContent = ''; $('project-dialog').showModal(); $('project-title').focus();
}
async function saveProject(event) {
  event.preventDefault(); $('save-project').disabled = true; $('project-error').textContent = '';
  try {
    const project = state.projectEditor, data = { title: $('project-title').value, prompt: $('project-prompt').value };
    const result = project
      ? await api('c/projects/update', { ...data, project_id: project.id, expected_version: project.version })
      : await api('c/projects/create', data);
    $('project-dialog').close();
    if (!project) await selectProject(result.project_id); else await loadBoard(true);
    toast('Project saved.');
  } catch (error) { $('project-error').textContent = error.message; }
  finally { $('save-project').disabled = false; }
}
async function clearCancelled() {
  const count = state.board.tasks.filter(task => task.status === 'cancelled').length;
  if (!count || !confirm('Permanently delete ' + count + ' cancelled tasks from this project?')) return;
  const result = await api('c/clear-cancelled', { project_id: state.project });
  await loadBoard(true); toast('Cleared ' + result.deleted + ' cancelled tasks.');
}
$('new-project').addEventListener('click', () => openProjectEditor());
$('edit-project').addEventListener('click', () => openProjectEditor(true));
$('project-select').addEventListener('change', event => run(() => selectProject(event.target.value)));
$('project-form').addEventListener('submit', saveProject);
for (const id of ['close-project', 'cancel-project']) $(id).addEventListener('click', () => $('project-dialog').close());
$('clear-cancelled').addEventListener('click', () => run(clearCancelled));
$('group-epics').addEventListener('change', event => { state.grouped = event.target.checked; localStorage.setItem('eonarq-group-epics', state.grouped); renderTasks(); });
$('overview').addEventListener('click', () => state.board && selectEpic(null));
$('new-epic').addEventListener('click', () => state.project ? openNew('epic') : openProjectEditor());
$('add-task').addEventListener('click', () => state.board && (!state.project ? openProjectEditor() : state.epic ? openNew('master', state.epic) : openNew('epic')));
$('edit-epic').addEventListener('click', () => run(() => openEditor(state.epic)));
$('refresh').addEventListener('click', () => run(() => loadBoard(true)));
$('task-form').addEventListener('submit', saveEditor);
$('delete-task').addEventListener('click', () => run(deleteEditorTask));
for (const id of ['close-dialog', 'cancel-dialog']) $(id).addEventListener('click', () => $('task-dialog').close());
new ResizeObserver(drawBoundaries).observe($('waffle'));
setInterval(() => { if (!$('task-dialog').open && !$('project-dialog').open && !state.dragged && !state.pending.size) run(() => loadBoard()); }, 5000);
run(() => loadBoard());
