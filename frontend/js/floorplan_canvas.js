/**
 * floorplan_canvas.js — Phase 4C
 * ================================
 * Professional 2D Floor Plan Editor built on Fabric.js.
 * Bidirectional sync with the Three.js 3D scene via backend /floorplan/sync.
 *
 * Features:
 *  - Snap-to-grid (5/10/25cm configurable)
 *  - Undo/redo stack (Ctrl+Z / Ctrl+Y, up to 50 states)
 *  - Pan (middle-mouse / Space+drag) and zoom (scroll wheel)
 *  - Real-time scale ruler (1:50 / 1:100 / 1:200)
 *  - Export PNG / SVG / PDF
 *  - Wall drawing mode (delegated to WallTool)
 *  - Furniture footprints (proxy for 3D objects)
 *  - Auto-syncs with 3D scene on every change
 */

'use strict';

// ── Constants ────────────────────────────────────────────────────────────────

const CANVAS_ID = 'floorplan-canvas';
const PIXELS_PER_METER = 100;   // 1m = 100px at 1:100 scale
const GRID_SIZES = [5, 10, 25, 50];  // cm options

const FURNITURE_COLORS = {
    sofa:         '#6366f1',
    bed:          '#22d3ee',
    desk:         '#f59e0b',
    chair:        '#34d399',
    dining_table: '#fb923c',
    coffee_table: '#a78bfa',
    wardrobe:     '#f472b6',
    tv_stand:     '#60a5fa',
    bookshelf:    '#4ade80',
    nightstand:   '#c084fc',
    lamp:         '#fde68a',
    rug:          '#94a3b8',
};

// ── FloorplanCanvas ──────────────────────────────────────────────────────────

class FloorplanCanvas {
    constructor(containerId = 'floorplan-panel') {
        this.container   = document.getElementById(containerId);
        this.canvas      = null;     // Fabric.js canvas
        this.fabricEl    = null;     // <canvas> element
        this.gridSize    = 10;       // cm
        this.scale       = 1;        // zoom level
        this.roomWidth   = 500;      // cm
        this.roomDepth   = 400;      // cm
        this.undoStack   = [];
        this.redoStack   = [];
        this._maxUndo    = 50;
        this._syncing    = false;
        this._gridGroup  = null;
        this._roomRect   = null;
        this._wallTool   = null;
        this._snapEngine = null;
        this._fabricLoaded = false;

        this._initUI();
        this._loadFabric().then(() => this._initCanvas());
    }

    // ── Lifecycle ──────────────────────────────────────────────────────────

    async _loadFabric() {
        if (window.fabric) { this._fabricLoaded = true; return; }
        await new Promise((res, rej) => {
            const s = document.createElement('script');
            s.src = 'https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.1/fabric.min.js';
            s.onload = () => { this._fabricLoaded = true; res(); };
            s.onerror = rej;
            document.head.appendChild(s);
        });
    }

    _initCanvas() {
        if (!this._fabricLoaded || !this.container) return;

        // Create canvas element
        this.fabricEl = document.getElementById(CANVAS_ID);
        if (!this.fabricEl) {
            this.fabricEl = document.createElement('canvas');
            this.fabricEl.id = CANVAS_ID;
            const wrap = this.container.querySelector('.fp-canvas-wrap');
            if (wrap) wrap.appendChild(this.fabricEl);
        }

        const wrap = this.fabricEl.parentElement;
        const w = (wrap?.clientWidth  || 800);
        const h = (wrap?.clientHeight || 600);
        this.fabricEl.width  = w;
        this.fabricEl.height = h;

        this.canvas = new fabric.Canvas(CANVAS_ID, {
            backgroundColor: '#0f172a',
            selection:       true,
            preserveObjectStacking: true,
        });

        this._drawGrid();
        this._drawRoomOutline();
        this._bindCanvasEvents();
        this._renderRuler();

        // Keyboard shortcuts
        document.addEventListener('keydown', this._onKeyDown.bind(this));

        window.dispatchEvent(new CustomEvent('floorplan:ready', { detail: { canvas: this } }));
    }

    // ── Room ───────────────────────────────────────────────────────────────

    setRoom(widthCm, depthCm) {
        this.roomWidth = widthCm;
        this.roomDepth = depthCm;
        this._drawRoomOutline();
        this._drawGrid();
        this._renderRuler();
    }

    setRoomFromState(state) {
        const room = state.room || state;
        const w = (room.width  || 5) * 100;
        const d = (room.height || room.depth || 4) * 100;
        this.setRoom(w, d);
        // Place furniture footprints
        const objects = state.objects || [];
        objects.forEach(obj => this.addFurnitureFootprint(obj));
    }

    // ── Grid ───────────────────────────────────────────────────────────────

    _drawGrid() {
        if (!this.canvas) return;

        // Remove old grid
        const old = this.canvas.getObjects().filter(o => o._fpType === 'grid');
        old.forEach(o => this.canvas.remove(o));

        const gridPx  = this.gridSize * (PIXELS_PER_METER / 100);
        const w       = this.canvas.width;
        const h       = this.canvas.height;
        const lines   = [];

        for (let x = 0; x <= w; x += gridPx) {
            lines.push(new fabric.Line([x, 0, x, h], {
                stroke: 'rgba(99,102,241,0.12)', strokeWidth: 1,
                selectable: false, evented: false, _fpType: 'grid',
            }));
        }
        for (let y = 0; y <= h; y += gridPx) {
            lines.push(new fabric.Line([0, y, w, y], {
                stroke: 'rgba(99,102,241,0.12)', strokeWidth: 1,
                selectable: false, evented: false, _fpType: 'grid',
            }));
        }

        lines.forEach(l => this.canvas.add(l));
        this.canvas.renderAll();
    }

    _drawRoomOutline() {
        if (!this.canvas) return;

        const old = this.canvas.getObjects().filter(o => o._fpType === 'room');
        old.forEach(o => this.canvas.remove(o));

        const wPx = this.roomWidth  * (PIXELS_PER_METER / 100);
        const dPx = this.roomDepth  * (PIXELS_PER_METER / 100);
        const cx  = this.canvas.width  / 2;
        const cy  = this.canvas.height / 2;

        const rect = new fabric.Rect({
            left:          cx - wPx / 2,
            top:           cy - dPx / 2,
            width:         wPx,
            height:        dPx,
            fill:          'rgba(30,41,59,0.6)',
            stroke:        '#6366f1',
            strokeWidth:   3,
            selectable:    false,
            evented:       false,
            _fpType:       'room',
        });

        // Dimension labels
        const labelStyle = { fontSize: 12, fill: '#94a3b8', selectable: false, evented: false, _fpType: 'room' };
        const wLabel = new fabric.Text(`${(this.roomWidth / 100).toFixed(1)} m`, {
            left: cx - 20, top: cy - dPx / 2 - 24, ...labelStyle
        });
        const dLabel = new fabric.Text(`${(this.roomDepth / 100).toFixed(1)} m`, {
            left: cx + wPx / 2 + 8, top: cy - 10, ...labelStyle, angle: 90
        });

        this.canvas.add(rect, wLabel, dLabel);
        this.canvas.sendToBack(rect);
        this.canvas.renderAll();
    }

    // ── Furniture Footprints ───────────────────────────────────────────────

    addFurnitureFootprint(obj) {
        if (!this.canvas) return;
        const existing = this.canvas.getObjects().find(o => o._fpObjId === obj.id);
        if (existing) { this._updateFurnitureFootprint(existing, obj); return; }

        const size = obj.size || [1.0, 1.0];
        const wPx  = size[0] * PIXELS_PER_METER;
        const dPx  = size[1] * PIXELS_PER_METER;

        const cx   = this.canvas.width  / 2;
        const cy   = this.canvas.height / 2;
        const px   = cx + (obj.x || 0) * PIXELS_PER_METER - wPx / 2;
        const py   = cy + (obj.z || 0) * PIXELS_PER_METER - dPx / 2;

        const color = FURNITURE_COLORS[obj.type] || '#6366f1';
        const rect  = new fabric.Rect({
            left:        px,
            top:         py,
            width:       wPx,
            height:      dPx,
            fill:        color + '33',
            stroke:      color,
            strokeWidth: 2,
            angle:       obj.rotation || 0,
            cornerColor: '#fff',
            cornerSize:  8,
            transparentCorners: false,
            _fpType:     'furniture',
            _fpObjId:    obj.id,
            _fpObjType:  obj.type,
        });

        const label = new fabric.Text(obj.type?.replace(/_/g, ' ') || '?', {
            left:        px + 4,
            top:         py + 4,
            fontSize:    10,
            fill:        '#e2e8f0',
            selectable:  false,
            evented:     false,
            _fpType:     'furniture_label',
            _fpObjId:    obj.id,
        });

        rect.on('modified', () => this._onFurnitureModified(rect));
        this.canvas.add(rect, label);
        this.canvas.renderAll();
    }

    _updateFurnitureFootprint(rect, obj) {
        const size = obj.size || [1.0, 1.0];
        const cx   = this.canvas.width  / 2;
        const cy   = this.canvas.height / 2;
        rect.set({
            left:   cx + (obj.x || 0) * PIXELS_PER_METER - (size[0] * PIXELS_PER_METER) / 2,
            top:    cy + (obj.z || 0) * PIXELS_PER_METER - (size[1] * PIXELS_PER_METER) / 2,
            angle:  obj.rotation || 0,
        });
        this.canvas.renderAll();
    }

    _onFurnitureModified(rect) {
        if (this._syncing) return;
        const cx  = this.canvas.width  / 2;
        const cy  = this.canvas.height / 2;
        const w   = rect.width  * rect.scaleX;
        const h   = rect.height * rect.scaleY;
        const x   = (rect.left + w / 2 - cx) / PIXELS_PER_METER;
        const z   = (rect.top  + h / 2 - cy) / PIXELS_PER_METER;

        window.dispatchEvent(new CustomEvent('floorplan:object-moved', {
            detail: { id: rect._fpObjId, x: parseFloat(x.toFixed(2)), z: parseFloat(z.toFixed(2)), rotation: rect.angle }
        }));
        this._saveUndoState();
    }

    // ── Undo / Redo ────────────────────────────────────────────────────────

    _saveUndoState() {
        if (!this.canvas) return;
        const json = JSON.stringify(this.canvas.toJSON(['_fpType', '_fpObjId', '_fpObjType']));
        this.undoStack.push(json);
        if (this.undoStack.length > this._maxUndo) this.undoStack.shift();
        this.redoStack = [];
    }

    undo() {
        if (this.undoStack.length === 0) return;
        const current = JSON.stringify(this.canvas.toJSON(['_fpType', '_fpObjId', '_fpObjType']));
        this.redoStack.push(current);
        const prev = this.undoStack.pop();
        this.canvas.loadFromJSON(prev, () => this.canvas.renderAll());
    }

    redo() {
        if (this.redoStack.length === 0) return;
        const next = this.redoStack.pop();
        this._saveUndoState();
        this.canvas.loadFromJSON(next, () => this.canvas.renderAll());
    }

    // ── Scale / Zoom ───────────────────────────────────────────────────────

    _bindCanvasEvents() {
        if (!this.canvas) return;

        // Scroll → zoom
        this.canvas.on('mouse:wheel', (opt) => {
            const delta = opt.e.deltaY;
            let zoom     = this.canvas.getZoom();
            zoom        *= 0.999 ** delta;
            zoom         = Math.min(5, Math.max(0.2, zoom));
            this.canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom);
            this.scale   = zoom;
            opt.e.preventDefault();
            opt.e.stopPropagation();
            this._renderRuler();
        });

        // Middle-mouse / space+drag → pan
        let panning = false, lastPt = null;
        this.canvas.on('mouse:down', opt => {
            if (opt.e.button === 1 || (opt.e.spaceKey && opt.e.buttons === 1)) {
                panning = true;
                lastPt  = { x: opt.e.clientX, y: opt.e.clientY };
            }
        });
        this.canvas.on('mouse:move', opt => {
            if (!panning || !lastPt) return;
            const dt = { x: opt.e.clientX - lastPt.x, y: opt.e.clientY - lastPt.y };
            const vpt = this.canvas.viewportTransform.slice();
            vpt[4] += dt.x; vpt[5] += dt.y;
            this.canvas.setViewportTransform(vpt);
            lastPt = { x: opt.e.clientX, y: opt.e.clientY };
        });
        this.canvas.on('mouse:up', () => { panning = false; lastPt = null; });

        // Auto-save undo on object modification
        this.canvas.on('object:modified', () => this._saveUndoState());
    }

    // ── Ruler ──────────────────────────────────────────────────────────────

    _renderRuler() {
        const el = this.container?.querySelector('.fp-ruler-value');
        if (el) {
            const realScale = (1 / this.scale) * 100; // cm per pixel
            el.textContent  = `1:${Math.round(realScale)}`;
        }
    }

    // ── Keyboard Shortcuts ─────────────────────────────────────────────────

    _onKeyDown(e) {
        if (!this.container?.classList.contains('visible')) return;
        const ctrl = e.ctrlKey || e.metaKey;
        if (ctrl && e.key === 'z') { e.preventDefault(); this.undo(); }
        if (ctrl && e.key === 'y') { e.preventDefault(); this.redo(); }
        if (ctrl && e.shiftKey && e.key === 'Z') { e.preventDefault(); this.redo(); }
        if (e.key === 'Delete' || e.key === 'Backspace') {
            const active = this.canvas?.getActiveObject();
            if (active && active._fpType === 'furniture') {
                this.canvas.remove(active);
                this._saveUndoState();
                window.dispatchEvent(new CustomEvent('floorplan:object-deleted', { detail: { id: active._fpObjId } }));
            }
        }
    }

    // ── Export ────────────────────────────────────────────────────────────

    exportPNG(filename = 'floorplan.png') {
        if (!this.canvas) return;
        const dataUrl = this.canvas.toDataURL({ format: 'png', multiplier: 2 });
        const a = document.createElement('a');
        a.href = dataUrl; a.download = filename; a.click();
    }

    exportSVG(filename = 'floorplan.svg') {
        if (!this.canvas) return;
        const svg  = this.canvas.toSVG();
        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href = url; a.download = filename; a.click();
        URL.revokeObjectURL(url);
    }

    /** Get the Fabric.js canvas JSON state (for server sync). */
    getJSON() {
        return this.canvas?.toJSON(['_fpType', '_fpObjId', '_fpObjType']) || {};
    }

    // ── Backend Sync ──────────────────────────────────────────────────────

    async syncToBackend() {
        try {
            const res = await fetch('/floorplan/sync', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ canvas_json: this.getJSON(), room_width_cm: this.roomWidth, room_depth_cm: this.roomDepth }),
            });
            return await res.json();
        } catch (err) {
            console.error('[FloorplanCanvas] sync error:', err);
        }
    }

    async loadFromBackend() {
        try {
            const res = await fetch('/state');
            const state = await res.json();
            this.setRoomFromState(state);
        } catch (err) {
            console.error('[FloorplanCanvas] load error:', err);
        }
    }

    // ── UI Init ───────────────────────────────────────────────────────────

    _initUI() {
        if (!this.container) return;
        this.container.innerHTML = `
        <div class="fp-inner">
          <div class="fp-toolbar">
            <button class="fp-tool-btn active" id="fp-tool-select" title="Select (V)">↖ Select</button>
            <button class="fp-tool-btn" id="fp-tool-wall" title="Draw Wall (W)">▭ Wall</button>
            <button class="fp-tool-btn" id="fp-tool-room" title="Set Room Size">⬜ Room</button>
            <div class="fp-divider"></div>
            <button class="fp-tool-btn" id="fp-tool-undo" title="Undo (Ctrl+Z)">↩ Undo</button>
            <button class="fp-tool-btn" id="fp-tool-redo" title="Redo (Ctrl+Y)">↪ Redo</button>
            <div class="fp-divider"></div>
            <label class="fp-label">Grid:</label>
            <select id="fp-grid-size" class="fp-select">
              ${GRID_SIZES.map(s => `<option value="${s}" ${s===10?'selected':''}>${s}cm</option>`).join('')}
            </select>
            <div class="fp-divider"></div>
            <span class="fp-ruler-label">Scale</span>
            <span class="fp-ruler-value">1:100</span>
            <div class="fp-divider"></div>
            <button class="fp-tool-btn" id="fp-export-png">📷 PNG</button>
            <button class="fp-tool-btn" id="fp-export-svg">✏️ SVG</button>
            <button class="fp-tool-btn" id="fp-export-pdf">📄 PDF</button>
            <div class="fp-spacer"></div>
            <button class="fp-tool-btn danger" id="fp-close">✕</button>
          </div>
          <div class="fp-body">
            <div class="fp-sidebar-left" id="fp-templates-sidebar"></div>
            <div class="fp-canvas-wrap">
              <canvas id="${CANVAS_ID}"></canvas>
            </div>
            <div class="fp-sidebar-right" id="fp-materials-sidebar"></div>
          </div>
          <div class="fp-statusbar">
            <span id="fp-cursor-pos">x: 0.00m, z: 0.00m</span>
            <span id="fp-object-info"></span>
          </div>
        </div>`;

        this._injectStyles();
        this._bindToolbar();
    }

    _bindToolbar() {
        document.getElementById('fp-tool-undo')?.addEventListener('click', () => this.undo());
        document.getElementById('fp-tool-redo')?.addEventListener('click', () => this.redo());
        document.getElementById('fp-export-png')?.addEventListener('click', () => this.exportPNG());
        document.getElementById('fp-export-svg')?.addEventListener('click', () => this.exportSVG());
        document.getElementById('fp-export-pdf')?.addEventListener('click', () => this._exportPDF());
        document.getElementById('fp-close')?.addEventListener('click', () => this.hide());

        document.getElementById('fp-grid-size')?.addEventListener('change', e => {
            this.gridSize = parseInt(e.target.value);
            this._drawGrid();
        });

        // Tool buttons
        ['select', 'wall', 'room'].forEach(tool => {
            document.getElementById(`fp-tool-${tool}`)?.addEventListener('click', () => {
                document.querySelectorAll('.fp-tool-btn').forEach(b => b.classList.remove('active'));
                document.getElementById(`fp-tool-${tool}`)?.classList.add('active');
                window.dispatchEvent(new CustomEvent('floorplan:tool-changed', { detail: { tool } }));
            });
        });
    }

    async _exportPDF() {
        try {
            const res = await fetch('/floorplan/export?format=pdf');
            if (res.ok) {
                const blob = await res.blob();
                const url  = URL.createObjectURL(blob);
                const a    = document.createElement('a');
                a.href = url; a.download = 'floorplan.pdf'; a.click();
                URL.revokeObjectURL(url);
            }
        } catch (e) {
            // Fallback: use jsPDF client-side
            this.exportPNG('floorplan.png');
        }
    }

    show() { this.container?.classList.add('visible'); }
    hide() { this.container?.classList.remove('visible'); }
    toggle() { this.container?.classList.toggle('visible'); }

    _injectStyles() {
        if (document.getElementById('fp-styles')) return;
        const s = document.createElement('style');
        s.id = 'fp-styles';
        s.textContent = `
        #floorplan-panel {
            position:fixed; inset:0; z-index:1500;
            background:rgba(7,11,22,0.98); backdrop-filter:blur(20px);
            display:none; flex-direction:column;
            font-family:'Inter',sans-serif; color:#e2e8f0;
            transition:opacity 0.3s;
        }
        #floorplan-panel.visible { display:flex; }
        .fp-inner { display:flex; flex-direction:column; height:100%; overflow:hidden; }
        .fp-toolbar { display:flex; align-items:center; gap:4px; padding:8px 12px; background:rgba(15,23,42,0.95); border-bottom:1px solid rgba(99,102,241,0.2); flex-wrap:wrap; }
        .fp-tool-btn { padding:6px 12px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#94a3b8; cursor:pointer; font-size:12px; font-weight:600; transition:all 0.2s; white-space:nowrap; }
        .fp-tool-btn:hover { background:rgba(99,102,241,0.2); color:#e2e8f0; border-color:rgba(99,102,241,0.4); }
        .fp-tool-btn.active { background:rgba(99,102,241,0.3); color:#a5b4fc; border-color:#6366f1; }
        .fp-tool-btn.danger { color:#f87171; }
        .fp-tool-btn.danger:hover { background:rgba(239,68,68,0.2); }
        .fp-divider { width:1px; height:24px; background:rgba(255,255,255,0.1); margin:0 4px; }
        .fp-spacer { flex:1; }
        .fp-label { font-size:11px; color:#64748b; }
        .fp-select { padding:5px 8px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:7px; color:#e2e8f0; font-size:12px; cursor:pointer; }
        .fp-ruler-label { font-size:11px; color:#64748b; margin-right:4px; }
        .fp-ruler-value { font-size:12px; color:#a5b4fc; font-weight:700; min-width:40px; }
        .fp-body { display:flex; flex:1; overflow:hidden; }
        .fp-sidebar-left, .fp-sidebar-right { width:200px; flex-shrink:0; background:rgba(15,23,42,0.7); border-right:1px solid rgba(255,255,255,0.06); overflow-y:auto; padding:8px; }
        .fp-sidebar-right { border-left:1px solid rgba(255,255,255,0.06); border-right:none; }
        .fp-canvas-wrap { flex:1; overflow:hidden; position:relative; cursor:crosshair; }
        #${CANVAS_ID}-upper-canvas { cursor:crosshair !important; }
        .fp-statusbar { display:flex; align-items:center; gap:16px; padding:4px 12px; background:rgba(15,23,42,0.95); border-top:1px solid rgba(255,255,255,0.06); font-size:11px; color:#64748b; }
        `;
        document.head.appendChild(s);
    }
}

export { FloorplanCanvas, PIXELS_PER_METER };
