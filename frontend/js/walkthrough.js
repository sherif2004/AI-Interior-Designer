/**
 * Phase 5.4 (MVP) — First-person walkthrough
 * Pointer lock + WASD movement on a flat plane.
 */

import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';

export class WalkthroughController {
  constructor({ camera, domElement, scene }) {
    this.camera = camera;
    this.domElement = domElement;
    this.scene = scene;

    this.controls = new PointerLockControls(camera, domElement);
    this.enabled = false;

    this.velocity = new THREE.Vector3();
    this.direction = new THREE.Vector3();
    this.keys = { w: false, a: false, s: false, d: false, shift: false };

    this._onKeyDown = (e) => this._handleKey(e, true);
    this._onKeyUp = (e) => this._handleKey(e, false);
  }

  start() {
    if (this.enabled) return;
    this.enabled = true;
    document.addEventListener('keydown', this._onKeyDown);
    document.addEventListener('keyup', this._onKeyUp);
    this.controls.lock();
  }

  stop() {
    if (!this.enabled) return;
    this.enabled = false;
    document.removeEventListener('keydown', this._onKeyDown);
    document.removeEventListener('keyup', this._onKeyUp);
    try { this.controls.unlock(); } catch {}
  }

  _handleKey(e, down) {
    const k = (e.key || '').toLowerCase();
    if (k === 'w') this.keys.w = down;
    if (k === 'a') this.keys.a = down;
    if (k === 's') this.keys.s = down;
    if (k === 'd') this.keys.d = down;
    if (k === 'shift') this.keys.shift = down;
    if (k === 'escape' && down) this.stop();
  }

  update(dt) {
    if (!this.enabled) return;
    const speed = this.keys.shift ? 4.2 : 2.6;

    // Damp
    this.velocity.x -= this.velocity.x * 8.0 * dt;
    this.velocity.z -= this.velocity.z * 8.0 * dt;

    this.direction.z = Number(this.keys.w) - Number(this.keys.s);
    this.direction.x = Number(this.keys.d) - Number(this.keys.a);
    this.direction.normalize();

    if (this.keys.w || this.keys.s) this.velocity.z -= this.direction.z * speed * dt;
    if (this.keys.a || this.keys.d) this.velocity.x -= this.direction.x * speed * dt;

    this.controls.moveRight(-this.velocity.x);
    this.controls.moveForward(-this.velocity.z);

    // Clamp to "floor": keep eye height stable
    this.camera.position.y = Math.max(0.9, this.camera.position.y);
  }
}

