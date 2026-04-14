/**
 * Main app — wires up the UI, Three.js scene, API, WebSocket, and 2D fallback.
 */
import { initScene, buildRoom, syncObjects, highlightObject } from './scene.js';
import { FURNITURE_EMOJIS } from './furniture.js';
import { sendCommand, resetRoom, getCatalog, createWebSocket, checkLLMStatus } from './api.js';

// ─────────────────────── State ──────────────────────────────────────────────
let currentState = null;
let is3D = true;
let catalog = {};
let ws = null;

// ─────────────────────── DOM refs ───────────────────────────────────────────
const canvas3d      = document.getElementById('three-canvas');
const canvas2d      = document.getElementById('canvas-2d');
const chatHistory   = document.getElementById('chat-history');
const commandInput  = document.getElementById('command-input');
const sendBtn       = document.getElementById('send-btn');
const loadingOverlay= document.getElementById('loading-overlay');
const wsStatus      = document.getElementById('ws-status');
const wsLabel       = document.getElementById('ws-label');
const wsDot         = wsStatus.querySelector('.dot');
const objectCount   = document.getElementById('object-count');
const statRoom      = document.getElementById('stat-room');
const statObjects   = document.getElementById('stat-objects');
const statLast      = document.getElementById('stat-last');
const inventoryList = document.getElementById('inventory-list');
const catalogGrid   = document.getElementById('catalog-grid');
const viewLabel     = document.getElementById('view-label');
const btnToggleView = document.getElementById('btn-toggle-view');
const btnReset      = document.getElementById('btn-reset');

// ─────────────────────── Init ───────────────────────────────────────────────
async function init() {
  // Boot 3D scene
  initScene(canvas3d);

  // Load catalog
  try {
    catalog = await getCatalog();
    renderCatalog(catalog);
  } catch (e) {
    console.warn('Could not load catalog:', e);
  }

  // Check LLM status asynchronously
  checkLLM();

  // Connect WebSocket
  connectWS();

  // Event listeners
  sendBtn.addEventListener('click', handleSend);
  commandInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });

  btnToggleView.addEventListener('click', toggleView);
  btnReset.addEventListener('click', handleReset);

  // Quick command chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      commandInput.value = chip.dataset.cmd;
      handleSend();
    });
  });
}

// ─────────────────────── WebSocket ──────────────────────────────────────────
function connectWS() {
  setWsStatus('connecting');
  try {
    ws = createWebSocket(handleWSMessage);

    ws.addEventListener('open', () => setWsStatus('connected'));
    ws.addEventListener('close', () => {
      setWsStatus('error');
      setTimeout(connectWS, 3000); // auto-reconnect
    });
    ws.addEventListener('error', () => setWsStatus('error'));
  } catch (e) {
    setWsStatus('error');
    setTimeout(connectWS, 3000);
  }
}

function setWsStatus(status) {
  wsDot.className = 'dot dot-' + status;
  wsLabel.textContent = {
    connecting: 'Connecting…',
    connected:  'Live',
    error:      'Offline',
  }[status] || status;
}

function handleWSMessage(data) {
  if (data.type === 'state_update') {
    applyState(data.state);
  }
}

async function checkLLM() {
  const dot = document.getElementById('llm-dot');
  const label = document.getElementById('llm-label');
  label.textContent = 'Checking…';
  dot.className = 'dot dot-connecting';
  
  try {
    const res = await checkLLMStatus();
    if (res.connected) {
      dot.className = 'dot dot-connected';
      label.textContent = 'LLM OK';
      document.getElementById('llm-status').title = `Connected to ${res.model}`;
    } else {
      dot.className = 'dot dot-error';
      label.textContent = 'LLM Err';
      document.getElementById('llm-status').title = res.error || 'Check API Key';
    }
  } catch (e) {
    dot.className = 'dot dot-error';
    label.textContent = 'LLM Fail';
    document.getElementById('llm-status').title = 'Failed to reach backend';
  }
}

// ─────────────────────── State rendering ────────────────────────────────────
function applyState(state) {
  currentState = state;

  // Update 3D scene
  if (state.room) buildRoom(state.room);
  if (state.objects) syncObjects(state.objects);

  // Update stats bar
  if (state.room) {
    statRoom.textContent = `${state.room.width} × ${state.room.height} m`;
  }
  statObjects.textContent = (state.objects || []).length;
  const la = state.last_action;
  statLast.textContent = la?.type ? `${la.type} ${la.object_id || ''}` : '—';

  // Update inventory
  renderInventory(state.objects || []);
  objectCount.textContent = `${(state.objects || []).length} items`;

  // Update 2D if visible
  if (!is3D) render2D(state);
}

// ─────────────────────── Command handling ───────────────────────────────────
async function handleSend() {
  const cmd = commandInput.value.trim();
  if (!cmd) return;

  commandInput.value = '';
  commandInput.disabled = true;
  sendBtn.disabled = true;

  // Show user message
  appendMessage('user', cmd);

  // Show typing indicator
  const typingId = showTyping();
  showLoading(true);

  try {
    const result = await sendCommand(cmd);
    removeTyping(typingId);
    showLoading(false);

    const msg = result.message || '✅ Done!';
    const isError = msg.startsWith('⚠️') || msg.startsWith('❌');
    appendMessage('assistant', msg, isError ? 'error' : 'success');

    // State is already applied via WebSocket, but apply directly if needed
    if (result.state && !ws?.readyState === WebSocket.OPEN) {
      applyState(result.state);
    }
  } catch (err) {
    removeTyping(typingId);
    showLoading(false);
    appendMessage(
      'assistant',
      `⚠️ Could not connect to backend. Make sure the server is running on port 8000.\n\n<small>${err.message}</small>`,
      'error'
    );
  } finally {
    commandInput.disabled = false;
    sendBtn.disabled = false;
    commandInput.focus();
  }
}

async function handleReset() {
  if (!confirm('Reset the room? All furniture will be removed.')) return;
  try {
    const result = await resetRoom();
    applyState(result.state);
    appendMessage('assistant', '🔄 Room has been reset. Starting fresh!');
  } catch (e) {
    appendMessage('assistant', `⚠️ Reset failed: ${e.message}`, 'error');
  }
}

// ─────────────────────── Chat UI ────────────────────────────────────────────
function appendMessage(role, text, bubbleClass = '') {
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '👤' : '🤖';

  const bubble = document.createElement('div');
  bubble.className = `bubble ${bubbleClass}`;
  bubble.innerHTML = _formatText(text);

  div.appendChild(avatar);
  div.appendChild(bubble);
  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return div;
}

function showTyping() {
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'chat-message assistant';
  div.id = id;
  div.innerHTML = `
    <div class="avatar">🤖</div>
    <div class="bubble typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function showLoading(show) {
  loadingOverlay.style.display = show ? 'flex' : 'none';
}

function _formatText(text) {
  return text
    .replace(/\n/g, '<br/>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.*?)_/g, '<em>$1</em>');
}

// ─────────────────────── Inventory ──────────────────────────────────────────
function renderInventory(objects) {
  if (objects.length === 0) {
    inventoryList.innerHTML = '<p class="empty-inventory">No furniture placed yet.</p>';
    return;
  }

  inventoryList.innerHTML = '';
  for (const obj of objects) {
    const item = document.createElement('div');
    item.className = 'inv-item';
    item.dataset.id = obj.id;

    const dot = document.createElement('div');
    dot.className = 'inv-color';
    dot.style.background = obj.color;

    const info = document.createElement('div');
    info.className = 'inv-info';
    info.innerHTML = `
      <div class="inv-name">${obj.description || obj.type}</div>
      <div class="inv-pos">${obj.id} · (${obj.x.toFixed(1)}, ${obj.z.toFixed(1)})</div>`;

    const del = document.createElement('button');
    del.className = 'inv-delete';
    del.title = 'Delete';
    del.textContent = '✕';
    del.addEventListener('click', async (e) => {
      e.stopPropagation();
      commandInput.value = `Delete ${obj.id}`;
      handleSend();
    });

    item.appendChild(dot);
    item.appendChild(info);
    item.appendChild(del);

    item.addEventListener('click', () => {
      highlightObject(obj.id);
      document.querySelectorAll('.inv-item').forEach(i => i.classList.remove('highlighted'));
      item.classList.add('highlighted');
    });

    inventoryList.appendChild(item);
  }
}

// ─────────────────────── Catalog ────────────────────────────────────────────
function renderCatalog(cat) {
  catalogGrid.innerHTML = '';
  for (const [type, def] of Object.entries(cat)) {
    const item = document.createElement('div');
    item.className = 'catalog-item';
    item.title = def.description;

    const emoji = FURNITURE_EMOJIS[type] || '📦';
    item.innerHTML = `
      <div class="catalog-emoji">${emoji}</div>
      <div class="catalog-name">${type.replace(/_/g, ' ')}</div>`;

    item.addEventListener('click', () => {
      commandInput.value = `Add a ${type.replace(/_/g, ' ')}`;
      commandInput.focus();
    });

    catalogGrid.appendChild(item);
  }
}

// ─────────────────────── View toggle ────────────────────────────────────────
function toggleView() {
  is3D = !is3D;
  canvas3d.style.display = is3D ? 'block' : 'none';
  canvas2d.style.display = is3D ? 'none' : 'block';
  viewLabel.textContent = is3D ? '3D View' : '2D View';

  if (!is3D && currentState) render2D(currentState);
}

function render2D(state) {
  const ctx = canvas2d.getContext('2d');
  const container = canvas2d.parentElement.getBoundingClientRect();
  canvas2d.width = container.width;
  canvas2d.height = container.height;

  if (!state?.room) return;
  const rw = state.room.width;
  const rh = state.room.height;

  // Scale to fit canvas with padding
  const pad = 60;
  const scale = Math.min((canvas2d.width - pad * 2) / rw, (canvas2d.height - pad * 2) / rh);
  const ox = (canvas2d.width - rw * scale) / 2;
  const oy = (canvas2d.height - rh * scale) / 2;

  // Background
  ctx.fillStyle = '#080d1c';
  ctx.fillRect(0, 0, canvas2d.width, canvas2d.height);

  // Room floor
  ctx.fillStyle = '#1a2240';
  ctx.strokeStyle = '#2a3a6a';
  ctx.lineWidth = 2;
  roundRect(ctx, ox, oy, rw * scale, rh * scale, 8);
  ctx.fill();
  ctx.stroke();

  // Grid
  ctx.strokeStyle = '#1e2d55';
  ctx.lineWidth = 0.5;
  for (let x = 0; x <= rw; x++) {
    ctx.beginPath();
    ctx.moveTo(ox + x * scale, oy);
    ctx.lineTo(ox + x * scale, oy + rh * scale);
    ctx.stroke();
  }
  for (let z = 0; z <= rh; z++) {
    ctx.beginPath();
    ctx.moveTo(ox, oy + z * scale);
    ctx.lineTo(ox + rw * scale, oy + z * scale);
    ctx.stroke();
  }

  // Furniture
  for (const obj of state.objects || []) {
    const fx = ox + obj.x * scale;
    const fz = oy + obj.z * scale;
    const fw = obj.w * scale;
    const fd = obj.d * scale;

    ctx.save();
    ctx.translate(fx + fw / 2, fz + fd / 2);
    ctx.rotate((obj.rotation || 0) * Math.PI / 180);

    ctx.fillStyle = obj.color;
    ctx.strokeStyle = 'rgba(255,255,255,0.25)';
    ctx.lineWidth = 1;
    roundRect(ctx, -fw / 2, -fd / 2, fw, fd, 4);
    ctx.fill();
    ctx.stroke();

    // Label
    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    ctx.font = `bold ${Math.max(9, Math.min(13, fw / 4))}px Inter`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(obj.type.replace(/_/g, ' '), 0, 0);
    ctx.restore();
  }

  // Dimension labels
  ctx.fillStyle = '#4b5980';
  ctx.font = '11px JetBrains Mono, monospace';
  ctx.textAlign = 'center';
  ctx.fillText(`${rw}m`, ox + rw * scale / 2, oy + rh * scale + 20);
  ctx.save();
  ctx.translate(ox - 20, oy + rh * scale / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(`${rh}m`, 0, 0);
  ctx.restore();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

// ─────────────────────── Boot ───────────────────────────────────────────────
init().catch(console.error);
