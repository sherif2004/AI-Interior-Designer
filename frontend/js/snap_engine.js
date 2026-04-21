/**
 * snap_engine.js — Phase 4C
 * ===========================
 * Smart snap engine for the 2D floor plan editor.
 * Supports:
 *  - Grid snap (configurable interval in cm)
 *  - Wall-endpoint snap (magnetic, 15px radius)
 *  - Wall-midpoint snap
 *  - Object-centre alignment snap (shows guiding crosshair)
 *  - Angle snap (0/45/90/135°) while holding Shift
 */

'use strict';

import { PIXELS_PER_METER } from './floorplan_canvas.js';

const SNAP_RADIUS  = 15;   // px — close enough to snap to a point
const ANGLE_STEP   = 45;   // degrees

class SnapEngine {
    constructor(canvas, gridSizeCm = 10) {
        this.canvas      = canvas;
        this.gridSizeCm  = gridSizeCm;
        this._guideLines = [];
    }

    setGridSize(cm) { this.gridSizeCm = cm; }

    /**
     * Given a Fabric mouse event, return the best-snapped canvas point {x, y}.
     * Priority: endpoint snap > midpoint snap > grid snap.
     */
    getSnappedPoint(opt) {
        const raw = this.canvas.getPointer(opt.e);
        const pt  = { x: raw.x, y: raw.y };

        this._clearGuides();

        // 1. Endpoint snap (walls + furniture corners)
        const ep = this._snapToEndpoint(pt);
        if (ep) { this._drawGuide(ep); return ep; }

        // 2. Object centre snap
        const cp = this._snapToObjectCentre(pt);
        if (cp) { this._drawGuide(cp); return cp; }

        // 3. Grid snap
        return this._snapToGrid(pt);
    }

    /**
     * Snap a movement delta so that the dragged object aligns with smart guides.
     */
    snapObjectPosition(obj) {
        const cx = obj.left + (obj.width * obj.scaleX) / 2;
        const cy = obj.top  + (obj.height * obj.scaleY) / 2;

        this._clearGuides();

        // Check alignment with other furniture centres
        const others = this.canvas.getObjects()
            .filter(o => o !== obj && o._fpType === 'furniture' && o.visible);

        for (const other of others) {
            const ox = other.left + (other.width  * other.scaleX) / 2;
            const oy = other.top  + (other.height * other.scaleY) / 2;

            if (Math.abs(cx - ox) < SNAP_RADIUS) {
                this._drawGuide({ x: ox, y: cy }, 'vertical');
                obj.set({ left: ox - (obj.width * obj.scaleX) / 2 });
            }
            if (Math.abs(cy - oy) < SNAP_RADIUS) {
                this._drawGuide({ x: cx, y: oy }, 'horizontal');
                obj.set({ top: oy - (obj.height * obj.scaleY) / 2 });
            }
        }
    }

    /**
     * Snap an angle to the nearest ANGLE_STEP (used when Shift is held).
     */
    static snapAngle(degrees) {
        return Math.round(degrees / ANGLE_STEP) * ANGLE_STEP;
    }

    // ── Private ──────────────────────────────────────────────────────────

    _snapToGrid(pt) {
        const gridPx = (this.gridSizeCm / 100) * PIXELS_PER_METER;
        return {
            x: Math.round(pt.x / gridPx) * gridPx,
            y: Math.round(pt.y / gridPx) * gridPx,
        };
    }

    _snapToEndpoint(pt) {
        const snap = this._nearestWithin(pt, this._getAllEndpoints());
        return snap;
    }

    _snapToObjectCentre(pt) {
        const centres = this.canvas.getObjects()
            .filter(o => o._fpType === 'furniture' || o._fpType === 'wall')
            .map(o => ({
                x: o.left + (o.width  * (o.scaleX || 1)) / 2,
                y: o.top  + (o.height * (o.scaleY || 1)) / 2,
            }));
        return this._nearestWithin(pt, centres);
    }

    _getAllEndpoints() {
        const pts = [];
        this.canvas.getObjects()
            .filter(o => o._fpType === 'wall' && o._fpP1)
            .forEach(w => {
                pts.push({ x: w._fpP1.x, y: w._fpP1.y });
                pts.push({ x: w._fpP2.x, y: w._fpP2.y });
                // Midpoint
                pts.push({
                    x: (w._fpP1.x + w._fpP2.x) / 2,
                    y: (w._fpP1.y + w._fpP2.y) / 2,
                });
            });
        // Room corners
        const room = this.canvas.getObjects().find(o => o._fpType === 'room');
        if (room) {
            const { left: l, top: t, width: w, height: h } = room;
            [
                { x: l,     y: t },
                { x: l + w, y: t },
                { x: l,     y: t + h },
                { x: l + w, y: t + h },
                { x: l + w / 2, y: t },
                { x: l + w / 2, y: t + h },
                { x: l, y: t + h / 2 },
                { x: l + w, y: t + h / 2 },
            ].forEach(p => pts.push(p));
        }
        return pts;
    }

    _nearestWithin(pt, candidates) {
        let best = null, bestDist = SNAP_RADIUS;
        for (const c of candidates) {
            const d = Math.sqrt((pt.x - c.x) ** 2 + (pt.y - c.y) ** 2);
            if (d < bestDist) { best = c; bestDist = d; }
        }
        return best;
    }

    // ── Guide Lines ───────────────────────────────────────────────────────

    _drawGuide(pt, direction = 'both') {
        const w = this.canvas.width;
        const h = this.canvas.height;
        const style = { stroke: '#22d3ee', strokeWidth: 1, strokeDashArray: [4, 4], selectable: false, evented: false, _fpType: 'guide' };

        if (direction === 'both' || direction === 'horizontal') {
            const hLine = new fabric.Line([0, pt.y, w, pt.y], style);
            this.canvas.add(hLine);
            this._guideLines.push(hLine);
        }
        if (direction === 'both' || direction === 'vertical') {
            const vLine = new fabric.Line([pt.x, 0, pt.x, h], style);
            this.canvas.add(vLine);
            this._guideLines.push(vLine);
        }

        // Snap indicator circle
        const circle = new fabric.Circle({
            left: pt.x - 5, top: pt.y - 5, radius: 5,
            fill: 'transparent', stroke: '#22d3ee', strokeWidth: 2,
            selectable: false, evented: false, _fpType: 'guide',
        });
        this.canvas.add(circle);
        this._guideLines.push(circle);
    }

    _clearGuides() {
        this._guideLines.forEach(g => this.canvas.remove(g));
        this._guideLines = [];
    }
}

export { SnapEngine };
