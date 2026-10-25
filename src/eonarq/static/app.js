const $ = id => document.getElementById(id);
const state = { board: null, byId: new Map(), epic: new URL(location.href).searchParams.get('epic'), editor: null, hovered: null, focused: null, loading: null, fingerprint: null };
const statusLabels = { todo: 'To do', in_progress: 'In progress', blocked: 'Blocked', done: 'Done' };
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
    const board = await api('q/board'), fingerprint = JSON.stringify(board);
    if (!force && state.fingerprint === fingerprint) return;
    state.board = board; state.fingerprint = fingerprint; state.byId = new Map(board.tasks.map(task => [task.id, task]));
    if (state.epic && !state.byId.has(state.epic)) state.epic = null;
    render();
  })();
  try { await state.loading; } finally { state.loading = null; }
}
function selectEpic(id) {
  state.epic = id;
  const url = new URL(location.href);
  if (id) url.searchParams.set('epic', id); else url.searchParams.delete('epic');
  history.replaceState(null, '', url); render();
}
function renderSidebar() {
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
  const epic = currentEpic(), cells = scopedCells(), done = cells.filter(cell => cell.status === 'done').length;
  const masters = state.board.tasks.filter(task => task.kind === 'master' && (!state.epic || task.parent_id === state.epic));
  $('breadcrumb').textContent = epic ? 'WORKSPACE / EPIC' : 'WORKSPACE / OVERVIEW';
  $('page-title').textContent = epic ? epic.title : 'Your work, in view.';
  $('page-description').textContent = epic ? statusLabels[epic.status] + ' · Master tasks, subtasks and prompts for this epic.' : 'Epics, master tasks and the steps that move them forward.';
  $('add-task').textContent = epic ? '+ Add master task' : '+ New epic'; $('edit-epic').hidden = !epic;
  $('metric-percent').textContent = percent(cells.length ? done / cells.length * 100 : 0);
  $('metric-leaves').textContent = done + ' / ' + cells.length;
  $('metric-masters').textContent = masters.filter(task => task.status === 'done').length + ' / ' + masters.length;
  $('tasks-title').textContent = epic ? 'Master tasks' : 'Epics';
  $('tasks-count').textContent = (epic ? masters.length : roots().length) + (epic ? ' master tasks' : ' epics');
  renderChart(cells); renderTasks();
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
    const cell = button('', 'cell' + (item.status === 'done' ? ' done' : ''), () => openEditor(item.id), title);
    cell.title = title; cell.dataset.task = item.id; cell.dataset.group = group;
    cell.addEventListener('pointerenter', () => { state.hovered = group; $('cell-hint').textContent = title; highlightBoundary(); });
    cell.addEventListener('pointerleave', () => { state.hovered = null; highlightBoundary(); });
    cell.addEventListener('focus', () => { state.focused = group; $('cell-hint').textContent = title; highlightBoundary(); });
    cell.addEventListener('blur', () => { state.focused = null; highlightBoundary(); }); grid.append(cell);
  }
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'task-boundaries'); svg.setAttribute('aria-hidden', 'true'); grid.append(svg);
  $('cell-hint').textContent = cells.length ? 'Hover a square to see its task; click to edit its prompt.' : 'Create an epic to start your plan.';
  $('chart-clarification').textContent = 'Each square is a leaf task. Hover to outline its ' + (state.epic ? 'master task.' : 'epic.') + ' A task without children counts as one leaf.';
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
function renderTasks() {
  const list = $('task-list'); list.replaceChildren(); list.className = state.epic ? '' : 'epic-cards';
  const tasks = state.epic ? children(state.epic) : roots();
  if (!tasks.length) { list.className = ''; list.append(emptyState(state.epic ? 'Break the epic into master tasks.' : 'A clear place for a long plan.', state.epic ? 'Add a master task, then give it subtasks and a prompt.' : 'Create your first epic. Give it a goal, then plan the work beneath it.')); return; }
  tasks.forEach((task, index) => {
    if (!state.epic) {
      const card = node('article', 'panel epic-card'), top = node('div', 'card-top');
      top.append(button(task.title, 'title-button', () => selectEpic(task.id)), badge(task));
      const footer = node('div', 'card-footer'); footer.append(node('span', '', task.done + ' / ' + task.total + ' leaf tasks · ' + percent(task.percent)), button('Edit prompt', 'button', () => openEditor(task.id)));
      card.append(top, progress(task), footer); list.append(card); return;
    }
    const panel = node('article', 'panel master-panel'), top = node('div', 'master-top'), title = node('div', 'master-title');
    title.append(checkbox(task), node('span', 'task-number', String(index + 1).padStart(2, '0')), button(task.title, 'title-button', () => openEditor(task.id)));
    const actions = node('div', 'master-actions'); actions.append(badge(task), button('+ Subtask', 'button', () => openNew('subtask', task.id)), button('Edit', 'button', () => openEditor(task.id), 'Edit ' + task.title));
    top.append(title, actions); panel.append(top);
    const subtasks = children(task.id);
    if (subtasks.length) {
      const rows = node('div', 'subtask-list');
      for (const subtask of subtasks) {
        const row = node('div', 'subtask-row'); row.append(checkbox(subtask), button(subtask.title, 'title-button' + (subtask.status === 'done' ? ' completed' : ''), () => openEditor(subtask.id)), badge(subtask), button('Edit', 'task-edit', () => openEditor(subtask.id), 'Edit ' + subtask.title)); rows.append(row);
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
  $('task-status').value = task?.status || 'todo'; $('task-status').disabled = !task;
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
  const editor = state.editor, data = { title: $('task-title').value, prompt: $('task-prompt').value, position: Number($('task-position').value) };
  $('save-task').disabled = true; $('form-error').textContent = '';
  let saved = false;
  try {
    const result = editor.task
      ? await api('c/update', { ...data, task_id: editor.task.id, expected_version: editor.task.version, status: $('task-status').value })
      : await api('c/create', { ...data, kind: editor.kind, parent_id: editor.parent_id });
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
$('overview').addEventListener('click', () => state.board && selectEpic(null));
$('new-epic').addEventListener('click', () => state.board && openNew('epic'));
$('add-task').addEventListener('click', () => state.board && (state.epic ? openNew('master', state.epic) : openNew('epic')));
$('edit-epic').addEventListener('click', () => run(() => openEditor(state.epic)));
$('refresh').addEventListener('click', () => run(() => loadBoard(true)));
$('task-form').addEventListener('submit', saveEditor);
$('delete-task').addEventListener('click', () => run(deleteEditorTask));
for (const id of ['close-dialog', 'cancel-dialog']) $(id).addEventListener('click', () => $('task-dialog').close());
new ResizeObserver(drawBoundaries).observe($('waffle'));
setInterval(() => { if (!$('task-dialog').open) run(() => loadBoard()); }, 5000);
run(() => loadBoard());
