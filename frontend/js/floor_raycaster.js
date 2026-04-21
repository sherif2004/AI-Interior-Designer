/**
 * floor_raycaster.js — Phase 4A
 * ================================
 * Converts 2D mouse clicks into 3D floor-plane coordinates.
 * Creates an invisible floor plane at y=0 and raycasts against it.
 * Used by the camera placement overlay to position furniture.
 */

'use strict';

class FloorRaycaster {
    constructor(camera, renderer) {
        this.camera   = camera;
        this.renderer = renderer;
        this.raycaster = new THREE.Raycaster();
        this.mouse     = new THREE.Vector2();

        // Invisible floor plane at y=0
        const geo = new THREE.PlaneGeometry(100, 100);
        const mat = new THREE.MeshBasicMaterial({ visible: false, side: THREE.DoubleSide });
        this.floorPlane = new THREE.Mesh(geo, mat);
        this.floorPlane.rotation.x = -Math.PI / 2;
        this.floorPlane.name = 'floor_raycaster_plane';
    }

    /** Add the invisible plane to a scene. */
    addToScene(scene) {
        scene.add(this.floorPlane);
    }

    /** Remove the invisible plane from a scene. */
    removeFromScene(scene) {
        scene.remove(this.floorPlane);
    }

    /**
     * Convert a mouse event (or {clientX, clientY}) to a 3D floor position.
     * @param {MouseEvent|{clientX,clientY}} event
     * @returns {{x: number, y: number, z: number} | null}
     */
    getFloorPosition(event) {
        const canvas = this.renderer.domElement;
        const rect   = canvas.getBoundingClientRect();

        this.mouse.set(
            ((event.clientX - rect.left) / rect.width)  * 2 - 1,
            -((event.clientY - rect.top)  / rect.height) * 2 + 1
        );

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const hits = this.raycaster.intersectObject(this.floorPlane);

        if (hits.length > 0) {
            const pt = hits[0].point;
            return { x: pt.x, y: 0, z: pt.z };
        }
        return null;
    }

    /**
     * Get normalized device coordinates from a mouse event.
     * @returns {{x: number, y: number}}
     */
    getNDC(event) {
        const canvas = this.renderer.domElement;
        const rect   = canvas.getBoundingClientRect();
        return {
            x: ((event.clientX - rect.left) / rect.width)  * 2 - 1,
            y: -((event.clientY - rect.top)  / rect.height) * 2 + 1,
        };
    }

    /**
     * Snap a position to the nearest grid point.
     * @param {{x,z}} pos
     * @param {number} gridSize — grid increment in metres (default: 0.25)
     */
    static snapToGrid(pos, gridSize = 0.25) {
        return {
            x: Math.round(pos.x / gridSize) * gridSize,
            y: pos.y || 0,
            z: Math.round(pos.z / gridSize) * gridSize,
        };
    }

    /**
     * Clamp a position within room bounds.
     * @param {{x,z}} pos
     * @param {number} roomW — room width in metres
     * @param {number} roomD — room depth in metres
     * @param {number} margin — clearance from walls
     */
    static clampToRoom(pos, roomW, roomD, margin = 0.3) {
        return {
            x: Math.max(-roomW / 2 + margin, Math.min(roomW / 2 - margin, pos.x)),
            y: pos.y || 0,
            z: Math.max(-roomD / 2 + margin, Math.min(roomD / 2 - margin, pos.z)),
        };
    }
}

export { FloorRaycaster };
