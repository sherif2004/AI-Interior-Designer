/**
 * ar_placement_overlay.js — Phase 4A
 * =====================================
 * Ghost mesh overlay for furniture placement in camera background mode.
 * Shows a semi-transparent furniture preview that follows the cursor,
 * turns green (valid) or red (collision) before the user clicks to confirm.
 */

'use strict';

import { FloorRaycaster } from './floor_raycaster.js';
import { ARSyncCoordinator } from './ar_sync.js';

class ARPlacementOverlay {
    constructor(scene, camera, renderer, roomState) {
        this.scene     = scene;
        this.camera    = camera;
        this.renderer  = renderer;
        this.roomState = roomState;
        this.active    = false;

        this.raycaster = new FloorRaycaster(camera, renderer);
        this.raycaster.addToScene(scene);

        this.arSync    = new ARSyncCoordinator();
        this.ghostMesh = null;
        this.selectedType   = null;
        this.selectedProduct = null;

        // Materials
        this.matValid    = new THREE.MeshStandardMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.55 });
        this.matInvalid  = new THREE.MeshStandardMaterial({ color: 0xef4444, transparent: true, opacity: 0.55 });
        this.matNeutral  = new THREE.MeshStandardMaterial({ color: 0x6366f1, transparent: true, opacity: 0.45 });

        this._onMouseMoveBound  = this._onMouseMove.bind(this);
        this._onMouseClickBound = this._onMouseClick.bind(this);
        this._onKeyDownBound    = this._onKeyDown.bind(this);
    }

    /** Activate placement mode for a furniture type. */
    startPlacement(furnitureType, ikeaProduct = null) {
        this.selectedType    = furnitureType;
        this.selectedProduct = ikeaProduct;
        this._createGhost(furnitureType);

        if (!this.active) {
            this.active = true;
            const canvas = this.renderer.domElement;
            canvas.addEventListener('mousemove', this._onMouseMoveBound);
            canvas.addEventListener('click',     this._onMouseClickBound);
            window.addEventListener('keydown',   this._onKeyDownBound);
        }

        this._showCursor('crosshair');
        window.dispatchEvent(new CustomEvent('ar:placement-started', { detail: { type: furnitureType, ikeaProduct } }));
    }

    /** Deactivate placement mode. */
    stopPlacement() {
        if (!this.active) return;
        this.active = false;

        const canvas = this.renderer.domElement;
        canvas.removeEventListener('mousemove', this._onMouseMoveBound);
        canvas.removeEventListener('click',     this._onMouseClickBound);
        window.removeEventListener('keydown',   this._onKeyDownBound);

        this._removeGhost();
        this._showCursor('default');
        window.dispatchEvent(new CustomEvent('ar:placement-stopped'));
    }

    // ── Private ──────────────────────────────────────────────────────────────

    _createGhost(type) {
        this._removeGhost();

        const dims = this._getDims(type);
        const geo  = new THREE.BoxGeometry(dims.w, dims.h, dims.d);

        this.ghostMesh = new THREE.Mesh(geo, this.matNeutral.clone());
        this.ghostMesh.name = '__ghost__';
        this.ghostMesh.castShadow    = false;
        this.ghostMesh.receiveShadow = false;
        this.ghostMesh.position.y    = dims.h / 2;
        this.scene.add(this.ghostMesh);
    }

    _removeGhost() {
        if (this.ghostMesh) {
            this.scene.remove(this.ghostMesh);
            this.ghostMesh.geometry.dispose();
            this.ghostMesh = null;
        }
    }

    _onMouseMove(event) {
        if (!this.ghostMesh) return;

        const pos = this.raycaster.getFloorPosition(event);
        if (!pos) return;

        const snapped = FloorRaycaster.snapToGrid(pos, 0.25);
        const clamped = this._clampToRoom(snapped);

        this.ghostMesh.position.set(clamped.x, this.ghostMesh.position.y, clamped.z);

        // Collision check
        const hasCollision = this._checkCollision(clamped);
        const mat = hasCollision ? this.matInvalid : this.matValid;
        this.ghostMesh.material.color.set(mat.color);
        this.ghostMesh.material.opacity = hasCollision ? 0.65 : 0.55;

        window.dispatchEvent(new CustomEvent('ar:ghost-moved', {
            detail: { pos: clamped, valid: !hasCollision }
        }));
    }

    async _onMouseClick(event) {
        if (!this.ghostMesh || !this.selectedType) return;

        const pos = {
            x: this.ghostMesh.position.x,
            y: 0,
            z: this.ghostMesh.position.z,
        };

        const hasCollision = this._checkCollision(pos);
        if (hasCollision) {
            this._flashInvalid();
            return;
        }

        // Confirm placement
        await this.arSync.placeFromAR(
            this.selectedType,
            pos,
            0,
            this.selectedProduct?.color || null,
            this.selectedProduct,
        );

        // Flash success then re-arm for next placement
        this._flashValid();
        window.dispatchEvent(new CustomEvent('ar:item-placed', {
            detail: { type: this.selectedType, pos, product: this.selectedProduct }
        }));
    }

    _onKeyDown(event) {
        if (event.key === 'Escape') {
            this.stopPlacement();
        }
        if ((event.key === 'r' || event.key === 'R') && this.ghostMesh) {
            this.ghostMesh.rotation.y += Math.PI / 4; // rotate 45°
        }
    }

    _checkCollision(pos) {
        const objects = (this.roomState?.objects || []);
        const dims    = this._getDims(this.selectedType);
        const hw = dims.w / 2 + 0.1;
        const hd = dims.d / 2 + 0.1;

        for (const obj of objects) {
            const odims  = this._getDims(obj.type);
            const ohw    = odims.w / 2 + 0.1;
            const ohd    = odims.d / 2 + 0.1;
            const ox     = obj.x || 0;
            const oz     = obj.z || 0;

            if (
                Math.abs(pos.x - ox) < hw + ohw &&
                Math.abs(pos.z - oz) < hd + ohd
            ) return true;
        }
        return false;
    }

    _clampToRoom(pos) {
        const w = (this.roomState?.width  || 5) / 2 - 0.3;
        const d = (this.roomState?.depth  || 5) / 2 - 0.3;
        return {
            x: Math.max(-w, Math.min(w, pos.x)),
            y: 0,
            z: Math.max(-d, Math.min(d, pos.z)),
        };
    }

    _getDims(type = 'sofa') {
        const dims = {
            sofa:          { w: 2.2, h: 0.85, d: 0.9 },
            bed:           { w: 1.6, h: 0.5,  d: 2.1 },
            desk:          { w: 1.2, h: 0.75, d: 0.6 },
            dining_table:  { w: 1.4, h: 0.75, d: 0.85 },
            wardrobe:      { w: 1.2, h: 2.0,  d: 0.6 },
            chair:         { w: 0.5, h: 0.9,  d: 0.55 },
            coffee_table:  { w: 1.0, h: 0.45, d: 0.55 },
            tv_stand:      { w: 1.5, h: 0.5,  d: 0.4 },
            lamp:          { w: 0.4, h: 1.6,  d: 0.4 },
            bookshelf:     { w: 0.8, h: 2.0,  d: 0.3 },
            nightstand:    { w: 0.5, h: 0.6,  d: 0.4 },
            office_chair:  { w: 0.65,h: 1.1,  d: 0.65 },
            rug:           { w: 2.0, h: 0.02, d: 3.0 },
        };
        return dims[type] || { w: 0.8, h: 0.9, d: 0.8 };
    }

    _flashValid() {
        if (!this.ghostMesh) return;
        this.ghostMesh.material.color.set(0x22c55e);
        setTimeout(() => {
            if (this.ghostMesh) this.ghostMesh.material.color.set(0x22d3ee);
        }, 300);
    }

    _flashInvalid() {
        if (!this.ghostMesh) return;
        this.ghostMesh.material.color.set(0xef4444);
        setTimeout(() => {
            if (this.ghostMesh) this.ghostMesh.material.color.set(0x22d3ee);
        }, 500);
    }

    _showCursor(style) {
        if (this.renderer?.domElement) {
            this.renderer.domElement.style.cursor = style;
        }
    }
}

export { ARPlacementOverlay };
