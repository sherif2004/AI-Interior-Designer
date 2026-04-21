/**
 * ar_product_browser.js — Phase 4D
 * ===================================
 * IKEA Egypt product catalog browser inside the AR/3D viewer.
 * Displays products with EGP prices, multi-image galleries, color swatches.
 * "View in AR" launches the life-size AR session.
 *
 * Data source: GET /products/catalog  (from ikea_catalog.db, EGP prices)
 */

'use strict';

class ARProductBrowser {
    constructor(containerId = 'ar-product-browser') {
        this.container = document.getElementById(containerId);
        this.products  = [];
        this.filtered  = [];
        this.selected  = null;
        this._page     = 0;
        this._pageSize = 12;
        this._onSelectCallbacks = [];
        this._init();
    }

    /** Register callback for when user clicks "View in AR" */
    onSelect(fn) { this._onSelectCallbacks.push(fn); }

    async load(category = '', query = '') {
        try {
            const params = new URLSearchParams({ limit: 200 });
            if (category) params.set('category', category);
            if (query)    params.set('q', query);
            const res  = await fetch(`/products/catalog?${params}`);
            const data = await res.json();
            this.products = data.products || data || [];
            this.filtered = [...this.products];
            this._page = 0;
            this._render();
        } catch (err) {
            console.error('[ARProductBrowser] Load error:', err);
        }
    }

    filter(query = '', category = '') {
        const q = query.toLowerCase();
        this.filtered = this.products.filter(p => {
            const matchQ    = !q || p.name?.toLowerCase().includes(q) || p.series?.toLowerCase().includes(q);
            const matchCat  = !category || p.category === category || p.ikea_category === category;
            return matchQ && matchCat;
        });
        this._page = 0;
        this._render();
    }

    // ── Private ──────────────────────────────────────────────────────────────

    _init() {
        if (!this.container) return;
        this.container.innerHTML = `
        <div class="apb-inner">
          <div class="apb-header">
            <h3 class="apb-title">🛋️ IKEA Egypt Catalog</h3>
            <button class="apb-close" id="apb-close">✕</button>
          </div>
          <div class="apb-controls">
            <input type="text" class="apb-search" id="apb-search" placeholder="Search sofas, beds, desks…"/>
            <select class="apb-category" id="apb-category">
              <option value="">All Categories</option>
              <option value="sofa">Sofas</option>
              <option value="bed">Beds</option>
              <option value="chair">Chairs</option>
              <option value="desk">Desks</option>
              <option value="coffee_table">Coffee Tables</option>
              <option value="tv_stand">TV Benches</option>
              <option value="wardrobe">Wardrobes</option>
              <option value="nightstand">Nightstands</option>
            </select>
          </div>
          <div class="apb-grid" id="apb-grid"></div>
          <div class="apb-pagination" id="apb-pagination"></div>
        </div>`;
        this._injectStyles();
        this._bindControls();
        this.load();
    }

    _bindControls() {
        document.getElementById('apb-close')?.addEventListener('click', () => this.hide());

        const search = document.getElementById('apb-search');
        const cat    = document.getElementById('apb-category');

        let searchTimer;
        search?.addEventListener('input', () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => this.filter(search.value, cat?.value), 300);
        });
        cat?.addEventListener('change', () => this.filter(search?.value || '', cat.value));
    }

    _render() {
        const grid = document.getElementById('apb-grid');
        if (!grid) return;

        const start    = this._page * this._pageSize;
        const pageProds = this.filtered.slice(start, start + this._pageSize);

        if (pageProds.length === 0) {
            grid.innerHTML = '<div class="apb-empty">No products found. Try different search terms.</div>';
            return;
        }

        grid.innerHTML = pageProds.map(p => this._cardHTML(p)).join('');

        // Bind card buttons
        grid.querySelectorAll('.apb-card').forEach(card => {
            const id = card.dataset.id;
            const p  = this.products.find(x => x.id === id || x.item_no === id);
            if (!p) return;

            card.querySelector('.apb-btn-ar')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this._selectProduct(p);
            });

            card.querySelector('.apb-btn-info')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this._showDetail(p);
            });

            // Image gallery thumbnail cycling
            const imgs   = p.image_urls || [p.image_url];
            const mainImg = card.querySelector('.apb-img');
            let imgIdx = 0;
            card.querySelectorAll('.apb-thumb').forEach((thumb, i) => {
                thumb.addEventListener('click', (e) => {
                    e.stopPropagation();
                    imgIdx = i;
                    if (mainImg && imgs[i]) mainImg.src = imgs[i];
                    card.querySelectorAll('.apb-thumb').forEach(t => t.classList.remove('active'));
                    thumb.classList.add('active');
                });
            });
        });

        this._renderPagination();
    }

    _cardHTML(p) {
        const imgs    = (p.image_urls || [p.image_url]).filter(Boolean).slice(0, 4);
        const mainImg = imgs[0] || 'https://via.placeholder.com/300x300?text=No+Image';
        const price   = p.price ? `${p.price.toLocaleString('ar-EG')} ${p.currency || 'EGP'}` : 'N/A';
        const hasModel = p.model_url ? '🏠 AR Ready' : '';

        const thumbs = imgs.slice(1, 4).map((url, i) =>
            `<img class="apb-thumb" src="${url}" alt="view ${i+2}" loading="lazy"/>`
        ).join('');

        const dims = p.size ? `${(p.size[0]*100).toFixed(0)}×${(p.size[1]*100).toFixed(0)}cm` : '';

        return `
        <div class="apb-card" data-id="${p.id || p.item_no}">
          <div class="apb-img-wrap">
            <img class="apb-img" src="${mainImg}" alt="${p.name}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x200?text=IKEA'"/>
            ${hasModel ? `<span class="apb-ar-badge">${hasModel}</span>` : ''}
          </div>
          ${thumbs ? `<div class="apb-thumbs">${thumbs}</div>` : ''}
          <div class="apb-info">
            <div class="apb-series">${p.series || ''}</div>
            <div class="apb-name">${p.name || 'Unknown'}</div>
            <div class="apb-desc">${p.description || ''}</div>
            ${dims ? `<div class="apb-dims">📐 ${dims}</div>` : ''}
            <div class="apb-price">${price}</div>
            <div class="apb-btns">
              <button class="apb-btn apb-btn-ar" title="View in AR / Place in room">
                📦 Add to Room
              </button>
              <a class="apb-btn apb-btn-buy" href="${p.buy_url || '#'}" target="_blank" rel="noopener" title="View on IKEA Egypt">
                🛒
              </a>
            </div>
          </div>
        </div>`;
    }

    _renderPagination() {
        const pag    = document.getElementById('apb-pagination');
        if (!pag) return;
        const total  = Math.ceil(this.filtered.length / this._pageSize);
        if (total <= 1) { pag.innerHTML = ''; return; }

        pag.innerHTML = `
        <button class="apb-page-btn" ${this._page === 0 ? 'disabled' : ''} data-dir="-1">‹ Prev</button>
        <span class="apb-page-info">Page ${this._page + 1} / ${total} (${this.filtered.length} items)</span>
        <button class="apb-page-btn" ${this._page >= total - 1 ? 'disabled' : ''} data-dir="1">Next ›</button>`;

        pag.querySelectorAll('.apb-page-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._page = Math.max(0, Math.min(total - 1, this._page + parseInt(btn.dataset.dir)));
                this._render();
                document.getElementById('apb-grid')?.scrollIntoView({ behavior: 'smooth' });
            });
        });
    }

    _selectProduct(product) {
        this.selected = product;
        this._onSelectCallbacks.forEach(fn => fn(product));
        window.dispatchEvent(new CustomEvent('ar-browser:product-selected', { detail: product }));
    }

    _showDetail(product) {
        window.dispatchEvent(new CustomEvent('ar-browser:show-detail', { detail: product }));
    }

    show() { this.container?.classList.add('visible'); }
    hide() { this.container?.classList.remove('visible'); }
    toggle() { this.container?.classList.toggle('visible'); }

    _injectStyles() {
        if (document.getElementById('apb-styles')) return;
        const s = document.createElement('style');
        s.id = 'apb-styles';
        s.textContent = `
        #ar-product-browser {
            position:fixed; left:-380px; top:0; height:100vh; width:360px; z-index:1200;
            background:rgba(7,11,22,0.97); border-right:1px solid rgba(99,102,241,0.25);
            backdrop-filter:blur(24px); transition:left 0.35s cubic-bezier(0.34,1.56,0.64,1);
            font-family:'Inter',sans-serif; display:flex; flex-direction:column; overflow:hidden;
        }
        #ar-product-browser.visible { left:0; }
        .apb-inner { display:flex; flex-direction:column; height:100%; overflow:hidden; }
        .apb-header { display:flex; justify-content:space-between; align-items:center; padding:16px 20px 12px; border-bottom:1px solid rgba(255,255,255,0.06); flex-shrink:0; }
        .apb-title { margin:0; font-size:16px; font-weight:700; color:#e2e8f0; }
        .apb-close { background:none; border:none; color:#64748b; cursor:pointer; font-size:18px; padding:4px 8px; border-radius:8px; transition:all 0.2s; }
        .apb-close:hover { background:rgba(255,255,255,0.1); color:#e2e8f0; }
        .apb-controls { padding:12px 16px; display:flex; gap:8px; flex-shrink:0; }
        .apb-search { flex:1; padding:9px 12px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:10px; color:#e2e8f0; font-size:13px; outline:none; }
        .apb-search:focus { border-color:#6366f1; background:rgba(99,102,241,0.1); }
        .apb-category { padding:9px 8px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:10px; color:#e2e8f0; font-size:12px; outline:none; cursor:pointer; }
        .apb-grid { flex:1; overflow-y:auto; padding:12px 12px 0; display:flex; flex-direction:column; gap:10px; }
        .apb-grid::-webkit-scrollbar { width:4px; }
        .apb-grid::-webkit-scrollbar-thumb { background:rgba(99,102,241,0.4); border-radius:2px; }
        .apb-card { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); border-radius:12px; overflow:hidden; transition:all 0.25s; cursor:default; }
        .apb-card:hover { border-color:rgba(99,102,241,0.4); background:rgba(99,102,241,0.06); transform:translateY(-1px); box-shadow:0 8px 25px rgba(0,0,0,0.3); }
        .apb-img-wrap { position:relative; }
        .apb-img { width:100%; height:160px; object-fit:cover; display:block; transition:opacity 0.3s; }
        .apb-ar-badge { position:absolute; top:8px; right:8px; background:rgba(34,211,238,0.9); color:#0a0f1e; font-size:10px; font-weight:700; padding:3px 8px; border-radius:20px; }
        .apb-thumbs { display:flex; gap:4px; padding:6px; background:rgba(0,0,0,0.3); }
        .apb-thumb { width:44px; height:36px; object-fit:cover; border-radius:5px; cursor:pointer; opacity:.6; transition:all 0.2s; border:2px solid transparent; }
        .apb-thumb:hover, .apb-thumb.active { opacity:1; border-color:#6366f1; }
        .apb-info { padding:10px 12px; }
        .apb-series { font-size:10px; font-weight:700; color:#6366f1; text-transform:uppercase; letter-spacing:.8px; margin-bottom:2px; }
        .apb-name { font-size:13px; font-weight:600; color:#e2e8f0; margin-bottom:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .apb-desc { font-size:11px; color:#64748b; margin-bottom:4px; }
        .apb-dims { font-size:11px; color:#475569; margin-bottom:6px; }
        .apb-price { font-size:17px; font-weight:800; color:#22d3ee; margin-bottom:8px; direction:ltr; }
        .apb-btns { display:flex; gap:6px; }
        .apb-btn { padding:7px 12px; border:none; border-radius:8px; cursor:pointer; font-size:12px; font-weight:600; text-decoration:none; display:flex; align-items:center; gap:4px; transition:all 0.2s; }
        .apb-btn-ar { flex:1; background:linear-gradient(135deg,#6366f1,#4f46e5); color:#fff; justify-content:center; }
        .apb-btn-ar:hover { background:linear-gradient(135deg,#818cf8,#6366f1); transform:translateY(-1px); }
        .apb-btn-buy { background:rgba(255,255,255,0.08); color:#94a3b8; border:1px solid rgba(255,255,255,0.1); }
        .apb-btn-buy:hover { background:rgba(255,255,255,0.14); color:#e2e8f0; }
        .apb-empty { padding:40px 20px; text-align:center; color:#475569; font-size:14px; }
        .apb-pagination { padding:12px 16px; display:flex; align-items:center; gap:8px; border-top:1px solid rgba(255,255,255,0.06); flex-shrink:0; }
        .apb-page-btn { padding:7px 14px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:8px; color:#94a3b8; cursor:pointer; font-size:12px; transition:all 0.2s; }
        .apb-page-btn:hover:not(:disabled) { background:rgba(99,102,241,0.2); color:#e2e8f0; }
        .apb-page-btn:disabled { opacity:.35; cursor:default; }
        .apb-page-info { flex:1; text-align:center; font-size:11px; color:#475569; }
        `;
        document.head.appendChild(s);
    }
}

export { ARProductBrowser };
