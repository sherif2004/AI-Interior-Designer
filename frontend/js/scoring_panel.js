/**
 * scoring_panel.js — Phase 4B
 * ============================
 * Animated layout score panel showing the 5-dimension breakdown.
 * Updates in real-time after every furniture action.
 */

'use strict';

const DIMENSION_META = {
    walkability:       { label: 'Walkability',       icon: '🚶', color: '#22d3ee' },
    functional_zoning: { label: 'Functional Zoning', icon: '🗺️', color: '#a78bfa' },
    visual_balance:    { label: 'Visual Balance',     icon: '⚖️', color: '#f59e0b' },
    object_relations:  { label: 'Object Relations',   icon: '🔗', color: '#34d399' },
    natural_light:     { label: 'Natural Light',      icon: '☀️', color: '#fbbf24' },
};

class ScoringPanel {
    constructor(containerId = 'scoring-panel') {
        this.container = document.getElementById(containerId);
        this.visible   = false;
        this._lastScore = null;
        this._init();
    }

    _init() {
        if (!this.container) return;

        this.container.innerHTML = `
        <div class="scoring-panel-inner">
          <div class="scoring-header">
            <span class="scoring-title">🏆 Layout Score</span>
            <button class="scoring-close" id="scoring-close-btn" title="Close">✕</button>
          </div>
          <div class="scoring-overall">
            <div class="scoring-gauge">
              <svg viewBox="0 0 120 70" class="gauge-svg">
                <path class="gauge-bg" d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="#1e293b" stroke-width="10" stroke-linecap="round"/>
                <path class="gauge-fill" id="gauge-fill" d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="#22d3ee"
                      stroke-width="10" stroke-linecap="round" stroke-dasharray="160" stroke-dashoffset="160"/>
              </svg>
              <div class="gauge-value" id="gauge-value">—</div>
              <div class="gauge-grade" id="gauge-grade">—</div>
            </div>
            <div class="scoring-summary" id="scoring-summary">Run a command to score your layout</div>
          </div>
          <div class="scoring-dimensions" id="scoring-dimensions"></div>
          <div class="scoring-actions">
            <button class="score-action-btn" id="btn-autofix">🔧 Auto-Fix Issues</button>
            <button class="score-action-btn secondary" id="btn-get-score">📊 Refresh Score</button>
          </div>
        </div>`;

        this._bindEvents();
        this._injectStyles();
    }

    _bindEvents() {
        document.getElementById('scoring-close-btn')?.addEventListener('click', () => this.hide());

        document.getElementById('btn-get-score')?.addEventListener('click', async () => {
            await this.refresh();
        });

        document.getElementById('btn-autofix')?.addEventListener('click', async () => {
            const btn = document.getElementById('btn-autofix');
            btn.textContent = '⏳ Auto-fixing...';
            btn.disabled = true;
            try {
                const res = await fetch('/autofix', { method: 'POST' });
                const data = await res.json();
                if (data.actions_applied) {
                    window.dispatchEvent(new CustomEvent('autofix:applied', { detail: data }));
                    await this.refresh();
                }
            } catch (e) { console.error(e); }
            finally {
                btn.textContent = '🔧 Auto-Fix Issues';
                btn.disabled = false;
            }
        });

        // Auto-refresh on room state changes
        window.addEventListener('room:updated', () => {
            if (this.visible) setTimeout(() => this.refresh(), 500);
        });
    }

    show() {
        if (this.container) {
            this.container.classList.add('visible');
            this.visible = true;
            if (!this._lastScore) this.refresh();
        }
    }

    hide() {
        if (this.container) {
            this.container.classList.remove('visible');
            this.visible = false;
        }
    }

    toggle() {
        this.visible ? this.hide() : this.show();
    }

    async refresh() {
        try {
            const res  = await fetch('/score');
            const data = await res.json();
            this.update(data);
        } catch (err) {
            console.error('[ScoringPanel] fetch error:', err);
        }
    }

    update(scoreData) {
        if (!scoreData || !this.container) return;
        this._lastScore = scoreData;

        const overall = scoreData.overall || 0;
        const grade   = scoreData.grade || '—';
        const summary = scoreData.summary || '';
        const dims    = scoreData.dimensions || {};

        // Animate gauge
        const fillEl = document.getElementById('gauge-fill');
        if (fillEl) {
            const arc    = 160;
            const offset = arc - (overall / 100) * arc;
            fillEl.style.strokeDashoffset = offset;
            // colour by grade
            const gradeColor = { A: '#22d3ee', B: '#34d399', C: '#f59e0b', D: '#fb923c', F: '#ef4444' };
            fillEl.style.stroke = gradeColor[grade] || '#22d3ee';
        }

        const valEl = document.getElementById('gauge-value');
        if (valEl) {
            this._animateNumber(valEl, parseInt(valEl.textContent) || 0, overall, 600);
        }

        const gradeEl = document.getElementById('gauge-grade');
        if (gradeEl) {
            gradeEl.textContent = `Grade ${grade}`;
            gradeEl.style.color = { A: '#22d3ee', B: '#34d399', C: '#f59e0b', D: '#fb923c', F: '#ef4444' }[grade] || '#94a3b8';
        }

        const summaryEl = document.getElementById('scoring-summary');
        if (summaryEl) summaryEl.textContent = summary;

        // Dimension bars
        const dimEl = document.getElementById('scoring-dimensions');
        if (dimEl) {
            dimEl.innerHTML = Object.entries(dims).map(([key, dim]) => {
                const meta  = DIMENSION_META[key] || { label: key, icon: '•', color: '#6366f1' };
                const score = dim.score || 0;
                const weight = Math.round((dim.weight || 0) * 100);
                const bestNote = (dim.notes || [])[0] || '';
                return `
                <div class="dim-row">
                  <div class="dim-label">
                    <span class="dim-icon">${meta.icon}</span>
                    <span class="dim-name">${meta.label}</span>
                    <span class="dim-weight">${weight}%</span>
                    <span class="dim-score">${score}</span>
                  </div>
                  <div class="dim-bar-bg">
                    <div class="dim-bar-fill" style="width:${score}%;background:${meta.color}"></div>
                  </div>
                  ${bestNote ? `<div class="dim-note">${bestNote}</div>` : ''}
                </div>`;
            }).join('');
        }
    }

    _animateNumber(el, from, to, duration) {
        const start = performance.now();
        const step  = (now) => {
            const p = Math.min((now - start) / duration, 1);
            el.textContent = Math.round(from + (to - from) * this._ease(p));
            if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    _ease(t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; }

    _injectStyles() {
        if (document.getElementById('scoring-panel-styles')) return;
        const style = document.createElement('style');
        style.id = 'scoring-panel-styles';
        style.textContent = `
        #scoring-panel {
            position: fixed; right: -340px; top: 70px; width: 320px; z-index: 1100;
            background: rgba(10,15,30,0.95); border: 1px solid rgba(99,102,241,0.3);
            border-radius: 16px; backdrop-filter: blur(20px);
            box-shadow: 0 25px 50px rgba(0,0,0,0.5);
            transition: right 0.35s cubic-bezier(0.34,1.56,0.64,1);
            font-family: 'Inter', sans-serif; color: #e2e8f0; overflow: hidden;
        }
        #scoring-panel.visible { right: 16px; }
        .scoring-panel-inner { padding: 20px; }
        .scoring-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
        .scoring-title { font-size:16px; font-weight:700; color:#e2e8f0; letter-spacing:.5px; }
        .scoring-close { background:none; border:none; color:#94a3b8; cursor:pointer; font-size:18px; padding:2px 6px; border-radius:6px; transition:background 0.2s; }
        .scoring-close:hover { background:rgba(255,255,255,0.1); color:#e2e8f0; }
        .scoring-overall { text-align:center; margin-bottom:20px; }
        .gauge-svg { width:180px; height:100px; }
        .gauge-fill { transition: stroke-dashoffset 0.8s ease, stroke 0.5s ease; }
        .gauge-value { font-size:36px; font-weight:800; color:#e2e8f0; margin-top:-10px; }
        .gauge-grade { font-size:13px; font-weight:600; margin-top:2px; }
        .scoring-summary { font-size:12px; color:#94a3b8; margin-top:10px; line-height:1.5; text-align:left; background:rgba(255,255,255,0.04); padding:8px 12px; border-radius:8px; }
        .scoring-dimensions { display:flex; flex-direction:column; gap:10px; margin-bottom:16px; }
        .dim-row { background:rgba(255,255,255,0.03); border-radius:10px; padding:10px 12px; }
        .dim-label { display:flex; align-items:center; gap:6px; margin-bottom:6px; font-size:13px; }
        .dim-icon { font-size:15px; }
        .dim-name { flex:1; font-weight:500; }
        .dim-weight { color:#64748b; font-size:11px; }
        .dim-score { font-weight:700; color:#e2e8f0; min-width:28px; text-align:right; }
        .dim-bar-bg { height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden; }
        .dim-bar-fill { height:100%; border-radius:3px; transition:width 0.8s ease; }
        .dim-note { font-size:11px; color:#94a3b8; margin-top:5px; line-height:1.4; }
        .scoring-actions { display:flex; flex-direction:column; gap:8px; }
        .score-action-btn { padding:10px 16px; border:none; border-radius:10px; cursor:pointer; font-size:13px; font-weight:600; transition:all 0.2s; }
        .score-action-btn:not(.secondary) { background:linear-gradient(135deg,#6366f1,#4f46e5); color:#fff; }
        .score-action-btn:not(.secondary):hover { background:linear-gradient(135deg,#818cf8,#6366f1); transform:translateY(-1px); }
        .score-action-btn.secondary { background:rgba(255,255,255,0.07); color:#94a3b8; }
        .score-action-btn.secondary:hover { background:rgba(255,255,255,0.12); color:#e2e8f0; }
        `;
        document.head.appendChild(style);
    }
}

export { ScoringPanel };
