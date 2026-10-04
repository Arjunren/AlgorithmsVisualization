(() => {
  'use strict';

  const ROWS = 20;
  const COLS = 30;
  const MAX_WALL_DENSITY = 0.28;

  const gridEl = document.getElementById('grid');
  const algorithmEl = document.getElementById('algorithm');
  const speedEl = document.getElementById('speed');
  const speedLabelEl = document.getElementById('speedLabel');
  const statusEl = document.getElementById('status');
  const runBtn = document.getElementById('runBtn');
  const clearPathBtn = document.getElementById('clearPathBtn');
  const randomBtn = document.getElementById('randomBtn');
  const resetBtn = document.getElementById('resetBtn');
  const foundMetric = document.getElementById('foundMetric');
  const visitedMetric = document.getElementById('visitedMetric');
  const pathMetric = document.getElementById('pathMetric');
  const modeButtons = [...document.querySelectorAll('.mode-btn')];

  let start = [10, 4];
  let goal = [10, 25];
  let walls = new Set();
  let visited = new Set();
  let path = new Set();
  let mode = 'wall';
  let isPointerDown = false;
  let isAnimating = false;
  let animationToken = 0;

  const key = ([r, c]) => `${r},${c}`;
  const same = (a, b) => a[0] === b[0] && a[1] === b[1];
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function setStatus(message, type = 'normal') {
    const styles = {
      normal: 'border-slate-800 bg-slate-900/60 text-slate-300',
      success: 'border-emerald-900/70 bg-emerald-950/30 text-emerald-300',
      error: 'border-rose-900/70 bg-rose-950/30 text-rose-300',
    };
    statusEl.className = `mb-3 min-h-10 rounded-xl border px-4 py-2.5 text-sm ${styles[type] || styles.normal}`;
    statusEl.textContent = message;
  }

  function setMode(nextMode) {
    mode = nextMode;
    modeButtons.forEach((button) => {
      const active = button.dataset.mode === mode;
      button.className = `mode-btn rounded-lg border px-2 py-2 text-xs font-semibold ${
        active
          ? 'border-cyan-500 bg-cyan-500/15 text-cyan-300'
          : 'border-slate-700 text-slate-400 hover:border-slate-500'
      }`;
    });
  }

  function clearSearchVisuals() {
    animationToken += 1;
    visited.clear();
    path.clear();
    foundMetric.textContent = '—';
    visitedMetric.textContent = '0';
    pathMetric.textContent = '—';
    renderGrid();
  }

  function cellClass(r, c) {
    const coord = [r, c];
    const k = key(coord);
    let cls = 'grid-cell h-6 w-6 rounded-[3px] border border-slate-800 bg-slate-950';

    if (walls.has(k)) cls = 'grid-cell h-6 w-6 rounded-[3px] border border-slate-600 bg-slate-600';
    if (visited.has(k)) cls = 'grid-cell h-6 w-6 rounded-[3px] border border-sky-700 bg-sky-500/70';
    if (path.has(k)) cls = 'grid-cell h-6 w-6 rounded-[3px] border border-amber-300 bg-amber-300 shadow-sm shadow-amber-300/40';
    if (same(coord, start)) cls = 'grid-cell h-6 w-6 rounded-[3px] border border-emerald-300 bg-emerald-400 shadow-sm shadow-emerald-400/40';
    if (same(coord, goal)) cls = 'grid-cell h-6 w-6 rounded-[3px] border border-rose-300 bg-rose-400 shadow-sm shadow-rose-400/40';
    return cls;
  }

  function renderGrid() {
    const fragment = document.createDocumentFragment();
    gridEl.replaceChildren();
    gridEl.style.gridTemplateColumns = `repeat(${COLS}, 1.5rem)`;

    for (let r = 0; r < ROWS; r += 1) {
      for (let c = 0; c < COLS; c += 1) {
        const cell = document.createElement('button');
        cell.type = 'button';
        cell.className = cellClass(r, c);
        cell.dataset.row = String(r);
        cell.dataset.col = String(c);
        cell.setAttribute('aria-label', `Row ${r + 1}, column ${c + 1}`);
        fragment.appendChild(cell);
      }
    }
    gridEl.appendChild(fragment);
  }

  function editCell(r, c) {
    if (isAnimating) return;
    const coord = [r, c];
    const k = key(coord);

    if (mode === 'wall') {
      if (same(coord, start) || same(coord, goal)) return;
      walls.has(k) ? walls.delete(k) : walls.add(k);
    } else if (mode === 'start') {
      if (same(coord, goal)) return;
      walls.delete(k);
      start = coord;
    } else if (mode === 'goal') {
      if (same(coord, start)) return;
      walls.delete(k);
      goal = coord;
    }

    clearSearchVisuals();
  }

  function setBusy(busy) {
    isAnimating = busy;
    runBtn.disabled = busy;
    randomBtn.disabled = busy;
    resetBtn.disabled = busy;
  }

  async function animateSearch(result) {
    const token = ++animationToken;
    visited.clear();
    path.clear();
    renderGrid();

    const delay = Number(speedEl.value);
    const special = new Set([key(start), key(goal)]);

    for (const coord of result.visited) {
      if (token !== animationToken) return;
      const k = key(coord);
      if (!special.has(k)) visited.add(k);
      visitedMetric.textContent = String(visited.size + 1);
      renderGrid();
      await sleep(delay);
    }

    if (!result.found) {
      foundMetric.textContent = 'No path';
      pathMetric.textContent = '—';
      setStatus('No path exists for the current wall layout.', 'error');
      return;
    }

    for (const coord of result.path) {
      if (token !== animationToken) return;
      const k = key(coord);
      if (!special.has(k)) path.add(k);
      renderGrid();
      await sleep(Math.max(15, delay));
    }

    foundMetric.textContent = 'Found';
    visitedMetric.textContent = String(result.metrics.visited_nodes);
    pathMetric.textContent = String(result.metrics.path_length);
    setStatus(`Path found using ${result.algorithm.toUpperCase()}.`, 'success');
  }

  async function runSearch() {
    if (isAnimating) return;
    clearSearchVisuals();
    setBusy(true);
    setStatus('Searching…');

    const payload = {
      algorithm: algorithmEl.value,
      rows: ROWS,
      cols: COLS,
      start,
      goal,
      walls: [...walls].map((item) => item.split(',').map(Number)),
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const data = await response.json().catch(() => ({ error: 'Invalid server response.' }));
      if (!response.ok) throw new Error(data.error || 'Search request failed.');

      await animateSearch(data);
    } catch (error) {
      if (error.name === 'AbortError') {
        setStatus('The search request timed out.', 'error');
      } else {
        setStatus(error.message || 'Search failed.', 'error');
      }
    } finally {
      setBusy(false);
    }
  }

  function randomWalls() {
    if (isAnimating) return;
    walls.clear();
    const count = Math.floor(ROWS * COLS * MAX_WALL_DENSITY);
    while (walls.size < count) {
      const coord = [Math.floor(Math.random() * ROWS), Math.floor(Math.random() * COLS)];
      if (!same(coord, start) && !same(coord, goal)) walls.add(key(coord));
    }
    clearSearchVisuals();
    setStatus('Random walls generated.');
  }

  function resetGrid() {
    if (isAnimating) return;
    start = [10, 4];
    goal = [10, 25];
    walls.clear();
    clearSearchVisuals();
    setStatus('Grid reset.');
  }

  gridEl.addEventListener('pointerdown', (event) => {
    const cell = event.target.closest('[data-row][data-col]');
    if (!cell) return;
    isPointerDown = true;
    editCell(Number(cell.dataset.row), Number(cell.dataset.col));
  });

  gridEl.addEventListener('pointerover', (event) => {
    if (!isPointerDown || mode !== 'wall') return;
    const cell = event.target.closest('[data-row][data-col]');
    if (!cell) return;
    editCell(Number(cell.dataset.row), Number(cell.dataset.col));
  });

  window.addEventListener('pointerup', () => { isPointerDown = false; });
  modeButtons.forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode)));
  speedEl.addEventListener('input', () => { speedLabelEl.textContent = `${speedEl.value} ms`; });
  runBtn.addEventListener('click', runSearch);
  clearPathBtn.addEventListener('click', () => {
    clearSearchVisuals();
    setStatus('Search visualization cleared.');
  });
  randomBtn.addEventListener('click', randomWalls);
  resetBtn.addEventListener('click', resetGrid);

  setMode('wall');
  renderGrid();
})();
