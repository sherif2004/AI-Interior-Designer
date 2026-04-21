/**
 * sketch_input.js — Phase 5.3 (v1)
 * Lightweight sketch canvas modal → backend /import/sketch
 */

export function initSketchInput({
  openButton,
  statusEl,
  onApplied,
  api,
} = {}) {
  if (!openButton) return;

  let modal = null;
  let canvas = null;
  let ctx = null;
  let drawing = false;
  let last = null;

  function ensureModal() {
    if (modal) return;
    modal = document.createElement('div');
    modal.className = 'p5d-modal-overlay';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div class="p5d-modal">
        <div class="p5d-modal-header">
          <div class="p5d-modal-title">Sketch to Room</div>
          <button class="btn btn-outline" data-action="close">Close</button>
        </div>
        <div class="p5d-modal-body">
          <canvas class="p5d-sketch-canvas" width="900" height="520"></canvas>
          <div class="p5d-modal-actions">
            <button class="btn btn-outline" data-action="clear">Clear</button>
            <button class="btn btn-outline" data-action="preview">Preview</button>
            <button class="btn btn-primary" data-action="apply">Apply</button>
          </div>
          <div class="status-msg" data-el="summary"></div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    canvas = modal.querySelector('canvas');
    ctx = canvas.getContext('2d');
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    ctx.strokeStyle = 'rgba(248,250,252,0.95)';
    ctx.fillStyle = 'rgba(15,23,42,1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawGrid();

    modal.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-action]');
      if (!btn) return;
      const a = btn.dataset.action;
      if (a === 'close') close();
      if (a === 'clear') clear();
      if (a === 'preview') submit(false);
      if (a === 'apply') submit(true);
    });

    canvas.addEventListener('pointerdown', (e) => {
      drawing = true;
      last = pos(e);
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointermove', (e) => {
      if (!drawing) return;
      const p = pos(e);
      ctx.beginPath();
      ctx.moveTo(last.x, last.y);
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
      last = p;
    });
    canvas.addEventListener('pointerup', () => { drawing = false; last = null; });
    canvas.addEventListener('pointercancel', () => { drawing = false; last = null; });
  }

  function pos(e) {
    const r = canvas.getBoundingClientRect();
    return { x: (e.clientX - r.left) * (canvas.width / r.width), y: (e.clientY - r.top) * (canvas.height / r.height) };
  }

  function drawGrid() {
    const step = 40;
    ctx.save();
    ctx.strokeStyle = 'rgba(148,163,184,0.10)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= canvas.width; x += step) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += step) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }
    ctx.restore();
  }

  function clear() {
    ctx.fillStyle = 'rgba(15,23,42,1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawGrid();
    const sum = modal.querySelector('[data-el="summary"]');
    if (sum) sum.textContent = '';
  }

  function open() {
    ensureModal();
    modal.style.display = 'flex';
  }

  function close() {
    if (!modal) return;
    modal.style.display = 'none';
  }

  async function submit(apply) {
    try {
      const dataUrl = canvas.toDataURL('image/png');
      const sum = modal.querySelector('[data-el="summary"]');
      if (sum) sum.textContent = apply ? 'Applying…' : 'Previewing…';
      const res = await api.importSketch(dataUrl, apply);
      const summary = res.summary?.by_type ? JSON.stringify(res.summary.by_type) : '';
      const style = res.scan?.style ? `Style: ${res.scan.style}` : '';
      const conf = (res.scan?.confidence != null) ? `Confidence: ${Math.round(res.scan.confidence * 100)}%` : '';
      if (sum) sum.textContent = [style, conf, summary].filter(Boolean).join(' · ') || 'Done.';
      if (apply && res.state && typeof onApplied === 'function') onApplied(res.state);
      if (apply && statusEl) statusEl.textContent = `Applied ${res.actions_applied || 0} action(s) from sketch.`;
    } catch (e) {
      const sum = modal.querySelector('[data-el="summary"]');
      if (sum) sum.textContent = `Failed: ${e.message}`;
      if (statusEl) statusEl.textContent = `Sketch failed: ${e.message}`;
    }
  }

  openButton.addEventListener('click', open);
}

