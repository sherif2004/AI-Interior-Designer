/**
 * wall_tool.js — Phase 4C
 * =========================
 * Click-to-draw wall segments on the Fabric.js canvas.
 * Each wall has:
 *  - Adjustable thickness (10/15/20/30cm)
 *  - Live dimension label (length in metres)
 *  - Endpoint drag handles for resizing
 *  - Snap-to-grid and snap-to-endpoint (magnetic)
 */

'use strict';

import { PIXELS_PER_METER } from './floorplan_canvas.js';
import { SnapEngine } from './snap_engine.js';

const WALL_COLORS = {
    default:  { stroke: '#6366f1',  fill: 'rgba(99,102,241,0.25)' },
    selected: { stroke: '#22d3ee',  fill: 'rgba(34,211,238,0.3)' },
    hover:    { stroke: '#a78bfa',  fill: 'rgba(167,139,250,0.25)' },
};

class WallTool {
    constructor(canvas, snapEngine = null) {
        this.canvas     = canvas;   // Fabric.js canvas
        this.snap       = snapEngine || new SnapEngine(canvas);
        this.thickness  = 20;       // cm, wall thickness
        this.active     = false;
        this.drawing    = false;
        this.startPoint = null;
        this.liveWall   = null;     // Fabric object being drawn
        this.liveLabel  = null;
        this.walls      = [];       // [{fabric object, p1, p2, thicknessCm, id}]
        this._wallCount = 0;
        this._bound     = {};
    }

    /** Activate wall drawing mode. */
    activate() {
        if (this.active) return;
        this.active = true;
        this.canvas.selection = false;
        this.canvas.defaultCursor = 'crosshair';

        this._bound.mousedown  = this._onMouseDown.bind(this);
        this._bound.mousemove  = this._onMouseMove.bind(this);
        this._bound.dblclick   = this._onDblClick.bind(this);
        this._bound.keydown    = this._onKeyDown.bind(this);

        this.canvas.on('mouse:down',  this._bound.mousedown);
        this.canvas.on('mouse:move',  this._bound.mousemove);
        this.canvas.on('mouse:dblclick', this._bound.dblclick);
        document.addEventListener('keydown', this._bound.keydown);
    }

    /** Deactivate and clean up. */
    deactivate() {
        if (!this.active) return;
        this.active  = false;
        this.drawing = false;
        this.canvas.selection = true;
        this.canvas.defaultCursor = 'default';

        this.canvas.off('mouse:down',     this._bound.mousedown);
        this.canvas.off('mouse:move',     this._bound.mousemove);
        this.canvas.off('mouse:dblclick', this._bound.dblclick);
        document.removeEventListener('keydown', this._bound.keydown);

        this._removeLiveWall();
    }

    setThickness(cm) {
        this.thickness = parseInt(cm) || 20;
    }

    // ── Event Handlers ────────────────────────────────────────────────────

    _onMouseDown(opt) {
        if (opt.e.button !== 0) return;
        const pt = this.snap.getSnappedPoint(opt);

        if (!this.drawing) {
            // Start a new wall segment
            this.drawing    = true;
            this.startPoint = { ...pt };
            this._createLiveWall(pt);
        } else {
            // Finish wall segment, start next from same point
            this._commitWall(pt);
            this.startPoint = { ...pt };
        }
    }

    _onMouseMove(opt) {
        if (!this.drawing || !this.liveWall) return;
        const pt = this.snap.getSnappedPoint(opt);
        this._updateLiveWall(this.startPoint, pt);
    }

    _onDblClick(opt) {
        if (!this.drawing) return;
        this._removeLiveWall();
        this.drawing    = false;
        this.startPoint = null;
        this.canvas.renderAll();
    }

    _onKeyDown(e) {
        if (e.key === 'Escape' && this.drawing) {
            this._removeLiveWall();
            this.drawing    = false;
            this.startPoint = null;
            this.canvas.renderAll();
        }
    }

    // ── Wall Drawing ─────────────────────────────────────────────────────

    _createLiveWall(pt) {
        const thickPx = (this.thickness / 100) * PIXELS_PER_METER;

        this.liveWall = new fabric.Rect({
            left:           pt.x,
            top:            pt.y - thickPx / 2,
            width:          0,
            height:         thickPx,
            fill:           WALL_COLORS.default.fill,
            stroke:         WALL_COLORS.default.stroke,
            strokeWidth:    2,
            selectable:     false,
            evented:        false,
            originX:       'left',
            _fpType:        'wall_live',
        });

        this.liveLabel = new fabric.Text('0.00m', {
            left:        pt.x,
            top:         pt.y - thickPx - 18,
            fontSize:    11,
            fill:        '#94a3b8',
            selectable:  false,
            evented:     false,
            _fpType:     'wall_label_live',
        });

        this.canvas.add(this.liveWall, this.liveLabel);
    }

    _updateLiveWall(p1, p2) {
        if (!this.liveWall) return;

        const dx       = p2.x - p1.x;
        const dy       = p2.y - p1.y;
        const length   = Math.sqrt(dx * dx + dy * dy);
        const angle    = Math.atan2(dy, dx) * (180 / Math.PI);
        const thickPx  = (this.thickness / 100) * PIXELS_PER_METER;

        this.liveWall.set({
            left:   p1.x,
            top:    p1.y - thickPx / 2,
            width:  length,
            angle:  angle,
        });

        const midX  = (p1.x + p2.x) / 2;
        const midY  = (p1.y + p2.y) / 2;
        const lenM  = length / PIXELS_PER_METER;

        if (this.liveLabel) {
            this.liveLabel.set({
                left: midX - 20,
                top:  midY - thickPx - 20,
                text: `${lenM.toFixed(2)}m`,
            });
        }

        this.canvas.renderAll();
    }

    _commitWall(endPoint) {
        const p1 = this.startPoint;
        const p2 = endPoint;

        // Don't commit a zero-length wall
        const dx  = p2.x - p1.x;
        const dy  = p2.y - p1.y;
        if (Math.sqrt(dx * dx + dy * dy) < 5) return;

        this._removeLiveWall();

        const wallId   = `wall_${++this._wallCount}`;
        const thickPx  = (this.thickness / 100) * PIXELS_PER_METER;
        const length   = Math.sqrt(dx * dx + dy * dy);
        const angle    = Math.atan2(dy, dx) * (180 / Math.PI);
        const lenM     = length / PIXELS_PER_METER;

        // Create permanent wall rect
        const wallRect = new fabric.Rect({
            left:           p1.x,
            top:            p1.y - thickPx / 2,
            width:          length,
            height:         thickPx,
            fill:           WALL_COLORS.default.fill,
            stroke:         WALL_COLORS.default.stroke,
            strokeWidth:    2,
            angle:          angle,
            originX:        'left',
            cornerColor:    '#fff',
            cornerSize:     8,
            transparentCorners: false,
            selectable:     true,
            _fpType:        'wall',
            _fpWallId:      wallId,
            _fpThicknessCm: this.thickness,
            _fpP1:          { ...p1 },
            _fpP2:          { ...p2 },
        });

        // Dimension label
        const midX  = (p1.x + p2.x) / 2;
        const midY  = (p1.y + p2.y) / 2;
        const label = new fabric.Text(`${lenM.toFixed(2)}m`, {
            left:       midX - 20,
            top:        midY - thickPx - 18,
            fontSize:   11,
            fill:       '#94a3b8',
            selectable: false,
            evented:    false,
            angle:      0,
            _fpType:    'wall_label',
            _fpWallId:  wallId,
        });

        // Handle wall selection
        wallRect.on('selected',   () => { wallRect.set(WALL_COLORS.selected); this.canvas.renderAll(); });
        wallRect.on('deselected', () => { wallRect.set(WALL_COLORS.default);  this.canvas.renderAll(); });
        wallRect.on('modified',   () => this._onWallModified(wallRect, label));

        this.canvas.add(wallRect, label);
        this.canvas.renderAll();

        const wallData = {
            id:          wallId,
            p1:          { x: p1.x, y: p1.y },
            p2:          { x: p2.x, y: p2.y },
            p1_m:        { x: (p1.x - 400) / PIXELS_PER_METER, z: (p1.y - 300) / PIXELS_PER_METER },
            p2_m:        { x: (p2.x - 400) / PIXELS_PER_METER, z: (p2.y - 300) / PIXELS_PER_METER },
            thickness_cm: this.thickness,
            length_m:    parseFloat(lenM.toFixed(3)),
        };

        this.walls.push(wallData);
        window.dispatchEvent(new CustomEvent('floorplan:wall-added', { detail: wallData }));
    }

    _onWallModified(rect, label) {
        // Update label position on wall resize/move
        const cx    = rect.left + (rect.width * rect.scaleX) / 2;
        const cy    = rect.top  + (rect.height * rect.scaleY) / 2;
        const lenM  = (rect.width * rect.scaleX) / PIXELS_PER_METER;
        label.set({ left: cx - 20, top: cy - 25, text: `${lenM.toFixed(2)}m` });
        this.canvas.renderAll();

        window.dispatchEvent(new CustomEvent('floorplan:wall-modified', {
            detail: { id: rect._fpWallId, length_m: lenM }
        }));
    }

    _removeLiveWall() {
        if (this.liveWall) {
            this.canvas.remove(this.liveWall);
            this.liveWall = null;
        }
        if (this.liveLabel) {
            this.canvas.remove(this.liveLabel);
            this.liveLabel = null;
        }
    }

    /** Get all committed walls as world-space data. */
    getWalls() { return this.walls; }

    /** Clear all walls from canvas. */
    clearWalls() {
        const wallObjs = this.canvas.getObjects().filter(o => o._fpType === 'wall' || o._fpType === 'wall_label');
        wallObjs.forEach(w => this.canvas.remove(w));
        this.walls = [];
        this.canvas.renderAll();
    }
}

export { WallTool };
