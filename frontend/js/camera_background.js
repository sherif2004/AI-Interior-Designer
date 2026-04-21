/**
 * camera_background.js — Phase 4A
 * =================================
 * Manages the live camera feed as the Three.js scene background.
 * Supports: camera toggle, frame capture for room scanning, desktop mode.
 */

'use strict';

class CameraBackground {
    constructor(renderer, scene) {
        this.renderer  = renderer;
        this.scene     = scene;
        this.stream    = null;
        this.video     = null;
        this.texture   = null;
        this.active    = false;
        this.prevBg    = null;
        this._onResizeBound = this._onResize.bind(this);
    }

    /** Start live camera feed as scene background. */
    async start() {
        if (this.active) return;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false,
            });
        } catch (err) {
            // Fallback to any camera
            try {
                this.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            } catch (err2) {
                throw new Error(`Camera access denied: ${err2.message}`);
            }
        }

        // Create hidden video element
        this.video = document.createElement('video');
        this.video.srcObject    = this.stream;
        this.video.autoplay     = true;
        this.video.playsInline  = true;
        this.video.muted        = true;
        this.video.style.display = 'none';
        document.body.appendChild(this.video);
        await this.video.play();

        // Create Three.js VideoTexture
        if (window.THREE) {
            this.texture = new THREE.VideoTexture(this.video);
            this.texture.minFilter = THREE.LinearFilter;
            this.texture.magFilter = THREE.LinearFilter;
            this.prevBg  = this.scene.background;
            this.scene.background = this.texture;
        }

        this.active = true;
        window.addEventListener('resize', this._onResizeBound);
        this._onResize();
        console.log('[Camera] Live feed started');
        this._dispatchEvent('camera:started');
    }

    /** Stop the camera feed and restore the previous scene background. */
    stop() {
        if (!this.active) return;

        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }
        if (this.video && this.video.parentNode) {
            this.video.parentNode.removeChild(this.video);
            this.video = null;
        }
        if (this.texture) {
            this.texture.dispose();
            this.texture = null;
        }
        if (this.scene) {
            this.scene.background = this.prevBg;
        }
        this.active = false;
        window.removeEventListener('resize', this._onResizeBound);
        console.log('[Camera] Feed stopped');
        this._dispatchEvent('camera:stopped');
    }

    /** Toggle camera on/off. */
    async toggle() {
        if (this.active) {
            this.stop();
        } else {
            await this.start();
        }
        return this.active;
    }

    /**
     * Capture the current video frame as a base64 JPEG string.
     * Optionally draws onto a canvas for display.
     */
    captureFrame(quality = 0.85) {
        if (!this.video || !this.active) return null;

        const canvas  = document.createElement('canvas');
        canvas.width  = this.video.videoWidth  || 1280;
        canvas.height = this.video.videoHeight || 720;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);

        const dataUrl = canvas.toDataURL('image/jpeg', quality);
        const base64  = dataUrl.split(',')[1];
        return { dataUrl, base64 };
    }

    /**
     * Capture a frame and send it to the backend /scan/frame endpoint.
     * Returns the extracted room state update.
     */
    async scanFrame() {
        const frame = this.captureFrame();
        if (!frame) return null;

        try {
            const res = await fetch('/scan/frame', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ image: frame.base64, format: 'jpeg' }),
            });
            return await res.json();
        } catch (err) {
            console.error('[Camera] Scan frame error:', err);
            return null;
        }
    }

    _onResize() {
        if (this.texture) {
            this.texture.needsUpdate = true;
        }
    }

    _dispatchEvent(name, detail = {}) {
        window.dispatchEvent(new CustomEvent(name, { detail }));
    }
}

// ─── Camera Toggle UI ────────────────────────────────────────────────────────

function initCameraToggle(renderer, scene) {
    const camBg = new CameraBackground(renderer, scene);
    window._cameraBackground = camBg;

    const btn = document.getElementById('btn-camera-toggle');
    if (!btn) return camBg;

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        try {
            const isOn = await camBg.toggle();
            btn.textContent = isOn ? '📷 Camera OFF' : '📷 Camera ON';
            btn.classList.toggle('active', isOn);

            // Show/hide camera scan button
            const scanBtn = document.getElementById('btn-camera-scan');
            if (scanBtn) scanBtn.style.display = isOn ? 'inline-block' : 'none';
        } catch (err) {
            alert(`Camera error: ${err.message}`);
        } finally {
            btn.disabled = false;
        }
    });

    // Scan frame button
    const scanBtn = document.getElementById('btn-camera-scan');
    if (scanBtn) {
        scanBtn.style.display = 'none';
        scanBtn.addEventListener('click', async () => {
            scanBtn.textContent = '🔍 Scanning...';
            scanBtn.disabled = true;
            try {
                const result = await camBg.scanFrame();
                if (result && result.actions && result.actions.length > 0) {
                    window.dispatchEvent(new CustomEvent('camera:scan-result', { detail: result }));
                    scanBtn.textContent = `✅ Found ${result.furniture?.length || 0} items`;
                } else {
                    scanBtn.textContent = '📷 Scan Room';
                }
            } finally {
                scanBtn.disabled = false;
                setTimeout(() => { scanBtn.textContent = '📷 Scan Room'; }, 2000);
            }
        });
    }

    return camBg;
}

export { CameraBackground, initCameraToggle };
