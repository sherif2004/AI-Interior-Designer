/**
 * Version comparison module — save, list, and diff two design snapshots
 * in a split-screen 2D canvas view.
 */

let _versionsPanel = null;

// ─────────────────────── Panel bootstrap ────────────────────────────────────

export function initVersionsPanel(container) {
  _versionsPanel = container;
  _versionsPanel.innerHTML = _buildPanelHTML();
  _bindEvents();
  refreshVersionsList();
}

function _buildPanelHTML() {
  return `
    <div class="ver-toolbar">
      <div class="ver-save-section">
        <input type="text" id="ver-name-input" class="ver-name-input" placeholder="Version name (e.g. Design A)…" />
        <button class="btn btn-accent" id="btn-ver-save">💾 Save Version</button>
      </div>
      <div class="ver-compare-section">
        <select id="ver-select-a" class="ver-select">
          <option value="">— Pick Version A —</option>
        </select>
        <span class="ver-vs">vs</span>
        <select id="ver-select-b" class="ver-select">
          <option value="">— Pick Version B —</option>
        </select>
        <button class="btn btn-ghost" id="btn-ver-diff">⚡ Compare</button>
      </div>
    </div>

    <div class="ver-list-section">
      <div class="ver-list-title">Saved Versions</div>
      <div id="ver-list" class="ver-list">
        <p class="empty-inventory">No versions saved yet.</p>
      </div>
    </div>

    <div id="ver-diff-result" class="ver-diff-result" style="display:none;">
      <div class="ver-diff-header">
        <span id="ver-diff-title">Comparing…</span>
        <button class="btn btn-ghost btn-small" id="btn-ver-diff-close">✕ Close</button>
      </div>
      <div class="ver-diff-canvases">
        <div class="ver-canvas-wrapper">
          <div class="ver-canvas-label" id="ver-label-a">Version A</div>
          <canvas id="ver-canvas-a"></canvas>
        </div>
        <div class="ver-canvas-wrapper">
          <div class="ver-canvas-label" id="ver-label-b">Version B</div>
          <canvas id="ver-canvas-b"></canvas>
        </div>
      </div>
      <div id="ver-diff-stats" class="ver-diff-stats"></div>
    </div>
  `;
}

function _bindEvents() {
  document.getElementById('btn-ver-save').addEventListener('click', handleSaveVersion);
  document.getElementById('btn-ver-diff').addEventListener('click', handleDiff);
  document.getElementById('btn-ver-diff-close').addEventListener('click', () => {
    document.getElementById('ver-diff-result').style.display = 'none';
  });
}

// ─────────────────────── API calls ──────────────────────────────────────────

async function refreshVersionsList() {
  try {
    const res = await fetch('/versions');
    const data = await res.json();
    renderVersionsList(data.versions || []);
    populateSelects(data.versions || []);
  } catch (e) {
    console.warn('Could not load versions:', e);
  }
}

async function handleSaveVersion() {
  const nameInput = document.getElementById('ver-name-input');
  const name = nameInput.value.trim();
  if (!name) { alert('Please enter a version name.'); return; }

  const btn = document.getElementById('btn-ver-save');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    const res = await fetch('/versions/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    const data = await res.json();
    if (data.success) {
      nameInput.value = '';
      showVersionToast(`✅ Saved "${data.version.name}"`);
      refreshVersionsList();
    }
  } catch (e) {
    alert('Error saving version: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '💾 Save Version';
  }
}

async function handleDiff() {
  const a = document.getElementById('ver-select-a').value;
  const b = document.getElementById('ver-select-b').value;
  if (!a || !b) { alert('Please select both versions to compare.'); return; }
  if (a === b) { alert('Please select two different versions.'); return; }

  try {
    const res = await fetch(`/versions/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Diff failed');
    }
    const diff = await res.json();
    renderDiff(diff);
  } catch (e) {
    alert('Error comparing versions: ' + e.message);
  }
}

async function deleteVersion(id) {
  if (!confirm(`Delete version "${id}"?`)) return;
  try {
    await fetch(`/versions/${id}`, { method: 'DELETE' });
    refreshVersionsList();
  } catch (e) {
    alert('Error deleting version.');
  }
}

// ─────────────────────── Rendering ──────────────────────────────────────────

function renderVersionsList(versions) {
  const list = document.getElementById('ver-list');
  if (!versions.length) {
    list.innerHTML = '<p class="empty-inventory">No versions saved yet.</p>';
    return;
  }
  list.innerHTML = versions.map(v => `
    <div class="ver-item">
      <div class="ver-item-info">
        <div class="ver-item-name">${v.name}</div>
        <div class="ver-item-meta">${v.object_count} items · ${v.theme} · ${_formatDate(v.saved_at)}</div>
      </div>
      <div class="ver-item-actions">
        <button class="btn btn-ghost btn-xs" onclick="loadVersionToRoom('${v.id}')">📂 Load</button>
        <button class="btn btn-danger btn-xs" onclick="window._deleteVersion('${v.id}')">✕</button>
      </div>
    </div>
  `).join('');
}

function populateSelects(versions) {
  const selects = ['ver-select-a', 'ver-select-b'];
  for (const selId of selects) {
    const sel = document.getElementById(selId);
    const current = sel.value;
    sel.innerHTML = `<option value="">— Pick a Version —</option>` +
      versions.map(v => `<option value="${v.id}" ${v.id === current ? 'selected' : ''}>${v.name}</option>`).join('');
  }
}

function renderDiff(diff) {
  const panel = document.getElementById('ver-diff-result');
  panel.style.display = 'block';

  document.getElementById('ver-diff-title').textContent =
    `${diff.version_a.name}  vs  ${diff.version_b.name}`;
  document.getElementById('ver-label-a').textContent = diff.version_a.name;
  document.getElementById('ver-label-b').textContent = diff.version_b.name;

  const statsEl = document.getElementById('ver-diff-stats');
  statsEl.innerHTML = `
    <span class="diff-badge diff-added">+${diff.added.length} added</span>
    <span class="diff-badge diff-removed">−${diff.removed.length} removed</span>
    <span class="diff-badge diff-moved">↔ ${diff.moved.length} moved</span>
    <span class="diff-badge diff-unchanged">= ${diff.unchanged.length} same</span>
  `;

  _draw2DDiff('ver-canvas-a', diff.room_a, diff.version_a, diff, 'a');
  _draw2DDiff('ver-canvas-b', diff.room_b, diff.version_b, diff, 'b');

  panel.scrollIntoView({ behavior: 'smooth' });
}

function _draw2DDiff(canvasId, room, versionMeta, diff, side) {
  const versionData = diff[`version_${side}`];
  const versionFull = null; // we use the diff data to reconstruct objects

  const canvas = document.getElementById(canvasId);
  const parent = canvas.parentElement;
  canvas.width = parent.clientWidth || 320;
  canvas.height = 240;
  const ctx = canvas.getContext('2d');

  const rw = (room || {}).width || 8;
  const rh = (room || {}).height || 6;
  const pad = 30;
  const scale = Math.min((canvas.width - pad * 2) / rw, (canvas.height - pad * 2) / rh);
  const ox = (canvas.width - rw * scale) / 2;
  const oy = (canvas.height - rh * scale) / 2;

  // Background
  ctx.fillStyle = '#0d1425';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Floor
  ctx.fillStyle = (room?.floor_style?.color) || '#1a2240';
  ctx.strokeStyle = (room?.wall_style?.color) || '#2a3a6a';
  ctx.lineWidth = 2;
  ctx.fillRect(ox, oy, rw * scale, rh * scale);
  ctx.strokeRect(ox, oy, rw * scale, rh * scale);

  // Determine which version's object set to render
  const removedIds = new Set(diff.removed.map(o => o.id));
  const addedIds = new Set(diff.added.map(o => o.id));
  const movedIds = new Set(diff.moved.map(o => o.id));

  // All objects for this side
  let objects = [];
  if (side === 'a') {
    objects = [...diff.removed, ...diff.unchanged.map(u => ({ ...u, x: 0, z: 0, w: 1, d: 1 }))];
    // For proper render, fetch full version
    objects = diff.removed.concat(diff.moved.map(m => ({ ...m, ...m.from, type: m.type, id: m.id, w: 1, d: 0.8 })));
  } else {
    objects = diff.added.concat(diff.moved.map(m => ({ ...m, ...m.to, type: m.type, id: m.id, w: 1, d: 0.8 })));
  }

  // Draw objects with color coding
  for (const obj of objects) {
    const x = ox + (obj.x || 0) * scale;
    const z = oy + (obj.z || 0) * scale;
    const w = (obj.w || 1) * scale;
    const d = (obj.d || 0.8) * scale;

    let fillColor = 'rgba(100,140,220,0.7)';
    if (addedIds.has(obj.id) && side === 'b') fillColor = 'rgba(50,200,100,0.8)';
    if (removedIds.has(obj.id) && side === 'a') fillColor = 'rgba(220,60,60,0.8)';
    if (movedIds.has(obj.id)) fillColor = 'rgba(240,180,40,0.8)';

    ctx.fillStyle = fillColor;
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 1;
    ctx.fillRect(x, z, w, d);
    ctx.strokeRect(x, z, w, d);

    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    ctx.font = `${Math.max(8, Math.min(11, w / 4))}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText((obj.type || '?').replace(/_/g, ' '), x + w / 2, z + d / 2);
  }

  // Legend
  ctx.fillStyle = 'rgba(255,255,255,0.6)';
  ctx.font = '10px Inter, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(`${rw}m × ${rh}m`, ox, oy - 8);
}

function _formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

function showVersionToast(msg) {
  const toast = document.createElement('div');
  toast.className = 'ver-toast';
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// Expose for inline onclick handlers
window._deleteVersion = deleteVersion;
window.loadVersionToRoom = async (id) => {
  if (!confirm('Load this version into the room? Current changes will be overridden.')) return;
  // Use the command interface to load via project mechanism
  window.dispatchEvent(new CustomEvent('app:command', { detail: { command: `Load project ${id}` } }));
};

export { refreshVersionsList };
