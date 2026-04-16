/**
 * Three.js scene setup — room renderer with 3D furniture.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createFurnitureMesh } from './furniture.js';

let renderer, scene, camera, controls;
let floorMesh, wallMeshes = [], gridHelper;
let openingMeshes = [];
let floorMaterialRef = null;
let furnitureMeshMap = {}; // id → THREE.Group

const SCALE = 0.5; // 1 meter = 0.5 THREE units (for comfort)

/**
 * Initialize the Three.js scene.
 * @param {HTMLCanvasElement} canvas
 */
export function initScene(canvas) {
  // Renderer
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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
  const ambient = new THREE.AmbientLight(0x7080c0, 0.5);
  scene.add(ambient);

  const sun = new THREE.DirectionalLight(0xfff5e0, 1.4);
  sun.position.set(8, 12, 6);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.near = 0.5;
  sun.shadow.camera.far = 50;
  sun.shadow.camera.left = -15;
  sun.shadow.camera.right = 15;
  sun.shadow.camera.top = 15;
  sun.shadow.camera.bottom = -15;
  sun.shadow.bias = -0.001;
  scene.add(sun);

  const fill = new THREE.DirectionalLight(0x4080ff, 0.3);
  fill.position.set(-5, 5, -3);
  scene.add(fill);

  // Point light (warm ambience)
  const pointLight = new THREE.PointLight(0xf5c842, 0.6, 10);
  pointLight.position.set(2.5, 3, 2);
  scene.add(pointLight);

  // Resize
  _handleResize(canvas);
  window.addEventListener('resize', () => _handleResize(canvas));

  // Animate
  _animate();
}

function _animate() {
  requestAnimationFrame(_animate);
  controls.update();
  renderer.render(scene, camera);
}

function _handleResize(canvas) {
  const rect = canvas.parentElement.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height, false);
  camera.aspect = rect.width / rect.height;
  camera.updateProjectionMatrix();
}

/**
 * Build / rebuild the room geometry from state.
 * @param {object} roomData  {width, height, wall_thickness, doors, windows}
 */
export function buildRoom(roomData) {
  // Remove existing room meshes
  if (floorMesh) scene.remove(floorMesh);
  wallMeshes.forEach(m => scene.remove(m));
  openingMeshes.forEach(m => scene.remove(m));
  if (gridHelper) scene.remove(gridHelper);
  wallMeshes = [];
  openingMeshes = [];

  const rw = roomData.width * SCALE;
  const rh = roomData.height * SCALE;
  const wallH = (roomData.ceiling_height || 3.0) * SCALE;
  const wallT = 0.05;
  const floorStyle = roomData.floor_style || {};
  const wallStyle = roomData.wall_style || {};

  // Floor
  const floorGeo = new THREE.PlaneGeometry(rw, rh);
  const floorMat = createSurfaceMaterial(
    floorStyle.color || '#1a2240',
    floorStyle.material || 'wood',
    true,
  );
  floorMaterialRef = floorMat;
  floorMesh = new THREE.Mesh(floorGeo, floorMat);
  floorMesh.rotation.x = -Math.PI / 2;
  floorMesh.position.set(rw / 2, 0, rh / 2);
  floorMesh.receiveShadow = true;
  scene.add(floorMesh);

  // Grid
  gridHelper = new THREE.GridHelper(Math.max(rw, rh) + 2, Math.max(roomData.width, roomData.height) + 2, 0x1e2d55, 0x1e2d55);
  gridHelper.material.opacity = 0.35;
  gridHelper.material.transparent = true;
  gridHelper.position.set(rw / 2, 0.001, rh / 2);
  scene.add(gridHelper);

  // Walls (thin outlines)
  const wallMat = createSurfaceMaterial(
    wallStyle.color || '#2a3a6a',
    wallStyle.material || 'paint',
    false,
  );
  const walls = [
    { pos: [rw / 2, wallH / 2, 0],  size: [rw, wallH, wallT] },          // north
    { pos: [rw / 2, wallH / 2, rh], size: [rw, wallH, wallT] },          // south
    { pos: [0,      wallH / 2, rh / 2], size: [wallT, wallH, rh] },      // west
    { pos: [rw,     wallH / 2, rh / 2], size: [wallT, wallH, rh] },      // east
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

  // Reframe camera
  controls.target.set(rw / 2, 0, rh / 2);
  camera.position.set(rw / 2, Math.max(rw, rh) * 0.9, rh * 1.4);
  controls.update();
}

function buildOpenings(roomData, rw, rh, wallH) {
  const windows = roomData.windows || [];
  const doors = roomData.doors || [];

  for (const windowDef of windows) {
    const mesh = buildOpeningMesh(windowDef, rw, rh, wallH, 0x87ceeb, 1.1, 0.08);
    if (mesh) {
      scene.add(mesh);
      openingMeshes.push(mesh);
    }
  }

  for (const doorDef of doors) {
    const mesh = buildOpeningMesh(doorDef, rw, rh, wallH, 0x8b5a2b, 2.0, 0.12);
    if (mesh) {
      scene.add(mesh);
      openingMeshes.push(mesh);
    }
  }
}

function buildOpeningMesh(def, rw, rh, wallH, color, heightMeters, thickness) {
  const width = (def.width || 1.0) * SCALE;
  const height = Math.min(wallH * 0.85, heightMeters * SCALE);
  const geo = new THREE.BoxGeometry(width, height, thickness);
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.05, transparent: color === 0x87ceeb, opacity: color === 0x87ceeb ? 0.55 : 1 });
  const mesh = new THREE.Mesh(geo, mat);

  const wall = String(def.wall || 'north').toLowerCase();
  const pos = Math.min(0.95, Math.max(0.05, def.position || 0.5));
  const y = color === 0x87ceeb ? wallH * 0.58 : height / 2;

  if (wall === 'north') {
    mesh.position.set(rw * pos, y, 0.03);
  } else if (wall === 'south') {
    mesh.position.set(rw * pos, y, rh - 0.03);
  } else if (wall === 'west') {
    mesh.rotation.y = Math.PI / 2;
    mesh.position.set(0.03, y, rh * pos);
  } else if (wall === 'east') {
    mesh.rotation.y = Math.PI / 2;
    mesh.position.set(rw - 0.03, y, rh * pos);
  } else {
    return null;
  }

  return mesh;
}

function createSurfaceMaterial(color, materialType, isFloor = false) {
  const matType = String(materialType || '').toLowerCase();
  const baseColor = new THREE.Color(color || (isFloor ? '#1a2240' : '#2a3a6a'));

  let roughness = isFloor ? 0.85 : 0.9;
  let metalness = 0.02;

  if (matType.includes('marble') || matType.includes('stone')) {
    roughness = 0.35;
    metalness = 0.08;
  } else if (matType.includes('tile')) {
    roughness = 0.55;
  } else if (matType.includes('wood')) {
    roughness = 0.75;
  } else if (matType.includes('concrete')) {
    roughness = 0.95;
  } else if (matType.includes('panel')) {
    roughness = 0.7;
  } else if (matType.includes('wallpaper')) {
    roughness = 0.88;
  }

  return new THREE.MeshStandardMaterial({
    color: baseColor,
    roughness,
    metalness,
  });
}

/**
 * Sync Three.js scene with the full objects array from state.
 * Adds new objects, removes deleted ones, updates moved ones.
 * @param {Array} objects
 */
export function syncObjects(objects) {
  const newIds = new Set(objects.map(o => o.id));

  // Remove deleted objects
  for (const id of Object.keys(furnitureMeshMap)) {
    if (!newIds.has(id)) {
      scene.remove(furnitureMeshMap[id]);
      delete furnitureMeshMap[id];
    }
  }

  // Add / update objects
  for (const obj of objects) {
    if (furnitureMeshMap[obj.id]) {
      // Update position/rotation smoothly
      _animateObject(furnitureMeshMap[obj.id], obj);
    } else {
      // Create new mesh
      const group = createFurnitureMesh(obj);
      scene.add(group);
      furnitureMeshMap[obj.id] = group;

      // Entrance animation: drop from above
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

  const start = {
    x: group.position.x,
    y: group.position.y,
    z: group.position.z,
    ry: group.rotation.y,
  };
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
 * Highlight a specific object (e.g. on inventory click).
 */
export function highlightObject(id) {
  for (const [meshId, group] of Object.entries(furnitureMeshMap)) {
    group.traverse(child => {
      if (child.isMesh) {
        child.material.emissive = meshId === id
          ? new THREE.Color(0xf5c842)
          : new THREE.Color(0x000000);
        child.material.emissiveIntensity = meshId === id ? 0.3 : 0;
      }
    });
  }
}

export { SCALE };
