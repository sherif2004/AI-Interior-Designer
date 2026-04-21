/**
 * room_templates.js — Phase 4C
 * ==============================
 * Room template browser: shows pre-designed layouts as cards.
 * Clicking "Use Template" loads the layout into the current room.
 */

'use strict';

class RoomTemplates {
    constructor(containerId = 'fp-templates-sidebar') {
        this.container = document.getElementById(containerId);
        this.templates = [];
        this._init();
    }

    async _init() {
        if (!this.container) return;

        this.container.innerHTML = `
        <div class="tpl-lib">
          <div class="tpl-title">📐 Templates</div>
          <div class="tpl-list" id="tpl-list">
            <div class="tpl-loading">Loading…</div>
          </div>
        </div>`;

        this._injectStyles();
        await this._loadTemplates();
    }

    async _loadTemplates() {
        try {
            const res  = await fetch('/templates');
            const data = await res.json();
            this.templates = data.templates || data || [];
            this._render();
        } catch {
            // Show built-in fallbacks
            this.templates = [
                { id: 'studio_apartment', name: 'Studio Apartment',       description: '30m² open plan',      room_size: '6×5m', object_count: 7 },
                { id: 'living_room',      name: 'Living Room',            description: 'Two-sofa with TV',    room_size: '5.5×4.5m', object_count: 6 },
                { id: 'bedroom',          name: 'Master Bedroom',         description: 'King bed + wardrobes',room_size: '5×4.5m', object_count: 6 },
                { id: 'home_office',      name: 'Home Office',            description: 'L-shape desk setup',  room_size: '4×3.5m', object_count: 5 },
                { id: 'open_plan',        name: 'Open-Plan Living+Dining',description: '45m² combined space', room_size: '7.5×6m', object_count: 10 },
            ];
            this._render();
        }
    }

    _render() {
        const list = document.getElementById('tpl-list');
        if (!list) return;

        list.innerHTML = this.templates.map(t => `
        <div class="tpl-card" data-id="${t.id}">
          <div class="tpl-card-header">
            <div class="tpl-name">${t.name}</div>
            <div class="tpl-size">${t.room_size || ''}</div>
          </div>
          <div class="tpl-desc">${t.description || ''}</div>
          <div class="tpl-meta">${t.object_count || 0} pieces</div>
          <button class="tpl-use-btn" data-id="${t.id}">Use Template →</button>
        </div>`).join('');

        list.querySelectorAll('.tpl-use-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await this._loadTemplate(btn.dataset.id);
            });
        });
    }

    async _loadTemplate(templateId) {
        try {
            // Visual feedback
            const btn = document.querySelector(`.tpl-use-btn[data-id="${templateId}"]`);
            if (btn) { btn.textContent = 'Loading…'; btn.disabled = true; }

            const res  = await fetch(`/templates/${templateId}`);
            const data = await res.json();

            // Apply template via reset + bulk commands
            if (data.room) {
                await fetch('/reset', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ width: data.room.width || 5, height: data.room.height || 4 }),
                });
            }

            // Apply style
            if (data.style?.theme) {
                await fetch('/command', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: `set style ${data.style.theme}` }),
                });
            }

            // Add all objects
            for (const obj of (data.objects || [])) {
                await fetch('/command', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'ADD',
                        params: { type: obj.type, x: obj.x, z: obj.z, rotation: obj.rotation || 0 }
                    }),
                });
            }

            window.dispatchEvent(new CustomEvent('template:loaded', { detail: { id: templateId, data } }));
            if (btn) { btn.textContent = '✅ Loaded!'; setTimeout(() => { btn.textContent = 'Use Template →'; btn.disabled = false; }, 2000); }

        } catch (err) {
            console.error('[RoomTemplates] Load error:', err);
            const btn = document.querySelector(`.tpl-use-btn[data-id="${templateId}"]`);
            if (btn) { btn.textContent = 'Use Template →'; btn.disabled = false; }
        }
    }

    _injectStyles() {
        if (document.getElementById('tpl-styles')) return;
        const s = document.createElement('style');
        s.id = 'tpl-styles';
        s.textContent = `
        .tpl-lib { padding:4px; }
        .tpl-title { font-size:12px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:.8px; margin-bottom:10px; }
        .tpl-loading { color:#475569; font-size:12px; padding:16px 0; text-align:center; }
        .tpl-list { display:flex; flex-direction:column; gap:8px; }
        .tpl-card { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); border-radius:10px; padding:10px; transition:all 0.2s; }
        .tpl-card:hover { border-color:rgba(99,102,241,0.4); background:rgba(99,102,241,0.06); }
        .tpl-card-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px; }
        .tpl-name { font-size:12px; font-weight:700; color:#e2e8f0; line-height:1.3; }
        .tpl-size { font-size:10px; color:#6366f1; font-weight:600; white-space:nowrap; }
        .tpl-desc { font-size:11px; color:#64748b; margin-bottom:5px; line-height:1.4; }
        .tpl-meta { font-size:10px; color:#475569; margin-bottom:8px; }
        .tpl-use-btn { width:100%; padding:6px 10px; background:linear-gradient(135deg,#6366f1,#4f46e5); border:none; border-radius:7px; color:#fff; font-size:11px; font-weight:600; cursor:pointer; transition:all 0.2s; }
        .tpl-use-btn:hover:not(:disabled) { background:linear-gradient(135deg,#818cf8,#6366f1); transform:translateY(-1px); }
        .tpl-use-btn:disabled { opacity:.5; cursor:default; }
        `;
        document.head.appendChild(s);
    }
}

export { RoomTemplates };
