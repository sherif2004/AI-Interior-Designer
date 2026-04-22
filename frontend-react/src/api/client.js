const BASE = '';

function _headers(extra = {}) {
  const h = { ...extra };
  const t = localStorage.getItem('aid_auth_token') || '';
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

async function _post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: _headers({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function _get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: _headers() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function _delete(path) {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE', headers: _headers() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Core ──
export const sendCommand    = (command) => _post('/command', { command });
export const getState       = ()        => _get('/state');
export const resetRoom      = (w=10,h=8)=> _post('/reset', { width:w, height:h });
export const checkLLMStatus = ()        => _get('/llm-status');

// ── Budget / Measurements ──
export const getBudget       = () => _get('/budget');
export const getMeasurements = () => _get('/measurements');

// ── Versions ──
export const saveVersion   = (name) => _post('/versions/save', { name });
export const getVersions   = ()     => _get('/versions');
export const deleteVersion = (id)   => _delete(`/versions/${id}`);

// ── Render ──
export const renderRoom = () => _post('/render', {});

// ── Products ──
export async function getProducts(query = '', limit = 50) {
  const params = new URLSearchParams();
  if (query) params.append('q', query);
  params.append('limit', String(limit));
  try {
    const all = await _get('/products/all');
    const list = Array.isArray(all.products) ? all.products : [];
    if (list.length) {
      const q = query.toLowerCase();
      const filtered = q
        ? list.filter(p =>
            (p.name||'').toLowerCase().includes(q) ||
            (p.category||'').toLowerCase().includes(q) ||
            (p.series||'').toLowerCase().includes(q))
        : list;
      return { products: filtered.slice(0, limit), count: filtered.length };
    }
  } catch {}
  const data = await _get(`/products?${params.toString()}`);
  const products = data.products || data.results || [];
  return { products, count: data.count ?? products.length };
}

// ── Projects ──
export const getProjects = () => _get('/projects');

// ── Select ──
export const selectObject = (objectId) => _post('/select', { objectId });

// ── Score ──
export const getScore = () => _get('/score');

// ── WebSocket ──
export function createWebSocket(onMessage) {
  // Always connect directly to the backend WS to avoid Vite proxy ECONNABORTED crashes
  const wsUrl = `ws://${window.location.hostname}:8000/ws`;
  const ws = new WebSocket(wsUrl);
  ws.addEventListener('message', (event) => {
    try { onMessage(JSON.parse(event.data)); } catch {}
  });
  return ws;
}

// ── Utility ──
export function proxiedImgUrl(url) {
  if (!url) return '';
  try { return `/img?u=${encodeURIComponent(url)}`; } catch { return url; }
}
