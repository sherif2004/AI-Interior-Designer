/**
 * material_library.js — Phase 4C
 * ================================
 * Material and texture swatcher panel.
 * Lets users apply PBR materials to walls, floors, and furniture.
 * Dispatches events that the 3D scene listens to.
 */

'use strict';

const MATERIALS = {
    floors: [
        { id: 'oak_wood',         label: 'Oak Wood',          color: '#c4a882', pattern: 'wood',       preview: 'linear-gradient(45deg,#c4a882,#a0825c)' },
        { id: 'dark_wood',        label: 'Dark Walnut',       color: '#5c3d2e', pattern: 'wood',       preview: 'linear-gradient(45deg,#5c3d2e,#3d2416)' },
        { id: 'light_wood',       label: 'Light Birch',       color: '#e8d5b7', pattern: 'wood',       preview: 'linear-gradient(45deg,#e8d5b7,#d4b896)' },
        { id: 'herringbone_oak',  label: 'Herringbone Oak',   color: '#b8976a', pattern: 'herringbone',preview: 'repeating-linear-gradient(45deg,#b8976a 0,#b8976a 5px,#a07845 5px,#a07845 10px)' },
        { id: 'concrete',         label: 'Polished Concrete', color: '#9ca3af', pattern: 'concrete',   preview: 'linear-gradient(135deg,#9ca3af,#6b7280)' },
        { id: 'marble_white',     label: 'White Marble',      color: '#f5f5f0', pattern: 'marble',     preview: 'linear-gradient(135deg,#f5f5f0 0%,#e0ddd5 50%,#f0ece4 100%)' },
        { id: 'marble_dark',      label: 'Noir Marble',       color: '#2d2d2d', pattern: 'marble',     preview: 'linear-gradient(135deg,#2d2d2d 0%,#1a1a1a 50%,#3d3d3d 100%)' },
        { id: 'terracotta_tile',  label: 'Terracotta Tile',   color: '#c47a45', pattern: 'tile',       preview: 'repeating-linear-gradient(0deg,#c47a45 0,#c47a45 48px,#a86030 48px,#a86030 50px)' },
        { id: 'carpet_grey',      label: 'Grey Carpet',       color: '#94a3b8', pattern: 'carpet',     preview: 'repeating-linear-gradient(45deg,#94a3b8 0,#94a3b8 2px,#7b8fa8 2px,#7b8fa8 4px)' },
        { id: 'vinyl_white',      label: 'White Vinyl',       color: '#f8fafc', pattern: 'flat',       preview: '#f8fafc' },
    ],
    walls: [
        { id: 'plaster_white',    label: 'Warm White',        color: '#faf9f6', preview: '#faf9f6' },
        { id: 'plaster_warmgrey', label: 'Warm Grey',         color: '#e8e4dc', preview: '#e8e4dc' },
        { id: 'plaster_beige',    label: 'Beige',             color: '#f0e8d8', preview: '#f0e8d8' },
        { id: 'plaster_sage',     label: 'Sage Green',        color: '#b5c4b1', preview: '#b5c4b1' },
        { id: 'plaster_blue',     label: 'Dusty Blue',        color: '#b0c4d8', preview: '#b0c4d8' },
        { id: 'plaster_terracotta', label: 'Terracotta',      color: '#d4795a', preview: '#d4795a' },
        { id: 'plaster_charcoal', label: 'Charcoal',          color: '#374151', preview: '#374151' },
        { id: 'plaster_navy',     label: 'Navy',              color: '#1e3a5f', preview: '#1e3a5f' },
        { id: 'brick_exposed',    label: 'Exposed Brick',     color: '#a05c3c', preview: 'repeating-linear-gradient(0deg,#a05c3c 0,#a05c3c 14px,#8b4e30 14px,#8b4e30 16px)' },
        { id: 'wallpaper_stripe', label: 'Stripe Wallpaper',  color: '#e8e0f0', preview: 'repeating-linear-gradient(90deg,#e8e0f0 0,#e8e0f0 18px,#d0c8e8 18px,#d0c8e8 20px)' },
        { id: 'wood_panels',      label: 'Wood Panels',       color: '#8b6344', preview: 'repeating-linear-gradient(90deg,#8b6344 0,#8b6344 78px,#7a5235 78px,#7a5235 80px)' },
    ],
    furniture: [
        { id: 'fabric_grey',      label: 'Fabric Grey',       color: '#6b7280', preview: '#6b7280' },
        { id: 'fabric_beige',     label: 'Fabric Beige',      color: '#d4c5a9', preview: '#d4c5a9' },
        { id: 'fabric_navy',      label: 'Fabric Navy',       color: '#1e3a5f', preview: '#1e3a5f' },
        { id: 'fabric_olive',     label: 'Fabric Olive',      color: '#6b7028', preview: '#6b7028' },
        { id: 'leather_brown',    label: 'Brown Leather',     color: '#8b5e3c', preview: 'linear-gradient(135deg,#8b5e3c,#6b4228)' },
        { id: 'leather_black',    label: 'Black Leather',     color: '#1f2937', preview: 'linear-gradient(135deg,#374151,#111827)' },
        { id: 'wood_oak',         label: 'Oak',               color: '#c4a882', preview: 'linear-gradient(45deg,#c4a882,#a0825c)' },
        { id: 'wood_walnut',      label: 'Walnut',            color: '#5c3d2e', preview: 'linear-gradient(45deg,#5c3d2e,#3d2416)' },
        { id: 'white_gloss',      label: 'White Gloss',       color: '#f8fafc', preview: 'linear-gradient(135deg,#ffffff,#f0f4f8)' },
        { id: 'black_matte',      label: 'Black Matte',       color: '#111827', preview: '#111827' },
        { id: 'metal_brushed',    label: 'Brushed Metal',     color: '#9ca3af', preview: 'linear-gradient(90deg,#9ca3af,#6b7280,#9ca3af)' },
    ],
};

class MaterialLibrary {
    constructor(containerId = 'fp-materials-sidebar') {
        this.container = document.getElementById(containerId);
        this._init();
    }

    _init() {
        if (!this.container) return;

        this.container.innerHTML = `
        <div class="mat-lib">
          <div class="mat-title">🎨 Materials</div>
          <div class="mat-tabs">
            <button class="mat-tab active" data-cat="floors">Floors</button>
            <button class="mat-tab" data-cat="walls">Walls</button>
            <button class="mat-tab" data-cat="furniture">Furniture</button>
          </div>
          <div class="mat-grid" id="mat-grid"></div>
        </div>`;

        this._injectStyles();
        this._renderCategory('floors');

        this.container.querySelectorAll('.mat-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.container.querySelectorAll('.mat-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this._renderCategory(tab.dataset.cat);
            });
        });
    }

    _renderCategory(cat) {
        const grid  = document.getElementById('mat-grid');
        if (!grid) return;
        const items = MATERIALS[cat] || [];

        grid.innerHTML = items.map(m => `
        <div class="mat-swatch" data-id="${m.id}" data-cat="${cat}" data-color="${m.color}" title="${m.label}">
          <div class="mat-preview" style="background:${m.preview}"></div>
          <div class="mat-label">${m.label}</div>
        </div>`).join('');

        grid.querySelectorAll('.mat-swatch').forEach(sw => {
            sw.addEventListener('click', () => {
                const mat = { id: sw.dataset.id, category: sw.dataset.cat, color: sw.dataset.color };
                this._applyMaterial(mat);
                grid.querySelectorAll('.mat-swatch').forEach(s => s.classList.remove('selected'));
                sw.classList.add('selected');
            });
        });
    }

    _applyMaterial(mat) {
        window.dispatchEvent(new CustomEvent('material:applied', { detail: mat }));

        // Also send to backend for 3D scene update
        const action = mat.category === 'floors'
            ? { action: 'SET_FLOOR_STYLE', params: { material: mat.id, color: mat.color } }
            : mat.category === 'walls'
            ? { action: 'SET_WALL_STYLE',  params: { color: mat.color, material: mat.id } }
            : { action: 'SET_FURNITURE_MATERIAL', params: { material: mat.id, color: mat.color } };

        fetch('/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(action),
        }).catch(() => {});
    }

    _injectStyles() {
        if (document.getElementById('mat-lib-styles')) return;
        const s = document.createElement('style');
        s.id = 'mat-lib-styles';
        s.textContent = `
        .mat-lib { padding:4px; }
        .mat-title { font-size:12px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:.8px; margin-bottom:10px; }
        .mat-tabs { display:flex; gap:4px; margin-bottom:12px; }
        .mat-tab { flex:1; padding:5px 2px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); border-radius:7px; color:#64748b; font-size:10px; font-weight:600; cursor:pointer; transition:all 0.2s; }
        .mat-tab.active { background:rgba(99,102,241,0.25); color:#a5b4fc; border-color:#6366f1; }
        .mat-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
        .mat-swatch { cursor:pointer; border-radius:8px; border:2px solid transparent; overflow:hidden; background:rgba(255,255,255,0.04); transition:all 0.2s; }
        .mat-swatch:hover { border-color:rgba(99,102,241,0.5); transform:translateY(-1px); }
        .mat-swatch.selected { border-color:#6366f1; box-shadow:0 0 0 1px #6366f1; }
        .mat-preview { height:44px; width:100%; }
        .mat-label { font-size:9px; color:#94a3b8; padding:4px 6px; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        `;
        document.head.appendChild(s);
    }
}

export { MaterialLibrary, MATERIALS };
