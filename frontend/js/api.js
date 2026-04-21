/**
 * API client — thin fetch wrapper for the FastAPI backend.
 * Phase 2 & 3 additions: measurements, budget, versions, render, blueprint, products.
 */

const BASE = '';

async function _post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function _get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function _delete(path) {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ─────────────────────── Core ───────────────────────────────────────────────

export async function sendCommand(command) { return _post('/command', { command }); }
export async function getState() { return _get('/state'); }
export async function resetRoom(width = 10, height = 8) { return _post('/reset', { width, height }); }
export async function getCatalog() { return _get('/products?limit=50'); }
export async function getProjects() { return _get('/projects'); }
export async function checkLLMStatus() { return _get('/llm-status'); }

// ─────────────────────── Phase 2: Measurements ──────────────────────────────

export async function getMeasurements() { return _get('/measurements'); }

// ─────────────────────── Phase 2: Budget ────────────────────────────────────

export async function getBudget() { return _get('/budget'); }

// ─────────────────────── Phase 2: Versions ──────────────────────────────────

export async function saveVersion(name) { return _post('/versions/save', { name }); }
export async function getVersions() { return _get('/versions'); }
export async function getVersionDiff(a, b) { return _get(`/versions/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`); }
export async function getVersion(id) { return _get(`/versions/${id}`); }
export async function deleteVersion(id) { return _delete(`/versions/${id}`); }

// ─────────────────────── Phase 3: Render ────────────────────────────────────

export async function renderRoom() { return _post('/render', {}); }
export async function getRenderPrompt() { return _get('/render/prompt'); }

// ─────────────────────── Phase 3: Blueprint ─────────────────────────────────

export async function importBlueprint(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/import/blueprint`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─────────────────────── Phase 5.1: Photo Import / Style Detect ──────────────

async function _postFile(path, file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}${path}`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function importPhotoPreview(file) { return _postFile('/import/photo/preview', file); }
export async function importPhoto(file) { return _postFile('/import/photo', file); }
export async function detectStyleFromPhoto(file) { return _postFile('/style/detect', file); }
export async function detectStyleFromState() { return _post('/style/detect', {}); }

// ─────────────────────── Phase 5.3: Voice (v1 text) ─────────────────────────

export async function voiceCommand(text, session_id = 'default') {
  return _post('/voice/command', { text, session_id });
}

// ─────────────────────── Phase 5.3: Sketch (v1 image) ───────────────────────

export async function importSketch(imageDataUrl, apply = false) {
  return _post(`/import/sketch?apply=${apply ? '1' : '0'}`, { image: imageDataUrl });
}

// ─────────────────────── Phase 5.2: Commerce ────────────────────────────────

export async function multiRetailerSearch({ q = '', budget = 0, style = '', retailers = 'ikea', limit = 50 } = {}) {
  const params = new URLSearchParams();
  if (q) params.append('q', q);
  if (budget) params.append('budget', String(budget));
  if (style) params.append('style', style);
  if (retailers) params.append('retailers', retailers);
  if (limit) params.append('limit', String(limit));
  return _get(`/products/search?${params.toString()}`);
}

export async function getAvailability({ ids = '', retailer = 'ikea' } = {}) {
  const params = new URLSearchParams();
  if (ids) params.append('ids', ids);
  if (retailer) params.append('retailer', retailer);
  return _get(`/products/availability?${params.toString()}`);
}

export async function getBundles() { return _get('/products/bundle'); }
export async function getSustainability(productId) { return _get(`/products/sustainability/${encodeURIComponent(productId)}`); }

// ─────────────────────── Phase 5.5: Share / Comments / Export ────────────────

export async function createShare(role = 'view') { return _post('/share', { role }); }
export async function listComments() { return _get('/comments'); }
export async function addComment({ text, x = 0, y = 0, z = 0, object_id = '' }) {
  return _post('/comments', { text, x, y, z, object_id });
}

export async function exportMaterials() { return _get('/export/materials'); }
export async function exportDxf() {
  const res = await fetch(`${BASE}/export/dxf`, { method: 'POST' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.blob();
}

// ─────────────────────── Phase 5.6: Home (Multi-room) ───────────────────────

export async function homeAddRoom({ room_id = '', name = '' } = {}) {
  return _post('/home/rooms', { room_id, name });
}
export async function homeConnect({ a, b, type = 'door' }) {
  return _post('/home/connect', { a, b, type });
}
export async function homeBudget() { return _get('/home/budget'); }
export async function homeFlow() { return _get('/home/flow'); }

// ─────────────────────── Phase 3: Products ──────────────────────────────────

export async function getProducts(type, budget = null) {
  // Always return a consistent shape: { products: [...], count }
  const q = (type || '').toString().trim();
  const budgetVal = (budget == null ? null : Number(budget));

  // Fast path: full catalog, filtered client-side.
  try {
    const all = await _get('/products/all');
    const list = Array.isArray(all.products) ? all.products : [];
    if (list.length) {
      let filtered = list;
      if (q) {
        const qq = q.toLowerCase();
        filtered = filtered.filter(p =>
          (p.name && p.name.toLowerCase().includes(qq)) ||
          (p.category && p.category.toLowerCase().includes(qq)) ||
          (p.series && p.series.toLowerCase().includes(qq))
        );
      }
      if (budgetVal && budgetVal > 0) {
        filtered = filtered.filter(p => {
          const price = p.price_usd ?? p.price ?? p.price_low ?? p.price_high;
          return typeof price === 'number' ? price <= budgetVal : true;
        });
      }
      return { products: filtered.slice(0, 50), count: filtered.length };
    }
  } catch (e) {
    // ignore and fall back to server search
  }

  // Fallback: server-side search
  const params = new URLSearchParams();
  if (q) params.append('q', q);
  if (budgetVal && budgetVal > 0) params.append('budget', String(budgetVal));
  // Ask backend to return EGP if configured (Egypt region UX).
  // If backend doesn't have FX configured, it will fall back gracefully.
  params.append('currency', 'EGP');
  const data = await _get(`/products?${params.toString()}`);
  const products = data.products || data.results || [];
  return { products, count: data.count ?? products.length };
}

export async function getRoomProducts(state, budget = null) {
  const params = budget ? `?budget=${budget}` : '';
  return _post(`/products/room${params}`, state);
}

export async function placeProduct(productId, x = null, z = null) {
  return _post('/products/place', { productId, x, z });
}

export async function selectObject(objectId) {
  return _post('/select', { objectId });
}

// ─────────────────────── WebSocket ──────────────────────────────────────────

export function createWebSocket(onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  const ws = new WebSocket(wsUrl);

  ws.addEventListener('message', (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.warn('WS parse error:', e);
    }
  });

  return ws;
}
