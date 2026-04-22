/**
 * Three.js scene setup — room renderer with 3D furniture.
 * Phase 2 additions:
 *   - Day/night lighting cycle
 *   - Measurement lines between selected objects
 *   - Clearance warning halos
 *   - Improved shadow quality (VSM)
 *   - Hemisphere light for ambient occlusion approximation
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createFurnitureMesh } from './furnitureFactory.js';
import { WalkthroughController } from './walkthrough.js';

export let renderer, scene, camera, controls;
let floorMesh, wallMeshes = [], gridHelper;
let openingMeshes = [];
let furnitureMeshMap = {}; // id → THREE.Group
let walkthrough = null;

// Lighting refs for day/night control
let sunLight, ambientLight, hemiLight, fillLight;

// Measurement & clearance overlays
let measurementLines = [];
let clearanceHalos = [];

export const SCALE = 0.5; // 1 meter = 0.5 THREE units

// Current time of day (0–24)
let _timeOfDay = 14;

/**
 * Initialize the Three.js scene.
 * @param {HTMLCanvasElement} canvas
 */
export function initScene(canvas) {
  // Renderer — use VSM shadow maps for better quality
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.VSMShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.setClearColor(0x080d1c);

  // Scene
  scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x080d1c, 15, 40);

  // Camera
  camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
  camera.position.set(6, 9, 12);
  camera.lookAt(2.5, 0, 2);

  // Orbit controls
  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.minDistance = 2;
  controls.maxDistance = 30;
  controls.maxPolarAngle = Math.PI / 2.05;
  controls.target.set(2.5, 0, 2);

  // Lights
  _buildLights();

  // Resize
  _handleResize(canvas);
  window.addEventListener('resize', () => _handleResize(canvas));

  // Animate
  _animate();
}

function _buildLights() {
  // Hemisphere light (sky/ground — ambient occlusion approximation)
  hemiLight = new THREE.HemisphereLight(0x7080c0, 0x3a2a1a, 0.6);
  scene.add(hemiLight);

  // Sun directional light
  sunLight = new THREE.DirectionalLight(0xfff5e0, 1.4);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(2048, 2048);
  sunLight.shadow.camera.near = 0.5;
  sunLight.shadow.camera.far = 50;
  sunLight.shadow.camera.left = -15;
  sunLight.shadow.camera.right = 15;
  sunLight.shadow.camera.top = 15;
  sunLight.shadow.camera.bottom = -15;
  sunLight.shadow.bias = -0.001;
  sunLight.shadow.radius = 3; // VSM soft shadows
  scene.add(sunLight);

  // Cool fill light from opposite side
  fillLight = new THREE.DirectionalLight(0x4080ff, 0.3);
  fillLight.position.set(-5, 5, -3);
  scene.add(fillLight);

  // Apply time of day
  setTimeOfDay(_timeOfDay);
}

/**
 * Set time of day (0–24) and update sun position / colour / intensity.
 * @param {number} hour - 0 to 24
 */
export function setTimeOfDay(hour) {
  _timeOfDay = Math.max(0, Math.min(24, hour));

  // Sun arc: rises at 6, peaks at 12, sets at 20
  const t = (_timeOfDay - 6) / 14; // 0 → 1 over daytime
  const isNight = _timeOfDay < 6 || _timeOfDay > 20;

  if (isNight) {
    sunLight.intensity = 0.05;
    ambientLight && (ambientLight.intensity = 0.1);
    hemiLight.intensity = 0.15;
    fillLight.intensity = 0.05;
    renderer.toneMappingExposure = 0.6;
    scene.fog.color.set(0x050810);
    renderer.setClearColor(0x050810);
    hemiLight.color.set(0x202040);
  } else {
    const normalized = Math.sin(Math.PI * t); // 0→1→0 arc
    sunLight.intensity = 0.4 + normalized * 1.4;

    // Warm at sunrise/sunset, white at noon
    const warmth = 1 - Math.abs(t - 0.5) * 2;
    const sunColor = new THREE.Color();
    sunColor.r = 1.0;
    sunColor.g = 0.8 + warmth * 0.2;
    sunColor.b = 0.6 + warmth * 0.4;
    sunLight.color.copy(sunColor);

    // Sun position arc
    const angle = Math.PI * t;
    sunLight.position.set(
      -Math.cos(angle) * 12,
      Math.sin(angle) * 12,
      6
    );

    hemiLight.intensity = 0.3 + normalized * 0.5;
    hemiLight.color.set(normalized > 0.5 ? 0x88aaff : 0xffaa66);
    fillLight.intensity = 0.15 + normalized * 0.2;

    renderer.toneMappingExposure = 0.9 + normalized * 0.3;
    const fogColor = new THREE.Color().lerpColors(
      new THREE.Color(0x1a2040),
      new THREE.Color(0x080d1c),
      normalized
    );
    scene.fog.color.copy(fogColor);
    renderer.setClearColor(fogColor);
  }
}

function _animate() {
  requestAnimationFrame(_animate);
  if (walkthrough?.enabled) {
    walkthrough.update(1 / 60);
  }
  controls.update();
  renderer.render(scene, camera);
}

export function setWalkthroughEnabled(enabled, canvasEl = null) {
  const want = Boolean(enabled);
  if (want) {
    if (!walkthrough) walkthrough = new WalkthroughController({ camera, domElement: canvasEl || renderer.domElement, scene });
    controls.enabled = false;
    walkthrough.start();
  } else {
    if (walkthrough) walkthrough.stop();
    controls.enabled = true;
  }
}

export function isWalkthroughEnabled() {
  return Boolean(walkthrough?.enabled);
}

function _handleResize(canvas) {
  const rect = canvas.parentElement.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height, false);
  camera.aspect = rect.width / rect.height;
  camera.updateProjectionMatrix();
}

/**
 * Build / rebuild the room geometry from state.
 */
export function buildRoom(roomData) {
  if (floorMesh) scene.remove(floorMesh);
  wallMeshes.forEach(m => scene.remove(m));
  openingMeshes.forEach(m => scene.remove(m));
  if (gridHelper) scene.remove(gridHelper);
  wallMeshes = [];
  openingMeshes = [];

  const rw = (roomData.room_width || roomData.width || 10) * SCALE;
  const rh = (roomData.room_depth || roomData.height || 8) * SCALE;
  const wallH = (roomData.ceiling_height || 3.0) * SCALE;
  const wallT = 0.05;
  const floorStyle = roomData.floor_style || {};
  const wallStyle = roomData.wall_style || {};

  // Floor
  const floorMat = createSurfaceMaterial(floorStyle.color || '#1a2240', floorStyle.material || 'wood', true);
  
  if (roomData.floor_polygon && roomData.floor_polygon.length > 2) {
    // Custom shape floor
    const shape = new THREE.Shape();
    roomData.floor_polygon.forEach((pt, idx) => {
      // translate from center (0,0) to center (rw/2, rh/2)
      const px = (pt.x * SCALE) + (rw / 2);
      const pz = (pt.z * SCALE) + (rh / 2);
      if (idx === 0) shape.moveTo(px, -pz); // three.js shapes are drawn in XY, we rotate to XZ later so y becomes -z essentially
      else shape.lineTo(px, -pz);
    });
    
    const floorGeo = new THREE.ShapeGeometry(shape);
    floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.set(0, 0, 0); // shape points are already in target world coords 
    floorMesh.receiveShadow = true;
    scene.add(floorMesh);
  } else {
    // Basic rectangular floor
    const floorGeo = new THREE.PlaneGeometry(rw, rh);
    floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.position.set(rw / 2, 0, rh / 2);
    floorMesh.receiveShadow = true;
    scene.add(floorMesh);
  }

  // Grid
  gridHelper = new THREE.GridHelper(
    Math.max(rw, rh) + 2,
    Math.max(roomData.room_width || roomData.width || 10, roomData.room_depth || roomData.height || 8) + 2,
    0x1e2d55, 0x1e2d55
  );
  gridHelper.material.opacity = 0.35;
  gridHelper.material.transparent = true;
  gridHelper.position.set(rw / 2, 0.001, rh / 2);
  scene.add(gridHelper);

  // Walls
  const wallMat = createSurfaceMaterial(wallStyle.color || '#2a3a6a', wallStyle.material || 'paint', false);
  
  if (roomData.walls && roomData.walls.length > 0) {
    // Parse backend wall blocks
    for (const w of roomData.walls) {
      if (!w.geometry) continue;
      const geo = new THREE.BoxGeometry(
        w.geometry.dimensions.width * SCALE,
        w.geometry.dimensions.height * SCALE,
        w.geometry.dimensions.depth * SCALE
      );
      const mesh = new THREE.Mesh(geo, wallMat);
      
      // wall pos relative to center, translate to bottom right
      const px = (w.geometry.position.x * SCALE) + (rw / 2);
      const py = w.geometry.position.y * SCALE;
      const pz = (w.geometry.position.z * SCALE) + (rh / 2);
      
      mesh.position.set(px, py, pz);
      mesh.rotation.y = w.geometry.rotation_y * (Math.PI / 180);
      mesh.receiveShadow = true;
      scene.add(mesh);
      wallMeshes.push(mesh);
      
      // NOTE: Openings for custom walls could be handled via CSG (ThreeBSP) in the future.
      // For now we render solid walls.
    }
  } else {
    // Basic rectangle walls
    const walls = [
      { pos: [rw / 2, wallH / 2, 0],       size: [rw, wallH, wallT] },  // north
      { pos: [rw / 2, wallH / 2, rh],      size: [rw, wallH, wallT] },  // south
      { pos: [0,      wallH / 2, rh / 2],  size: [wallT, wallH, rh] },  // west
      { pos: [rw,     wallH / 2, rh / 2],  size: [wallT, wallH, rh] },  // east
    ];
    for (const w of walls) {
      const geo = new THREE.BoxGeometry(...w.size);
      const mesh = new THREE.Mesh(geo, wallMat);
      mesh.position.set(...w.pos);
      mesh.receiveShadow = true;
      scene.add(mesh);
      wallMeshes.push(mesh);
    }
    
    buildOpenings(roomData, rw, rh, wallH);
  }

  controls.target.set(rw / 2, 0, rh / 2);
  camera.position.set(rw / 2, Math.max(rw, rh) * 0.9, rh * 1.4);
  controls.update();
}

function buildOpenings(roomData, rw, rh, wallH) {
  for (const def of (roomData.windows || [])) {
    const mesh = buildOpeningMesh(def, rw, rh, wallH, 0x87ceeb, 1.1, 0.08);
    if (mesh) { scene.add(mesh); openingMeshes.push(mesh); }
  }
  for (const def of (roomData.doors || [])) {
    const mesh = buildOpeningMesh(def, rw, rh, wallH, 0x8b5a2b, 2.0, 0.12);
    if (mesh) { scene.add(mesh); openingMeshes.push(mesh); }
  }
}

function buildOpeningMesh(def, rw, rh, wallH, color, heightMeters, thickness) {
  const width = (def.width || 1.0) * SCALE;
  const height = Math.min(wallH * 0.85, heightMeters * SCALE);
  const geo = new THREE.BoxGeometry(width, height, thickness);
  const isWindow = color === 0x87ceeb;
  const mat = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.5,
    metalness: isWindow ? 0.1 : 0.05,
    transparent: isWindow,
    opacity: isWindow ? 0.55 : 1,
  });
  const mesh = new THREE.Mesh(geo, mat);
  const wall = String(def.wall || 'north').toLowerCase();
  const pos = Math.min(0.95, Math.max(0.05, def.position || 0.5));
  const y = isWindow ? wallH * 0.58 : height / 2;
  if (wall === 'north') mesh.position.set(rw * pos, y, 0.03);
  else if (wall === 'south') mesh.position.set(rw * pos, y, rh - 0.03);
  else if (wall === 'west') { mesh.rotation.y = Math.PI / 2; mesh.position.set(0.03, y, rh * pos); }
  else if (wall === 'east') { mesh.rotation.y = Math.PI / 2; mesh.position.set(rw - 0.03, y, rh * pos); }
  else return null;
  return mesh;
}

function createSurfaceMaterial(color, materialType, isFloor = false) {
  const matType = String(materialType || '').toLowerCase();
  const baseColor = new THREE.Color(color || (isFloor ? '#1a2240' : '#2a3a6a'));
  let roughness = isFloor ? 0.85 : 0.9;
  let metalness = 0.02;
  if (matType.includes('marble') || matType.includes('stone')) { roughness = 0.35; metalness = 0.08; }
  else if (matType.includes('tile')) { roughness = 0.55; }
  else if (matType.includes('wood')) { roughness = 0.75; }
  else if (matType.includes('concrete')) { roughness = 0.95; }
  else if (matType.includes('panel')) { roughness = 0.7; }
  else if (matType.includes('wallpaper')) { roughness = 0.88; }
  return new THREE.MeshStandardMaterial({ color: baseColor, roughness, metalness });
}

/**
 * Sync Three.js scene with objects from state.
 */
export function syncObjects(objects) {
  const newIds = new Set(objects.map(o => o.id));
  for (const id of Object.keys(furnitureMeshMap)) {
    if (!newIds.has(id)) {
      scene.remove(furnitureMeshMap[id]);
      delete furnitureMeshMap[id];
    }
  }
  for (const obj of objects) {
    if (furnitureMeshMap[obj.id]) {
      _animateObject(furnitureMeshMap[obj.id], obj);
    } else {
      const group = createFurnitureMesh(obj);
      scene.add(group);
      furnitureMeshMap[obj.id] = group;
      group.position.y = obj.height * SCALE + 2;
      _animateObject(group, obj, true);
    }
  }
}

function _animateObject(group, obj, isNew = false) {
  const targetX = obj.x * SCALE + obj.w * SCALE / 2;
  const targetZ = obj.z * SCALE + obj.d * SCALE / 2;
  const targetY = obj.height * SCALE / 2;
  const targetRotY = -(obj.rotation || 0) * Math.PI / 180;
  const start = { x: group.position.x, y: group.position.y, z: group.position.z, ry: group.rotation.y };
  const duration = isNew ? 500 : 350;
  const startTime = performance.now();
  function tick() {
    const t = Math.min((performance.now() - startTime) / duration, 1);
    const e = _easeOutBack(t);
    group.position.x = start.x + (targetX - start.x) * e;
    group.position.z = start.z + (targetZ - start.z) * e;
    group.position.y = start.y + (targetY - start.y) * e;
    group.rotation.y = start.ry + _shortAngle(start.ry, targetRotY) * e;
    if (t < 1) requestAnimationFrame(tick);
  }
  tick();
}

function _easeOutBack(t) {
  const c1 = 1.70158, c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}

function _shortAngle(from, to) {
  let diff = (to - from) % (Math.PI * 2);
  if (diff > Math.PI) diff -= Math.PI * 2;
  if (diff < -Math.PI) diff += Math.PI * 2;
  return diff;
}

/**
 * Highlight a specific object on inventory click.
 */
export function highlightObject(id) {
  for (const [meshId, group] of Object.entries(furnitureMeshMap)) {
    group.traverse(child => {
      if (child.isMesh) {
        child.material.emissive = meshId === id ? new THREE.Color(0xf5c842) : new THREE.Color(0x000000);
        child.material.emissiveIntensity = meshId === id ? 0.3 : 0;
      }
    });
  }
}

// ─────────────────────── Phase 2: Measurement Lines ─────────────────────────

let _measureMode = false;
let _selectedForMeasure = [];

export function setMeasureMode(active) {
  _measureMode = active;
  _selectedForMeasure = [];
  clearMeasurementLines();
  if (!active) clearMeasurementLines();
}

export function handleObjectClick(objectId) {
  if (!_measureMode) return;

  if (_selectedForMeasure.includes(objectId)) {
    _selectedForMeasure = _selectedForMeasure.filter(id => id !== objectId);
    return;
  }
  _selectedForMeasure.push(objectId);
  if (_selectedForMeasure.length === 2) {
    drawMeasurementLine(_selectedForMeasure[0], _selectedForMeasure[1]);
    _selectedForMeasure = [];
  }
}

export function drawMeasurementLine(idA, idB) {
  const ga = furnitureMeshMap[idA];
  const gb = furnitureMeshMap[idB];
  if (!ga || !gb) return;

  const posA = ga.position.clone();
  const posB = gb.position.clone();
  posA.y = 0.3;
  posB.y = 0.3;

  // Distance line
  const points = [posA, posB];
  const geo = new THREE.BufferGeometry().setFromPoints(points);
  const mat = new THREE.LineBasicMaterial({ color: 0xf5c842, linewidth: 2 });
  const line = new THREE.Line(geo, mat);
  scene.add(line);
  measurementLines.push(line);

  // Distance label (as a sprite)
  const distMeters = (posA.distanceTo(posB) / SCALE).toFixed(2);
  const labelSprite = _makeTextSprite(`${distMeters}m`, 0xf5c842);
  labelSprite.position.copy(posA.clone().lerp(posB, 0.5));
  labelSprite.position.y = 0.6;
  scene.add(labelSprite);
  measurementLines.push(labelSprite);
}

export function clearMeasurementLines() {
  for (const obj of measurementLines) scene.remove(obj);
  measurementLines = [];
}

function _makeTextSprite(text, color) {
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'rgba(0,0,0,0.65)';
  ctx.roundRect(4, 4, 248, 56, 12);
  ctx.fill();
  ctx.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
  ctx.font = 'bold 28px Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 128, 32);
  const texture = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(1.2, 0.4, 1);
  return sprite;
}

// ─────────────────────── Phase 2: Clearance Halos ───────────────────────────

export function showClearanceWarnings(warnings, objects) {
  // Remove old halos
  for (const h of clearanceHalos) scene.remove(h);
  clearanceHalos = [];

  const warningIds = new Set();
  const errorIds = new Set();
  for (const w of warnings) {
    if (w.severity === 'error') { errorIds.add(w.object_id); if (w.other_id) errorIds.add(w.other_id); }
    else { warningIds.add(w.object_id); if (w.other_id) warningIds.add(w.other_id); }
  }

  for (const obj of objects) {
    const group = furnitureMeshMap[obj.id];
    if (!group) continue;

    let color = null;
    if (errorIds.has(obj.id)) color = 0xff3333;
    else if (warningIds.has(obj.id)) color = 0xffaa00;
    if (!color) continue;

    const radius = Math.max(obj.w, obj.d) * SCALE * 0.75;
    const geo = new THREE.RingGeometry(radius, radius + 0.04, 32);
    const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.7, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(geo, mat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(group.position.x, 0.01, group.position.z);
    scene.add(ring);
    clearanceHalos.push(ring);
  }
}

export function clearClearanceWarnings() {
  for (const h of clearanceHalos) scene.remove(h);
  clearanceHalos = [];
}
