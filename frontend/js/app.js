/**
 * Main app — Phase 2 & 3 complete implementation.
 * Wires up: chat, 3D/2D view, WebSocket, budget panel, clearance warnings,
 * version comparison, AI render modal, blueprint import, product suggestions,
 * day/night slider, AR button, measurement mode.
 */
import {
  initScene, buildRoom, syncObjects, highlightObject,
  setTimeOfDay, setMeasureMode, clearMeasurementLines,
  showClearanceWarnings, clearClearanceWarnings, scene, renderer, camera, controls,
  setWalkthroughEnabled, isWalkthroughEnabled, SCALE
} from './scene.js';
import { FURNITURE_EMOJIS } from './furniture.js';
import {
  sendCommand, resetRoom, getCatalog, getProjects, getState, createWebSocket, checkLLMStatus,
  getMeasurements, getBudget,
  saveVersion, getVersions, getVersionDiff, deleteVersion as apiDeleteVersion,
  renderRoom, importBlueprint, getProducts, getRoomProducts, placeProduct, selectObject,
  importPhotoPreview, importPhoto, importSketch,
  multiRetailerSearch, createShare, listComments, addComment,
  exportDxf, exportMaterials,
  homeAddRoom, homeBudget, homeFlow
} from './api.js';
import { initVersionsPanel, refreshVersionsList } from './versions.js';
import { initAR } from './ar.js';
import { initVoiceInput } from './voice_input.js';
import { initSketchInput } from './sketch_input.js';

// ─────────────────────── State ───────────────────────────────────────────────
let currentState = null;
let is3D = true;
let catalog = {};
let ws = null;
let measureModeActive = false;
let activePanelId = 'panel-chat';
let draggedProduct = null;
let scrapeJobId = null;
let scrapePollTimer = null;
let productsPaging = { q: '', offset: 0, limit: 200, loading: false, done: false };

function proxiedImgUrl(url) {
  if (!url) return '';
  try { return `/img?u=${encodeURIComponent(url)}`; } catch { return url; }
}

function normalizeBuyUrl(url) {
  if (!url) return '';
  const u = String(url).trim();
  if (!u) return '';
  if (u.startsWith('http://') || u.startsWith('https://')) return u;
  if (u.startsWith('//')) return 'https:' + u;
  if (u.startsWith('/')) return 'https://www.ikea.com' + u;
  return 'https://www.ikea.com/' + u.replace(/^\/+/, '');
}

// ─────────────────────── DOM refs ───────────────────────────────────────────
const canvas3d      = document.getElementById('three-canvas');
const canvas2d      = document.getElementById('canvas-2d');
const viewerContainer = document.getElementById('viewer-container');
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
const styleTheme    = document.getElementById('style-theme');
const styleWalls    = document.getElementById('style-walls');
const styleFloor    = document.getElementById('style-floor');
const projectNameEl = document.getElementById('project-name');
const projectIdEl   = document.getElementById('project-id');
const projectCeilEl = document.getElementById('project-ceiling');
const projectListEl = document.getElementById('project-list');
const btnSaveProject= document.getElementById('btn-save-project');
const btnLoadProject= document.getElementById('btn-load-project');
const btnWalkthrough = document.getElementById('btn-walkthrough');
const btnRecord = document.getElementById('btn-record');

// Phase 5.2 commerce
const commerceQ = document.getElementById('commerce-q');
const btnCommerceSearch = document.getElementById('btn-commerce-search');
const commerceResults = document.getElementById('commerce-results');

// Phase 5.5 collab/export
const btnShareCreate = document.getElementById('btn-share-create');
const shareStatus = document.getElementById('share-status');
const commentText = document.getElementById('comment-text');
const btnCommentAdd = document.getElementById('btn-comment-add');
const commentsList = document.getElementById('comments-list');
const btnExportDxf = document.getElementById('btn-export-dxf');
const btnExportMaterials = document.getElementById('btn-export-materials');
const exportStatus = document.getElementById('export-status');

// Phase 5.6 home
const btnHomeAddRoom = document.getElementById('btn-home-add-room');
const btnHomeBudget = document.getElementById('btn-home-budget');
const btnHomeFlow = document.getElementById('btn-home-flow');
const homeStatus = document.getElementById('home-status');

// Inspector (right panel)
const inspectorSelected = document.getElementById('inspector-selected');
const inspectorType     = document.getElementById('inspector-type');
const inspectorPos      = document.getElementById('inspector-pos');
const inspectorRot      = document.getElementById('inspector-rot');
const inspectorSize     = document.getElementById('inspector-size');
const btnInspectorFocus = document.getElementById('btn-inspector-focus');
const btnInspectorDelete= document.getElementById('btn-inspector-delete');

// Phase 5.1: Room scan (photo)
const btnPhotoUpload = document.getElementById('btn-photo-upload');
const photoFileInput = document.getElementById('photo-file-input');
const photoPreviewEl = document.getElementById('photo-preview');
const btnPhotoPreview = document.getElementById('btn-photo-preview');
const btnPhotoApply = document.getElementById('btn-photo-apply');
let selectedPhotoFile = null;

// Phase 5.3: Voice
const btnVoiceToggle = document.getElementById('btn-voice-toggle');
const voiceStatusEl = document.getElementById('voice-status');
const voiceTranscriptEl = document.getElementById('voice-transcript');

// Phase 5.3: Sketch
const btnOpenSketch = document.getElementById('btn-open-sketch');
const sketchStatusEl = document.getElementById('sketch-status');

// ─────────────────────── Init ────────────────────────────────────────────────
async function init() {
  initScene(canvas3d);

  try { catalog = await getCatalog(); renderCatalog(catalog); } catch {}
  checkLLM();
  refreshProjectsList();

  try {
    const state = await getState();
    applyState(state);
  } catch {}

  connectWS();
  bindEvents();
  initSidePanels();
  initVersionsPanel(document.getElementById('panel-versions-inner'));
  initAR(scene, renderer);
  listenForVersionCommand();

  initVoiceInput({
    toggleButton: btnVoiceToggle,
    statusEl: voiceStatusEl,
    transcriptEl: voiceTranscriptEl,
    onText: (t) => {
      commandInput.value = t;
      handleSend();
    },
  });

  initSketchInput({
    openButton: btnOpenSketch,
    statusEl: sketchStatusEl,
    api: {
      importSketch: (img, apply) => importSketch(img, apply),
    },
    onApplied: (state) => applyState(state),
  });
}

function bindEvents() {
  sendBtn.addEventListener('click', handleSend);
  commandInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  });
  btnToggleView.addEventListener('click', toggleView);
  btnReset.addEventListener('click', handleReset);
  btnSaveProject.addEventListener('click', handleSaveProject);
  btnLoadProject.addEventListener('click', handleLoadProject);
  initProductDragDrop();
  initProductsPanel();

  // Quick command chips
  document.querySelectorAll('.chip').forEach(chip =>
    chip.addEventListener('click', () => { commandInput.value = chip.dataset.cmd; handleSend(); })
  );

  // Day/night slider
  const slider = document.getElementById('time-slider');
  const timeLabel = document.getElementById('time-label');
  if (slider) {
    slider.addEventListener('input', () => {
      const h = parseFloat(slider.value);
      setTimeOfDay(h);
      timeLabel.textContent = _formatHour(h);
    });
  }

  // Measure mode button
  const btnMeasure = document.getElementById('btn-measure');
  if (btnMeasure) {
    btnMeasure.addEventListener('click', () => {
      measureModeActive = !measureModeActive;
      setMeasureMode(measureModeActive);
      btnMeasure.classList.toggle('active', measureModeActive);
      btnMeasure.textContent = measureModeActive ? '📏 Click 2 Objects' : '📏 Measure';
      if (!measureModeActive) clearMeasurementLines();
    });
  }

  // AI Render button
  const btnRender = document.getElementById('btn-render');
  if (btnRender) btnRender.addEventListener('click', handleRender);

  // Blueprint upload
  const blueprintInput = document.getElementById('blueprint-file-input');
  const blueprintBtn = document.getElementById('btn-blueprint-upload');
  if (blueprintBtn && blueprintInput) {
    blueprintBtn.addEventListener('click', () => blueprintInput.click());
    blueprintInput.addEventListener('change', (e) => {
      if (e.target.files[0]) handleBlueprintUpload(e.target.files[0]);
    });
  }

  // Budget panel refresh
  const btnBudget = document.getElementById('btn-refresh-budget');
  if (btnBudget) btnBudget.addEventListener('click', refreshBudget);

  // Clearance toggle
  const btnClearance = document.getElementById('btn-clearance-toggle');
  if (btnClearance) btnClearance.addEventListener('click', refreshClearance);

  // Phase 5.4: Walkthrough toggle
  if (btnWalkthrough) {
    btnWalkthrough.addEventListener('click', () => {
      const enable = !isWalkthroughEnabled();
      setWalkthroughEnabled(enable, canvas3d);
      btnWalkthrough.classList.toggle('active', enable);
      btnWalkthrough.textContent = enable ? '🛑 Exit Walkthrough' : '🚶 Walkthrough';
    });
  }

  // Phase 5.4: Video record (client-side MediaRecorder)
  if (btnRecord) {
    let recorder = null;
    let chunks = [];
    btnRecord.addEventListener('click', async () => {
      try {
        if (recorder && recorder.state !== 'inactive') {
          recorder.stop();
          return;
        }
        const stream = canvas3d.captureStream(30);
        chunks = [];
        recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp9' });
        recorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: 'video/webm' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `walkthrough_${Date.now()}.webm`;
          a.click();
          setTimeout(() => URL.revokeObjectURL(url), 5000);
          btnRecord.textContent = '⏺ Record';
          btnRecord.classList.remove('active');
        };
        recorder.start(500);
        btnRecord.textContent = '⏹ Stop';
        btnRecord.classList.add('active');
      } catch (e) {
        appendMessage('assistant', `⚠️ Recording failed: ${e.message}`, 'error');
      }
    });
  }

  // Panel tabs
  document.querySelectorAll('.side-tab').forEach(tab => {
    tab.addEventListener('click', () => switchPanel(tab.dataset.panel));
  });

  // Phase 5.2: commerce search
  if (btnCommerceSearch) {
    btnCommerceSearch.addEventListener('click', async () => {
      const q = (commerceQ?.value || '').trim();
      if (!q) return;
      try {
        showLoading(true, 'Searching…');
        const res = await multiRetailerSearch({ q, retailers: 'ikea', limit: 40 });
        renderCommerceResults(res.products || []);
      } catch (e) {
        if (commerceResults) commerceResults.textContent = `Search failed: ${e.message}`;
      } finally {
        showLoading(false);
      }
    });
  }

  // Phase 5.5: share link
  if (btnShareCreate) {
    btnShareCreate.addEventListener('click', async () => {
      try {
        showLoading(true, 'Creating share link…');
        const res = await createShare('view');
        const url = `${window.location.origin}/share/${res.token}`;
        if (shareStatus) shareStatus.innerHTML = `Share token: <span class="mono">${res.token}</span><br/>Link: <a href="${url}" target="_blank" rel="noreferrer">${url}</a>`;
      } catch (e) {
        if (shareStatus) shareStatus.textContent = `Share failed: ${e.message}`;
      } finally {
        showLoading(false);
      }
    });
  }

  async function refreshComments() {
    try {
      const res = await listComments();
      renderComments(res.comments || []);
    } catch {}
  }

  if (btnCommentAdd) {
    btnCommentAdd.addEventListener('click', async () => {
      const text = (commentText?.value || '').trim();
      if (!text) return;
      try {
        const sel = currentState?.selected_object_id || '';
        await addComment({ text, x: 0, y: 0, z: 0, object_id: sel });
        if (commentText) commentText.value = '';
        await refreshComments();
      } catch (e) {
        appendMessage('assistant', `⚠️ Comment failed: ${e.message}`, 'error');
      }
    });
  }
  refreshComments();

  // Phase 5.5: exports
  if (btnExportDxf) {
    btnExportDxf.addEventListener('click', async () => {
      try {
        showLoading(true, 'Exporting DXF…');
        const blob = await exportDxf();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'room.dxf';
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 5000);
        if (exportStatus) exportStatus.textContent = 'DXF downloaded.';
      } catch (e) {
        if (exportStatus) exportStatus.textContent = `DXF export failed: ${e.message}`;
      } finally {
        showLoading(false);
      }
    });
  }
  if (btnExportMaterials) {
    btnExportMaterials.addEventListener('click', async () => {
      try {
        showLoading(true, 'Computing takeoff…');
        const res = await exportMaterials();
        if (exportStatus) exportStatus.textContent = `Floor: ${res.floor_area_m2}m² · Walls: ${res.wall_area_m2}m²`;
      } catch (e) {
        if (exportStatus) exportStatus.textContent = `Takeoff failed: ${e.message}`;
      } finally {
        showLoading(false);
      }
    });
  }

  // Phase 5.6: home
  if (btnHomeAddRoom) {
    btnHomeAddRoom.addEventListener('click', async () => {
      try {
        showLoading(true, 'Adding room…');
        const res = await homeAddRoom({ name: currentState?.project?.name || 'Room' });
        const n = Object.keys(res.home?.rooms || {}).length;
        if (homeStatus) homeStatus.textContent = `Home rooms: ${n}`;
      } catch (e) {
        if (homeStatus) homeStatus.textContent = `Add room failed: ${e.message}`;
      } finally {
        showLoading(false);
      }
    });
  }
  if (btnHomeBudget) {
    btnHomeBudget.addEventListener('click', async () => {
      try {
        showLoading(true, 'Computing home budget…');
        const res = await homeBudget();
        if (homeStatus) homeStatus.textContent = `Home budget: $${Math.round(res.total_low)}–$${Math.round(res.total_high)}`;
      } catch (e) {
        if (homeStatus) homeStatus.textContent = `Home budget failed: ${e.message}`;
      } finally {
        showLoading(false);
      }
    });
  }
  if (btnHomeFlow) {
    btnHomeFlow.addEventListener('click', async () => {
      try {
        showLoading(true, 'Computing flow…');
        const res = await homeFlow();
        const top = (res.hotspots?.[0] && `${res.hotspots[0][0]} (${res.hotspots[0][1]})`) || '—';
        if (homeStatus) homeStatus.textContent = `Connections: ${(res.connections || []).length} · Top: ${top}`;
      } catch (e) {
        if (homeStatus) homeStatus.textContent = `Flow failed: ${e.message}`;
      } finally {
        showLoading(false);
      }
    });
  }

  // Phase 5.1: photo upload/preview/apply
  if (btnPhotoUpload && photoFileInput) {
    btnPhotoUpload.addEventListener('click', () => photoFileInput.click());
    photoFileInput.addEventListener('change', (e) => {
      selectedPhotoFile = e.target.files?.[0] || null;
      if (photoPreviewEl) photoPreviewEl.textContent = selectedPhotoFile ? `Selected: ${selectedPhotoFile.name}` : '';
      if (btnPhotoPreview) btnPhotoPreview.disabled = !selectedPhotoFile;
      if (btnPhotoApply) btnPhotoApply.disabled = true;
    });
  }
  if (btnPhotoPreview) {
    btnPhotoPreview.addEventListener('click', async () => {
      if (!selectedPhotoFile) return;
      try {
        showLoading(true, 'Scanning photo…');
        const res = await importPhotoPreview(selectedPhotoFile);
        const summary = res.summary?.by_type ? JSON.stringify(res.summary.by_type) : '';
        const style = res.scan?.style ? `Style: ${res.scan.style}` : '';
        const conf = (res.scan?.confidence != null) ? `Confidence: ${Math.round(res.scan.confidence * 100)}%` : '';
        if (photoPreviewEl) photoPreviewEl.textContent = [style, conf, summary].filter(Boolean).join(' · ') || 'Preview ready.';
        if (btnPhotoApply) btnPhotoApply.disabled = false;
      } catch (err) {
        if (photoPreviewEl) photoPreviewEl.textContent = `Preview failed: ${err.message}`;
      } finally {
        showLoading(false);
      }
    });
  }
  if (btnPhotoApply) {
    btnPhotoApply.addEventListener('click', async () => {
      if (!selectedPhotoFile) return;
      try {
        showLoading(true, 'Applying scan…');
        const res = await importPhoto(selectedPhotoFile);
        if (res?.state) applyState(res.state);
        if (photoPreviewEl) photoPreviewEl.textContent = `Applied ${res.actions_applied || 0} action(s).`;
      } catch (err) {
        if (photoPreviewEl) photoPreviewEl.textContent = `Apply failed: ${err.message}`;
      } finally {
        showLoading(false);
      }
    });
  }

  if (btnInspectorFocus) {
    btnInspectorFocus.addEventListener('click', () => {
      const id = currentState?.selected_object_id;
      if (!id || !currentState?.objects?.length) return;
      const obj = currentState.objects.find(o => o.id === id);
      if (!obj || !camera || !controls) return;
      const x = (obj.x ?? 0) + (obj.w ?? (obj.size?.[0] ?? 1)) / 2;
      const z = (obj.z ?? 0) + (obj.d ?? (obj.size?.[1] ?? 1)) / 2;
      controls.target.set(x, 0, z);
      camera.position.set(x + 4.2, Math.max(4.8, (currentState?.room?.width || 10) * 0.5), z + 6.2);
      controls.update();
    });
  }
}

function showLoading(show, text = 'Processing…') {
  if (!loadingOverlay) return;
  loadingOverlay.style.display = show ? 'flex' : 'none';
  const t = loadingOverlay.querySelector('.loading-text');
  if (t) t.textContent = text;
}

function renderCommerceResults(products) {
  if (!commerceResults) return;
  if (!products || !products.length) {
    commerceResults.innerHTML = '<p class="empty-inventory">No results.</p>';
    return;
  }
  commerceResults.innerHTML = '';
  for (const p of products.slice(0, 40)) {
    const row = document.createElement('div');
    row.className = 'inv-item';
    row.innerHTML = `
      <div class="inv-info">
        <div><strong>${p.name || p.id}</strong> <span class="text-muted">(${p.retailer || ''})</span></div>
        <div class="text-muted mono">${p.price != null ? p.price : '—'} ${p.currency || ''}</div>
      </div>
      <button class="btn btn-outline btn-tiny" title="Open product" ${p.buy_url ? '' : 'disabled'}>View</button>
    `;
    const btn = row.querySelector('button');
    if (btn && p.buy_url) btn.addEventListener('click', () => window.open(p.buy_url, '_blank', 'noreferrer'));
    commerceResults.appendChild(row);
  }
}

function renderComments(items) {
  if (!commentsList) return;
  if (!items || !items.length) {
    commentsList.innerHTML = '<p class="empty-inventory">No comments yet.</p>';
    return;
  }
  commentsList.innerHTML = '';
  for (const c of items.slice().reverse().slice(0, 50)) {
    const row = document.createElement('div');
    row.className = 'inv-item';
    row.innerHTML = `
      <div class="inv-info">
        <div><strong>${c.text}</strong></div>
        <div class="text-muted mono">${c.object_id || ''}</div>
      </div>
    `;
    commentsList.appendChild(row);
  }
}

function initProductsPanel() {
  const btnLive = document.getElementById('btn-live-scrape');
  const btnSearch = document.getElementById('btn-products-search');
  const searchInput = document.getElementById('products-search');
  if (btnLive) btnLive.addEventListener('click', () => startLiveScrape());
  if (btnSearch) btnSearch.addEventListener('click', () => {
    const q = (searchInput?.value || '').trim();
    productsPaging = { ...productsPaging, q, offset: 0, done: false };
    loadProductsPage(true).catch(() => {});
  });
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') btnSearch?.click();
    });
  }
}

function listenForVersionCommand() {
  window.addEventListener('app:command', (e) => {
    commandInput.value = e.detail.command;
    handleSend();
  });
}

// ─────────────────────── Panel Tabs ─────────────────────────────────────────
function initSidePanels() {
  switchPanel('panel-chat');
}

function switchPanel(panelId) {
  activePanelId = panelId;
  document.querySelectorAll('.side-panel-content').forEach(p => p.classList.remove('active-panel'));
  document.querySelectorAll('.side-tab').forEach(t => t.classList.toggle('active', t.dataset.panel === panelId));
  const target = document.getElementById(panelId);
  if (target) target.classList.add('active-panel');

  if (panelId === 'panel-budget') refreshBudget();
  if (panelId === 'panel-clearance') refreshClearance();
  if (panelId === 'panel-versions') refreshVersionsList();
  if (panelId === 'panel-products') refreshRoomProducts();
}

// ─────────────────────── WebSocket ──────────────────────────────────────────
function connectWS() {
  setWsStatus('connecting');
  try {
    ws = createWebSocket(handleWSMessage);
    ws.addEventListener('open', () => setWsStatus('connected'));
    ws.addEventListener('close', () => { setWsStatus('error'); setTimeout(connectWS, 3000); });
    ws.addEventListener('error', () => setWsStatus('error'));
  } catch {
    setWsStatus('error');
    setTimeout(connectWS, 3000);
  }
}

function setWsStatus(status) {
  wsDot.className = 'dot dot-' + status;
  wsLabel.textContent = { connecting: 'Connecting…', connected: 'Live', error: 'Offline' }[status] || status;
}

function handleWSMessage(data) {
  if (data.type === 'state_update') applyState(data.state);
}

async function checkLLM() {
  const dot = document.getElementById('llm-dot');
  const label = document.getElementById('llm-label');
  dot.className = 'dot dot-connecting';
  label.textContent = 'Checking…';
  try {
    const res = await checkLLMStatus();
    dot.className = res.connected ? 'dot dot-connected' : 'dot dot-error';
    label.textContent = res.connected ? 'LLM OK' : 'LLM Err';
    document.getElementById('llm-status').title = res.connected ? `Connected to ${res.model}` : (res.error || 'Check API Key');
  } catch {
    dot.className = 'dot dot-error';
    label.textContent = 'LLM Fail';
  }
}

// ─────────────────────── State rendering ────────────────────────────────────
function applyState(state) {
  currentState = state;
  if (state.room) buildRoom(state.room);
  if (state.objects) syncObjects(state.objects);

  if (state.room) {
    statRoom.textContent = `${state.room.width} × ${state.room.height} m`;
    styleTheme.textContent = (state.room.theme || 'custom').replace(/_/g, ' ');
    styleWalls.textContent = state.room.wall_style?.label || 'default walls';
    styleFloor.textContent = state.room.floor_style?.label || 'default floor';
    projectCeilEl.textContent = `${(state.room.ceiling_height || 3.0).toFixed(1)}m`;
  }
  if (state.project) {
    projectNameEl.textContent = state.project.name || 'My Home Project';
    projectIdEl.textContent = state.project.id || 'default_project';
  }
  statObjects.textContent = (state.objects || []).length;
  const la = state.last_action;
  statLast.textContent = la?.type ? `${la.type} ${la.object_id || ''}` : '—';

  renderInventory(state.objects || []);
  objectCount.textContent = `${(state.objects || []).length} items`;
  if (state.selected_object_id) highlightObject(state.selected_object_id);
  updateInspector(state);
  if (!is3D) render2D(state);

  // Show clearance warnings if active
  if (state.clearance_warnings?.length > 0) {
    showClearanceWarnings(state.clearance_warnings, state.objects || []);
    updateClearanceBadge(state.clearance_warnings, state.accessibility_score);
  } else {
    clearClearanceWarnings();
    updateClearanceBadge([], 100);
  }
}

function updateInspector(state) {
  if (!inspectorSelected) return;
  const id = state?.selected_object_id || '';
  const obj = id ? (state.objects || []).find(o => o.id === id) : null;

  inspectorSelected.textContent = id || '—';
  inspectorType.textContent = obj?.type ? String(obj.type).replace(/_/g, ' ') : '—';
  const x = (obj?.x ?? null);
  const z = (obj?.z ?? null);
  inspectorPos.textContent = (x != null && z != null) ? `${x.toFixed?.(2) ?? x}, ${z.toFixed?.(2) ?? z} m` : '—';
  inspectorRot.textContent = (obj?.rotation != null) ? `${Number(obj.rotation).toFixed(0)}°` : '—';
  const w = (obj?.w ?? obj?.size?.[0] ?? null);
  const d = (obj?.d ?? obj?.size?.[1] ?? null);
  inspectorSize.textContent = (w != null && d != null) ? `${Number(w).toFixed(2)} × ${Number(d).toFixed(2)} m` : '—';

  if (btnInspectorFocus) btnInspectorFocus.disabled = !obj;
  if (btnInspectorDelete) btnInspectorDelete.disabled = !obj;
}

function initProductDragDrop() {
  if (!viewerContainer) return;

  viewerContainer.addEventListener('dragover', (e) => {
    if (!draggedProduct) return;
    e.preventDefault();
    viewerContainer.classList.add('drag-over');
  });

  viewerContainer.addEventListener('dragleave', () => {
    viewerContainer.classList.remove('drag-over');
  });

  viewerContainer.addEventListener('drop', async (e) => {
    if (!draggedProduct || !currentState?.room) return;
    e.preventDefault();
    viewerContainer.classList.remove('drag-over');

    const rect = viewerContainer.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width;
    const nz = (e.clientY - rect.top) / rect.height;
    const x = Math.max(0.3, Math.min(currentState.room.width - 0.3, nx * currentState.room.width));
    const z = Math.max(0.3, Math.min(currentState.room.height - 0.3, nz * currentState.room.height));

    try {
      await placeProduct(draggedProduct.id, x, z);
      appendMessage('assistant', `🛋️ Placed ${draggedProduct.name} in the room.`, 'success');
      if (activePanelId === 'panel-products') refreshRoomProducts();
    } catch (err) {
      appendMessage('assistant', `⚠️ Could not place product: ${err.message}`, 'error');
    } finally {
      draggedProduct = null;
    }
  });
}

function updateClearanceBadge(warnings, score) {
  const badge = document.getElementById('clearance-badge');
  if (!badge) return;
  if (warnings.length === 0) {
    badge.style.display = 'none';
  } else {
    badge.style.display = 'flex';
    badge.textContent = `⚠️ ${warnings.length} clearance issue${warnings.length > 1 ? 's' : ''}`;
    badge.className = `clearance-badge ${warnings.some(w => w.severity === 'error') ? 'badge-error' : 'badge-warning'}`;
  }
  const scoreEl = document.getElementById('accessibility-score');
  if (scoreEl) {
    scoreEl.textContent = `${score}%`;
    scoreEl.className = `score-value ${score > 80 ? 'score-good' : score > 50 ? 'score-ok' : 'score-bad'}`;
  }
}

async function refreshProjectsList() {
  try {
    const result = await getProjects();
    renderProjectsList(result.projects || []);
  } catch {}
}

function renderProjectsList(projects) {
  if (!projects.length) {
    projectListEl.innerHTML = '<div class="project-list-desc">No saved projects yet.</div>';
    return;
  }
  projectListEl.innerHTML = '';
  for (const project of projects) {
    const item = document.createElement('div');
    item.className = 'project-list-item';
    item.innerHTML = `
      <div class="project-list-meta">
        <div class="project-list-name">${project.name || project.id}</div>
        <div class="project-list-desc">${(project.room_type || 'generic').replace(/_/g, ' ')} · ${(project.theme || 'custom').replace(/_/g, ' ')}</div>
      </div>
      <div class="project-value mono">${project.id}</div>`;
    item.addEventListener('click', () => { commandInput.value = `Load project ${project.id}`; commandInput.focus(); });
    projectListEl.appendChild(item);
  }
}

// ─────────────────────── Command handling ───────────────────────────────────
async function handleSend() {
  const cmd = commandInput.value.trim();
  if (!cmd) return;
  commandInput.value = '';
  commandInput.disabled = true;
  sendBtn.disabled = true;
  appendMessage('user', cmd);
  const typingId = showTyping();
  showLoading(true);
  try {
    const result = await sendCommand(cmd);
    removeTyping(typingId);
    showLoading(false);
    const msg = result.message || '✅ Done!';
    const isError = msg.startsWith('⚠️') || msg.startsWith('❌');
    appendMessage('assistant', msg, isError ? 'error' : 'success');
    if (result.state && (!ws || ws.readyState !== WebSocket.OPEN)) applyState(result.state);
    // Auto-refresh product panel if a product was just added
    if (activePanelId === 'panel-products') refreshRoomProducts();
  } catch (err) {
    removeTyping(typingId);
    showLoading(false);
    appendMessage('assistant', `⚠️ Could not connect to backend.\n\n<small>${err.message}</small>`, 'error');
  } finally {
    commandInput.disabled = false;
    sendBtn.disabled = false;
    commandInput.focus();
  }
}

async function handleSaveProject() {
  const name = prompt('Project name?', currentState?.project?.name || 'My Home Project');
  if (!name) return;
  commandInput.value = `Save this as ${name}`;
  await handleSend();
  refreshProjectsList();
}

async function handleLoadProject() {
  const id = prompt('Project ID to load?', currentState?.project?.id || 'default_project');
  if (!id) return;
  commandInput.value = `Load project ${id}`;
  await handleSend();
  refreshProjectsList();
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

// ─────────────────────── Phase 2: Budget Panel ──────────────────────────────
async function refreshBudget() {
  const budgetPanel = document.getElementById('budget-panel-inner');
  if (!budgetPanel) return;
  budgetPanel.innerHTML = '<p class="loading-text-sm">Loading…</p>';
  try {
    const data = await getBudget();
    renderBudgetPanel(data, budgetPanel);
  } catch (e) {
    budgetPanel.innerHTML = `<p class="empty-inventory">Error: ${e.message}</p>`;
  }
}

function renderBudgetPanel(data, container) {
  if (!data.items?.length) {
    container.innerHTML = '<p class="empty-inventory">No furniture placed yet.</p>';
    return;
  }
  const categorized = {};
  for (const item of data.items) {
    const cat = item.category || 'general';
    if (!categorized[cat]) categorized[cat] = [];
    categorized[cat].push(item);
  }
  let html = '';
  for (const [cat, items] of Object.entries(categorized)) {
    html += `<div class="budget-category"><div class="budget-cat-title">${_capitalize(cat.replace('_', ' '))}</div>`;
    for (const item of items) {
      html += `<div class="budget-item">
        <span class="budget-item-name">${FURNITURE_EMOJIS[item.type] || '📦'} ${item.description || item.type}</span>
        <span class="budget-item-price">$${item.price_low}–$${item.price_high}</span>
      </div>`;
    }
    html += '</div>';
  }
  html += `<div class="budget-total">
    <span>Estimated Total</span>
    <span class="budget-total-value">$${data.total_low.toLocaleString()} – $${data.total_high.toLocaleString()} USD</span>
  </div>
  <p class="budget-note">${data.note}</p>`;
  container.innerHTML = html;
}

// ─────────────────────── Phase 2: Clearance Panel ───────────────────────────
async function refreshClearance() {
  const panel = document.getElementById('clearance-panel-inner');
  if (!panel) return;
  panel.innerHTML = '<p class="loading-text-sm">Checking clearances…</p>';
  try {
    const data = await getMeasurements();
    renderClearancePanel(data, panel);
  } catch (e) {
    panel.innerHTML = `<p class="empty-inventory">Error: ${e.message}</p>`;
  }
}

function renderClearancePanel(data, container) {
  const warnings = data.clearance_warnings || [];
  const score = data.accessibility_score || 100;

  let html = `<div class="clearance-score-bar">
    <span class="clearance-score-label">Accessibility Score</span>
    <div class="clearance-score-track">
      <div class="clearance-score-fill" style="width:${score}%; background:${score > 80 ? '#2dcc71' : score > 50 ? '#f5c842' : '#e74c3c'}"></div>
    </div>
    <span class="clearance-score-pct">${score}%</span>
  </div>`;

  if (!warnings.length) {
    html += '<div class="clearance-ok">✅ All clearances look good!</div>';
  } else {
    html += `<div class="clearance-warning-list">`;
    for (const w of warnings) {
      const icon = w.severity === 'error' ? '🔴' : '🟡';
      html += `<div class="clearance-warning-item ${w.severity}">
        <span class="cw-icon">${icon}</span>
        <span class="cw-msg">${w.message}</span>
      </div>`;
    }
    html += '</div>';
  }

  if ((data.inter_object_distances || []).length) {
    html += `<div class="clearance-distances"><div class="clearance-dist-title">Inter-Object Gaps</div>`;
    for (const d of (data.inter_object_distances || []).slice(0, 8)) {
      const ok = d.sufficient;
      html += `<div class="dist-row ${ok ? '' : 'dist-warn'}">
        <span>${d.type_a} ↔ ${d.type_b}</span>
        <span class="dist-val">${d.gap_m}m ${ok ? '✅' : '⚠️'}</span>
      </div>`;
    }
    html += '</div>';
  }

  container.innerHTML = html;
}

// ─────────────────────── Phase 3: AI Render ─────────────────────────────────
async function handleRender() {
  const btn = document.getElementById('btn-render');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Rendering…'; }

  try {
    const result = await renderRoom();
    showRenderModal(result);
  } catch (e) {
    appendMessage('assistant', `⚠️ Render failed: ${e.message}`, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '✨ AI Render'; }
  }
}

function showRenderModal(result) {
  const existing = document.getElementById('render-modal');
  if (existing) existing.remove();

  const imgSrc = result.image_url || (result.image_b64 ? `data:image/png;base64,${result.image_b64}` : null);
  const modal = document.createElement('div');
  modal.id = 'render-modal';
  modal.className = 'render-modal-overlay';
  modal.innerHTML = `
    <div class="render-modal">
      <div class="render-modal-header">
        <h3>✨ AI Photoreal Render</h3>
        <button class="btn btn-ghost btn-small" onclick="document.getElementById('render-modal').remove()">✕ Close</button>
      </div>
      ${imgSrc ? `<img class="render-modal-img" src="${imgSrc}" alt="AI room render" />` : `<p class="render-no-img">Image not available. Provider: ${result.provider}</p>`}
      <div class="render-modal-meta">
        <div class="render-provider-badge">Provider: ${result.provider || 'unknown'}${result.note ? ' · ' + result.note : ''}</div>
        <details class="render-prompt-details">
          <summary>View Prompt</summary>
          <p class="render-prompt">${result.prompt || ''}</p>
        </details>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

// ─────────────────────── Phase 3: Blueprint Import ──────────────────────────
async function handleBlueprintUpload(file) {
  const statusEl = document.getElementById('blueprint-status');
  if (statusEl) { statusEl.textContent = '⏳ Analyzing floor plan…'; statusEl.className = 'blueprint-status loading'; }

  try {
    const result = await importBlueprint(file);
    if (!result.success) throw new Error(result.error || 'Import failed');

    const parsed = result.parsed;
    if (statusEl) {
      statusEl.textContent = `✅ Detected: ${parsed.width}m × ${parsed.height}m, ${parsed.room_type} · ${parsed.notes || ''}`;
      statusEl.className = 'blueprint-status success';
    }

    // Show confirmation before applying
    const apply = confirm(
      `Floor plan detected!\n\n` +
      `Room: ${parsed.width}m × ${parsed.height}m\n` +
      `Type: ${parsed.room_type}\n` +
      `Doors: ${parsed.doors?.length || 0}, Windows: ${parsed.windows?.length || 0}\n\n` +
      `Apply to current room?`
    );
    if (apply) {
      commandInput.value = `Make the room ${parsed.width} by ${parsed.height} meters`;
      await handleSend();
      appendMessage('assistant', `📐 Blueprint imported! Room set to ${parsed.width}×${parsed.height}m. ${parsed.notes || ''}`);
    }
  } catch (e) {
    if (statusEl) { statusEl.textContent = `❌ ${e.message}`; statusEl.className = 'blueprint-status error'; }
    appendMessage('assistant', `⚠️ Blueprint import failed: ${e.message}`, 'error');
  }
}

// ─────────────────────── Phase 3: Product Catalog ───────────────────────────
async function refreshRoomProducts() {
  const panel = document.getElementById('products-panel-inner');
  if (!panel) return;
  panel.innerHTML = '<p class="loading-text-sm">Loading IKEA products…</p>';
  try {
    // Prefer the paginated "all products" feed (works during live scraping)
    productsPaging = { ...productsPaging, offset: 0, done: false };
    await loadProductsPage(true);
    if (!panel.dataset.hasProducts) {
      // Fall back to room-based suggestions
    const data = await getRoomProducts(currentState);
    renderProductsPanel(data.suggestions || {}, panel);
    }
  } catch (e) {
    panel.innerHTML = `<p class="empty-inventory">Error: ${e.message}</p>`;
  }
}

async function startLiveScrape() {
  const statusEl = document.getElementById('scrape-status');
  const btn = document.getElementById('btn-live-scrape');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Scraping…'; }
  if (statusEl) statusEl.textContent = 'Starting live scrape…';

  try {
    const qs = new URLSearchParams({ cc: 'eg', lang: 'en', rate: '1.5' });
    const res = await fetch(`/catalog/refresh?${qs.toString()}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    scrapeJobId = data.job_id;
    if (statusEl) statusEl.textContent = `Live scrape started (job ${scrapeJobId}). Loading products…`;

    // Start paging from the top and keep appending as DB grows
    productsPaging = { ...productsPaging, offset: 0, done: false };
    await loadProductsPage(true);
    startScrapePolling();
  } catch (e) {
    if (statusEl) statusEl.textContent = `Scrape failed to start: ${e.message}`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '⚡ Live scrape'; }
  }
}

function startScrapePolling() {
  stopScrapePolling();
  scrapePollTimer = setInterval(async () => {
    if (!scrapeJobId) return;
    try {
      const res = await fetch(`/catalog/status/${encodeURIComponent(scrapeJobId)}`);
      const job = await res.json();
      const statusEl = document.getElementById('scrape-status');
      if (statusEl) {
        const pct = job.total_categories ? Math.round((job.done_categories / job.total_categories) * 100) : 0;
        statusEl.textContent = `${job.status} · ${pct}% · ${job.products_total} products · ${job.message || ''}`;
      }
      // Keep loading more pages while scraping is running
      if (job.status === 'running') {
        await loadProductsPage(false);
      } else if (job.status === 'finished' || job.status === 'error') {
        await loadProductsPage(false);
        stopScrapePolling();
      }
    } catch {
      // ignore transient errors
    }
  }, 1500);
}

function stopScrapePolling() {
  if (scrapePollTimer) clearInterval(scrapePollTimer);
  scrapePollTimer = null;
}

async function loadProductsPage(reset = false) {
  const panel = document.getElementById('products-panel-inner');
  if (!panel) return;
  if (productsPaging.loading) return;
  if (productsPaging.done && !reset) return;

  productsPaging.loading = true;
  try {
    if (reset) {
      panel.innerHTML = '';
      panel.dataset.hasProducts = '';
    }
    const params = new URLSearchParams({
      limit: String(productsPaging.limit),
      offset: String(productsPaging.offset),
      currency: 'EGP',
    });
    if (productsPaging.q) params.append('q', productsPaging.q);
    const res = await fetch(`/products/all?${params.toString()}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    const products = data.products || [];
    if (products.length) {
      panel.dataset.hasProducts = '1';
      appendProductsToPanel(products, panel, reset);
      productsPaging.offset += products.length;
      // If DB hasn't grown enough yet, this might return short pages; keep polling.
      productsPaging.done = productsPaging.offset >= (data.total || 0);
    } else {
      // If scraping is ongoing, empty page just means "not yet"; don't mark done.
      if (!scrapeJobId) productsPaging.done = true;
    }
  } finally {
    productsPaging.loading = false;
  }
}

function appendProductsToPanel(products, container, reset = false) {
  // Simple flat list (faster than grouping during live updates)
  if (reset) container.innerHTML = '';
  for (const p of products) {
    const card = document.createElement('div');
    card.className = 'catalog-item';
    card.style.padding = '0';
    card.draggable = true;
    const bgImage = p.image_url ? `url('${proxiedImgUrl(p.image_url)}')` : 'none';
    card.innerHTML = `
      <div style="height: 90px; background: ${bgImage} center/cover no-repeat; border-bottom: 1px solid var(--border);"></div>
      <div style="padding: 8px; font-size: 0.85em; display:flex; flex-direction:column; gap:6px;">
        <div style="font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${p.name || p.id}">${p.name || p.id}</div>
        <div style="color:var(--text-muted); font-size: 0.85em;">${formatPrice(p)}</div>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-primary btn-small" style="width:100%;">Add</button>
          ${p.buy_url ? `<a class="btn btn-ghost btn-small" style="width:100%; text-decoration:none; text-align:center;" href="${normalizeBuyUrl(p.buy_url)}" target="_blank" rel="noopener">View</a>` : ''}
        </div>
      </div>`;

    card.addEventListener('dragstart', () => { draggedProduct = p; viewerContainer?.classList.add('drag-over'); });
    card.addEventListener('dragend', () => { draggedProduct = null; viewerContainer?.classList.remove('drag-over'); });

    const addBtn = card.querySelector('button');
    addBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await placeProduct(p.id);
        appendMessage('assistant', `🛋️ Added ${p.name || p.id}`, 'success');
      } catch (err) {
        appendMessage('assistant', `⚠️ ${err.message}`, 'error');
      }
    });

    container.appendChild(card);
  }
}

function renderAllProductsPanel(products, container) {
  if (!products.length) {
    container.innerHTML = '<p class="empty-inventory">No IKEA products found.</p>';
    return;
  }
  container.innerHTML = '';
  // Group by category
  const byCategory = {};
  for (const p of products) {
    const cat = p.category || 'other';
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(p);
  }
  for (const [cat, items] of Object.entries(byCategory)) {
    const group = document.createElement('div');
    group.className = 'product-group';
    group.innerHTML = `<div class="product-group-title">${cat.toUpperCase()}</div>`;
    for (const p of items.slice(0, 8)) { // limit to 8 per category
      const card = document.createElement('div');
      card.className = 'catalog-item';
      card.style.padding = '0';
      card.draggable = true;
      const bgImage = p.image_url ? `url('${proxiedImgUrl(p.image_url)}')` : 'none';
      card.innerHTML = `
        <div style="height: 80px; background: ${bgImage} center/cover no-repeat; border-bottom: 1px solid var(--border);"></div>
        <div style="padding: 6px; font-size: 0.8em; display:flex; flex-direction:column; gap:4px;">
          <div style="font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${p.name}">${p.name}</div>
          <div style="color:var(--text-muted); font-size: 0.85em;">${formatPrice(p)} ${p.width_cm ? `· ${p.width_cm}cm` : ''}</div>
          <button class="btn btn-primary btn-small" style="width:100%; font-size:0.75em;">Add</button>
        </div>`;
      
      // drag handlers
      card.addEventListener('dragstart', () => { draggedProduct = p; viewerContainer?.classList.add('drag-over'); });
      card.addEventListener('dragend', () => { draggedProduct = null; viewerContainer?.classList.remove('drag-over'); });
      
      // add button
      const addBtn = card.querySelector('button');
      addBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        try {
          await placeProduct(p.id);
          appendMessage('assistant', `🛋️ Added ${p.name}`, 'success');
        } catch (err) {
          appendMessage('assistant', `⚠️ ${err.message}`, 'error');
        }
      });
      
      group.appendChild(card);
    }
    container.appendChild(group);
  }
}

function renderProductsPanel(suggestions, container) {
  if (!Object.keys(suggestions).length) {
    container.innerHTML = '<p class="empty-inventory">Add furniture to see product suggestions.</p>';
    return;
  }
  let html = '';
  for (const [objId, data] of Object.entries(suggestions)) {
    html += `<div class="product-group">
      <div class="product-group-title">${FURNITURE_EMOJIS[data.object_type] || '📦'} ${(data.object_type || '').replace(/_/g, ' ')}</div>`;
    for (const p of data.products) {
      html += `<div class="product-card">
        ${p.image ? `<img class="product-img" src="${p.image}" alt="${p.name}" loading="lazy" onerror="this.style.display='none'" />` : ''}
        <div class="product-info">
          <div class="product-name">${p.name}</div>
          <div class="product-brand">${p.brand} · ${p.width_m ? `${p.width_m}×${p.depth_m}m` : ''}</div>
          <div class="product-price">$${p.price}</div>
          ${p.url ? `<a class="product-link btn btn-ghost btn-xs" href="${p.url}" target="_blank" rel="noopener">View →</a>` : ''}
        </div>
      </div>`;
    }
    html += '</div>';
  }
  container.innerHTML = html;
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
      <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
    </div>`;
  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return id;
}

function removeTyping(id) { const el = document.getElementById(id); if (el) el.remove(); }
// (legacy helper removed — use showLoading(show, text) above)
function _formatText(text) {
  return text
    .replace(/\n/g, '<br/>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.*?)_/g, '<em>$1</em>');
}

// ─────────────────────── Inventory ──────────────────────────────────────────
function renderInventory(objects) {
  if (!objects.length) {
    inventoryList.innerHTML = '<p class="empty-inventory">No furniture placed yet.</p>';
    return;
  }
  inventoryList.innerHTML = '';
  for (const obj of objects) {
    const item = document.createElement('div');
    item.className = 'inv-item';
    item.dataset.id = obj.id;
    let mediaEl;
    if (obj.image_url) {
      mediaEl = document.createElement('img');
      mediaEl.className = 'inv-color'; 
      mediaEl.style.objectFit = 'cover';
      mediaEl.style.border = '1px solid rgba(255,255,255,0.1)';
      mediaEl.src = proxiedImgUrl(obj.image_url);
      mediaEl.loading = 'lazy';
      mediaEl.referrerPolicy = 'no-referrer';
    } else {
      mediaEl = document.createElement('div');
      mediaEl.className = 'inv-color';
      mediaEl.style.background = obj.color;
    }

    const priceText = obj.price_low ? ` <span style="color:#10b981; font-size:0.85em;">$${obj.price_low}</span>` : '';
    const displayName = obj.name || obj.description || obj.type;

    const info = document.createElement('div');
    info.className = 'inv-info';
    info.innerHTML = `
      <div class="inv-name" title="${displayName}">${displayName}${priceText}</div>
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

    // Shop button
    const shopBtn = document.createElement('button');
    shopBtn.className = 'inv-shop';
    shopBtn.title = 'Shop similar products';
    shopBtn.textContent = '🛍️';
    shopBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      switchPanel('panel-products');
    });

    item.appendChild(mediaEl);
    item.appendChild(info);
    item.appendChild(shopBtn);
    item.appendChild(del);
    item.addEventListener('click', async () => {
      highlightObject(obj.id);
      document.querySelectorAll('.inv-item').forEach(i => i.classList.remove('highlighted'));
      item.classList.add('highlighted');
      try {
        await selectObject(obj.id);
      } catch (e) {
        console.warn('Could not sync selection:', e);
      }
    });
    inventoryList.appendChild(item);
  }
}

// ─────────────────────── Catalog ────────────────────────────────────────────
function renderCatalog(data) {
  catalogGrid.innerHTML = '';
  const products = data.results || [];
  
  for (const obj of products) {
    const item = document.createElement('div');
    item.className = 'catalog-item';
    item.style.padding = '0';
    item.style.overflow = 'hidden';
    item.style.display = 'flex';
    item.style.flexDirection = 'column';
    item.title = `${obj.name} · $${obj.price}`;
    item.draggable = true;

    const bgImage = obj.image_url ? `url('${proxiedImgUrl(obj.image_url)}')` : 'none';
    
    item.innerHTML = `
      <div style="height: 100px; background: ${bgImage} center/cover no-repeat; border-bottom: 1px solid var(--border);"></div>
      <div style="padding: 8px; font-size: 0.9em; display:flex; flex-direction:column; gap:6px;">
        <div style="font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${obj.name}">${obj.name}</div>
        <div style="color:var(--text-muted); font-size: 0.85em;">${formatPrice(obj)}</div>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-primary btn-small catalog-add-btn" style="width:100%;">Add</button>
          <button class="btn btn-ghost btn-small catalog-chat-btn" style="width:100%;">Chat</button>
        </div>
      </div>`;

    item.addEventListener('dragstart', () => {
      draggedProduct = obj;
      viewerContainer?.classList.add('drag-over');
    });
    item.addEventListener('dragend', () => {
      draggedProduct = null;
      viewerContainer?.classList.remove('drag-over');
    });

    const btn = item.querySelector('.catalog-add-btn');
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await placeProduct(obj.id);
        appendMessage('assistant', `🛋️ Added ${obj.name} to the room.`, 'success');
        if (activePanelId === 'panel-products') refreshRoomProducts();
      } catch (err) {
        appendMessage('assistant', `⚠️ Could not add product: ${err.message}`, 'error');
      }
    });

    const chatBtn = item.querySelector('.catalog-chat-btn');
    chatBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      commandInput.value = `Add an IKEA ${obj.name}`;
      handleSend();
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
  const pad = 60;
  const scale = Math.min((canvas2d.width - pad * 2) / rw, (canvas2d.height - pad * 2) / rh);
  const ox = (canvas2d.width - rw * scale) / 2;
  const oy = (canvas2d.height - rh * scale) / 2;

  ctx.fillStyle = '#080d1c';
  ctx.fillRect(0, 0, canvas2d.width, canvas2d.height);
  const floorStyle = state.room.floor_style || {};
  const wallStyle = state.room.wall_style || {};
  ctx.fillStyle = floorStyle.color || '#1a2240';
  ctx.strokeStyle = wallStyle.color || '#2a3a6a';
  ctx.lineWidth = 2;
  roundRect(ctx, ox, oy, rw * scale, rh * scale, 8);
  ctx.fill(); ctx.stroke();

  ctx.strokeStyle = '#1e2d55';
  ctx.lineWidth = 0.5;
  for (let x = 0; x <= rw; x++) {
    ctx.beginPath(); ctx.moveTo(ox + x * scale, oy); ctx.lineTo(ox + x * scale, oy + rh * scale); ctx.stroke();
  }
  for (let z = 0; z <= rh; z++) {
    ctx.beginPath(); ctx.moveTo(ox, oy + z * scale); ctx.lineTo(ox + rw * scale, oy + z * scale); ctx.stroke();
  }

  drawOpenings2D(ctx, state.room, ox, oy, scale, rw, rh);

  const warningIds = new Set((state.clearance_warnings || []).map(w => w.object_id));
  for (const obj of state.objects || []) {
    const fx = ox + obj.x * scale;
    const fz = oy + obj.z * scale;
    const fw = obj.w * scale;
    const fd = obj.d * scale;
    ctx.save();
    ctx.translate(fx + fw / 2, fz + fd / 2);
    ctx.rotate((obj.rotation || 0) * Math.PI / 180);
    ctx.fillStyle = obj.color;
    ctx.strokeStyle = warningIds.has(obj.id) ? '#ffaa00' : 'rgba(255,255,255,0.25)';
    ctx.lineWidth = warningIds.has(obj.id) ? 2.5 : 1;
    roundRect(ctx, -fw / 2, -fd / 2, fw, fd, 4);
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    ctx.font = `bold ${Math.max(9, Math.min(13, fw / 4))}px Inter`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(obj.type.replace(/_/g, ' '), 0, 0);
    ctx.restore();
  }

  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.font = '12px Inter, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(
    `${(state.room.theme || 'custom').replace(/_/g, ' ')} · ${state.room.wall_style?.label || ''} · ${state.room.floor_style?.label || ''}`,
    ox, oy - 16
  );
  ctx.fillStyle = '#4b5980';
  ctx.font = '11px JetBrains Mono, monospace';
  ctx.textAlign = 'center';
  ctx.fillText(`${rw}m`, ox + rw * scale / 2, oy + rh * scale + 20);
  ctx.save();
  ctx.translate(ox - 20, oy + rh * scale / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(`${rh}m`, 0, 0);
  ctx.restore();

  // Accessibility score badge in 2D
  const score = state.accessibility_score ?? 100;
  const scoreColor = score > 80 ? '#2dcc71' : score > 50 ? '#f5c842' : '#e74c3c';
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.beginPath(); ctx.roundRect(ox + rw * scale - 80, oy - 30, 80, 22, 6); ctx.fill();
  ctx.fillStyle = scoreColor;
  ctx.font = 'bold 11px Inter';
  ctx.textAlign = 'center';
  ctx.fillText(`Access: ${score}%`, ox + rw * scale - 40, oy - 14);
}

function drawOpenings2D(ctx, room, ox, oy, scale, rw, rh) {
  for (const win of (room.windows || [])) drawOpening2D(ctx, win, ox, oy, scale, rw, rh, '#87ceeb');
  for (const door of (room.doors || [])) drawOpening2D(ctx, door, ox, oy, scale, rw, rh, '#8b5a2b');
}

function drawOpening2D(ctx, def, ox, oy, scale, rw, rh, color) {
  const width = (def.width || 1.0) * scale;
  const wall = String(def.wall || 'north').toLowerCase();
  const pos = Math.min(0.95, Math.max(0.05, def.position || 0.5));
  ctx.fillStyle = color;
  if (wall === 'north') ctx.fillRect(ox + rw * scale * pos - width / 2, oy - 3, width, 6);
  else if (wall === 'south') ctx.fillRect(ox + rw * scale * pos - width / 2, oy + rh * scale - 3, width, 6);
  else if (wall === 'west') ctx.fillRect(ox - 3, oy + rh * scale * pos - width / 2, 6, width);
  else if (wall === 'east') ctx.fillRect(ox + rw * scale - 3, oy + rh * scale * pos - width / 2, 6, width);
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

// ─────────────────────── Helpers ────────────────────────────────────────────
function _capitalize(str) { return str.charAt(0).toUpperCase() + str.slice(1); }

function formatPrice(p) {
  const cur = (p?.currency || '').toUpperCase();
  const raw = p?.price ?? p?.price_usd ?? p?.price_low ?? p?.price_high;
  const val = (typeof raw === 'number') ? raw : Number(raw);
  if (!Number.isFinite(val) || val <= 0) return cur ? `— ${cur}` : '—';
  if (cur === 'EGP') return `${val.toLocaleString()} EGP`;
  if (cur) return `${val.toLocaleString()} ${cur}`;
  return `$${val.toLocaleString()}`;
}
function _formatHour(h) {
  const hh = Math.floor(h);
  const mm = Math.round((h - hh) * 60);
  const ampm = hh < 12 ? 'AM' : 'PM';
  const display = hh === 0 ? 12 : hh > 12 ? hh - 12 : hh;
  return `${display}:${mm.toString().padStart(2, '0')} ${ampm}`;
}

// ─────────────────────── Boot ────────────────────────────────────────────────
init().catch(console.error);
