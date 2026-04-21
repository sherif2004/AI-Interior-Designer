/**
 * ar_life_size.js — Phase 4D
 * ============================
 * Life-size IKEA product AR viewer (IKEA Place parity).
 * 
 * Priority chain:
 *   1. WebXR hit-test (native AR on Android/iOS)    → 1:1 scale GLB placement
 *   2. Camera background mode (desktop/unsupported) → Three.js procedural geometry
 *   3. Standard 3D mode (no camera)                 → normal scene placement
 *
 * GLB loading: uses THREE.GLTFLoader for model_url from IKEA Egypt DB.
 * Fallback:    generates a box geometry with correct 1:1 dimensions.
 */

'use strict';

class ARLifeSize {
    constructor(scene, camera, renderer, roomState) {
        this.scene      = scene;
        this.camera     = camera;
        this.renderer   = renderer;
        this.roomState  = roomState;

        this.currentProduct = null;
        this.previewMesh    = null;
        this.xrSession      = null;
        this.hitTestSource  = null;
        this.reticle        = null;
        this._loader        = null;

        this._mode = 'standard';  // 'webxr' | 'camera' | 'standard'

        this._initReticle();
    }

    /**
     * Start an AR life-size session for an IKEA product.
     * @param {object} product — IKEAProduct dict from backend
     */
    async startForProduct(product) {
        this.currentProduct = product;
        window.dispatchEvent(new CustomEvent('ar-life-size:loading', { detail: { product } }));

        const mode = await this._detectMode();
        this._mode = mode;

        if (mode === 'webxr') {
            await this._startWebXR(product);
        } else {
            await this._startCameraMode(product);
        }
    }

    /** Stop the AR session and clean up. */
    async stop() {
        if (this.xrSession) {
            await this.xrSession.end().catch(() => {});
            this.xrSession = null;
        }
        this._removePreview();
        if (this.reticle) this.reticle.visible = false;
        window.dispatchEvent(new CustomEvent('ar-life-size:stopped'));
    }

    // ── WebXR Path ───────────────────────────────────────────────────────────

    async _startWebXR(product) {
        try {
            this.xrSession = await navigator.xr.requestSession('immersive-ar', {
                requiredFeatures: ['hit-test'],
                optionalFeatures: ['dom-overlay'],
                domOverlay:       { root: document.getElementById('ar-overlay') || document.body },
            });

            this.renderer.xr.setReferenceSpaceType('local');
            await this.renderer.xr.setSession(this.xrSession);

            const refSpace = await this.xrSession.requestReferenceSpace('viewer');
            this.hitTestSource = await this.xrSession.requestHitTestSource({ space: refSpace });

            this.renderer.setAnimationLoop((timestamp, frame) => {
                this._xrFrame(frame, product);
            });

            // Tap to place
            this.xrSession.addEventListener('select', () => {
                if (this.reticle?.visible) {
                    this._confirmPlacement(this.reticle.position.clone(), product);
                }
            });

            this.xrSession.addEventListener('end', () => {
                this.renderer.setAnimationLoop(null);
                this.hitTestSource = null;
                this.xrSession     = null;
            });

        } catch (err) {
            console.warn('[ARLifeSize] WebXR failed, falling back to camera mode:', err.message);
            await this._startCameraMode(product);
        }
    }

    _xrFrame(frame, product) {
        if (!frame || !this.hitTestSource) return;

        const hitResults = frame.getHitTestResults(this.hitTestSource);
        if (hitResults.length > 0) {
            const pose = hitResults[0].getPose(this.renderer.xr.getReferenceSpace());
            if (pose) {
                if (!this.previewMesh) this._createPreview(product);
                this.reticle.visible = true;
                this.reticle.position.setFromMatrixPosition(new THREE.Matrix4().fromArray(pose.transform.matrix));
                if (this.previewMesh) {
                    this.previewMesh.position.copy(this.reticle.position);
                }
            }
        } else {
            this.reticle.visible = false;
        }

        this.renderer.render(this.scene, this.camera);
    }

    // ── Camera / Desktop Path ────────────────────────────────────────────────

    async _startCameraMode(product) {
        this._createPreview(product);
        this._updateOverlay(product);
        window.dispatchEvent(new CustomEvent('ar-life-size:camera-mode', { detail: { product } }));
    }

    // ── Preview Mesh ─────────────────────────────────────────────────────────

    async _createPreview(product) {
        this._removePreview();

        // Try loading GLB if model_url is available
        if (product.model_url) {
            try {
                const mesh = await this._loadGLB(product.model_url);
                this.previewMesh = mesh;
                this.previewMesh.userData.isARPreview = true;
                this.scene.add(this.previewMesh);
                return;
            } catch (err) {
                console.warn('[ARLifeSize] GLB load failed, using procedural geometry:', err.message);
            }
        }

        // Fallback: procedural box geometry at 1:1 IKEA dimensions
        const size = product.size || [1.0, 1.0];
        const w    = size[0] || 1.0;
        const d    = size[1] || 1.0;
        const h    = product.height || 0.85;

        const geo  = new THREE.BoxGeometry(w, h, d);
        const mat  = new THREE.MeshStandardMaterial({
            color:       new THREE.Color(product.color || '#888888'),
            transparent: true,
            opacity:     0.75,
            roughness:   0.7,
            metalness:   0.0,
        });
        this.previewMesh = new THREE.Mesh(geo, mat);
        this.previewMesh.position.y    = h / 2;
        this.previewMesh.castShadow    = true;
        this.previewMesh.userData.isARPreview = true;
        this.scene.add(this.previewMesh);
    }

    _removePreview() {
        if (this.previewMesh) {
            this.scene.remove(this.previewMesh);
            if (this.previewMesh.geometry) this.previewMesh.geometry.dispose();
            if (this.previewMesh.material) this.previewMesh.material.dispose();
            this.previewMesh = null;
        }
    }

    async _loadGLB(url) {
        if (!window.THREE?.GLTFLoader) {
            // Lazy-load GLTFLoader from CDN
            await this._loadScript('https://cdn.jsdelivr.net/npm/three@0.157.0/examples/js/loaders/GLTFLoader.js');
        }
        return new Promise((resolve, reject) => {
            const loader = new THREE.GLTFLoader();
            loader.load(
                url,
                (gltf) => {
                    const model = gltf.scene;
                    model.traverse(child => {
                        if (child.isMesh) {
                            child.castShadow    = true;
                            child.receiveShadow = true;
                        }
                    });
                    resolve(model);
                },
                undefined,
                reject
            );
        });
    }

    _loadScript(src) {
        return new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
            const s  = document.createElement('script');
            s.src    = src;
            s.onload  = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    // ── Reticle ───────────────────────────────────────────────────────────────

    _initReticle() {
        const geo  = new THREE.RingGeometry(0.15, 0.2, 32).rotateX(-Math.PI / 2);
        const mat  = new THREE.MeshBasicMaterial({ color: 0x22d3ee, side: THREE.DoubleSide });
        this.reticle = new THREE.Mesh(geo, mat);
        this.reticle.visible = false;
        this.reticle.matrixAutoUpdate = false;
        this.scene.add(this.reticle);
    }

    // ── Placement Confirmation ────────────────────────────────────────────────

    async _confirmPlacement(position, product) {
        if (!product) return;

        // Dispatch placement event (ARSync will handle the backend call)
        window.dispatchEvent(new CustomEvent('ar:product-placed', {
            detail: {
                product,
                position: { x: position.x, y: position.y, z: position.z },
                source: this._mode,
            }
        }));

        // Flash preview to confirm
        if (this.previewMesh?.material) {
            const origColor = this.previewMesh.material.color?.clone();
            this.previewMesh.material.color?.set(0x22c55e);
            setTimeout(() => {
                if (this.previewMesh?.material && origColor)
                    this.previewMesh.material.color.copy(origColor);
            }, 400);
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    async _detectMode() {
        if (navigator.xr) {
            try {
                const supported = await navigator.xr.isSessionSupported('immersive-ar');
                if (supported) return 'webxr';
            } catch (_) {}
        }
        if (navigator.mediaDevices?.getUserMedia) return 'camera';
        return 'standard';
    }

    _updateOverlay(product) {
        const overlay = document.getElementById('ar-life-size-overlay');
        if (!overlay) return;
        const price = product.price ? `${product.price.toLocaleString()} ${product.currency || 'EGP'}` : '';
        const size  = product.size ? `${(product.size[0]*100).toFixed(0)}×${(product.size[1]*100).toFixed(0)} cm` : '';
        overlay.innerHTML = `
        <div class="ar-overlay-card">
          <img class="ar-overlay-img" src="${product.image_url || ''}" alt="${product.name}"/>
          <div class="ar-overlay-info">
            <div class="ar-overlay-series">${product.series || ''}</div>
            <div class="ar-overlay-name">${product.name || ''}</div>
            ${size  ? `<div class="ar-overlay-size">📐 ${size}</div>` : ''}
            ${price ? `<div class="ar-overlay-price">${price}</div>` : ''}
            <div class="ar-overlay-btns">
              <button onclick="window._arLifeSize?.stop()" class="ar-ovl-btn secondary">✕ Exit AR</button>
              <button onclick="window.dispatchEvent(new CustomEvent('ar:confirm-placement'))" class="ar-ovl-btn primary">✅ Place Here</button>
            </div>
          </div>
        </div>`;
        overlay.style.display = 'block';
        window._arLifeSize = this;
    }
}

export { ARLifeSize };
