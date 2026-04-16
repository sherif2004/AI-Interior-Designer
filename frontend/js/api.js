/**
 * API client — thin fetch wrapper for the FastAPI backend.
 */

// Use relative paths so it works on localhost, 0.0.0.0, or any domain
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

export async function sendCommand(command) {
  return _post('/command', { command });
}

export async function getState() {
  return _get('/state');
}

export async function resetRoom(width = 10, height = 8) {
  return _post('/reset', { width, height });
}

export async function getCatalog() {
  return _get('/catalog');
}

export async function getProjects() {
  return _get('/projects');
}

export async function deleteObject(objectId) {
  return _post('/command', { command: `Delete ${objectId}` });
}

export async function checkLLMStatus() {
  return _get('/llm-status');
}

/**
 * Create a WebSocket connection.
 * @param {function} onMessage  Called with parsed JSON message
 * @returns {WebSocket}
 */
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
