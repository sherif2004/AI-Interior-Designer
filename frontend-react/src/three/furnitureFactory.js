/**
 * Furniture mesh factory — creates 3D representations for each furniture type.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const SCALE = 0.5; // 1 meter → 0.5 THREE units

// Texture cache so repeated products don't re-download images
const _texCache = new Map(); // url -> THREE.Texture
const _loader = new THREE.TextureLoader();

function _proxiedImgUrl(url) {
  if (!url) return '';
  try { return `/img?u=${encodeURIComponent(url)}`; } catch { return url; }
}

function _applyProductTexture(group, obj, w, d, h) {
  const raw = obj?.image_url;
  if (!raw) return;
  const url = _proxiedImgUrl(raw);
  if (!url) return;

  let tex = _texCache.get(url);
  if (!tex) {
    tex = _loader.load(
      url,
      (t) => {
        t.colorSpace = THREE.SRGBColorSpace;
        t.anisotropy = 4;
        t.needsUpdate = true;
      },
      undefined,
      () => {}
    );
    _texCache.set(url, tex);
  }

  // Put the product image on a top "label" plane so the 3D object looks like the real product.
  const geo = new THREE.PlaneGeometry(Math.max(0.12, w * 0.95), Math.max(0.12, d * 0.95));
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0.98, side: THREE.DoubleSide });
  const plane = new THREE.Mesh(geo, mat);
  plane.rotation.x = -Math.PI / 2;
  plane.position.y = h / 2 + 0.012;
  plane.renderOrder = 2;
  group.add(plane);
}

// Emoji map for catalog display
export const FURNITURE_EMOJIS = {
  bed: '🛏️',
  single_bed: '🛏️',
  nightstand: '🪑',
  wardrobe: '🚪',
  dresser: '🗄️',
  sofa: '🛋️',
  armchair: '🪑',
  coffee_table: '☕',
  tv_stand: '📺',
  dining_table: '🍽️',
  chair: '🪑',
  desk: '💻',
  office_chair: '🪑',
  bookshelf: '📚',
  lamp: '💡',
  plant: '🪴',
  rug: '🟫',
};

/**
 * Create a Three.js Group representing a furniture item.
 * @param {object} obj  {id, type, x, z, w, d, rotation, color, height}
 * @returns {THREE.Group}
 */
export function createFurnitureMesh(obj) {
  const group = new THREE.Group();
  group.name = obj.id;

  const w = obj.w * SCALE;
  const d = obj.d * SCALE;
  const h = obj.height * SCALE;
  const color = new THREE.Color(obj.color);

  const placeholder = new THREE.Group();
  switch (obj.type) {
    case 'bed':
    case 'single_bed':
      _buildBed(placeholder, w, d, h, color);
      break;
    case 'sofa':
      _buildSofa(placeholder, w, d, h, color);
      break;
    case 'wardrobe':
      _buildWardrobe(placeholder, w, d, h, color);
      break;
    case 'bookshelf':
      _buildBookshelf(placeholder, w, d, h, color);
      break;
    case 'desk':
      _buildDesk(placeholder, w, d, h, color);
      break;
    case 'lamp':
      _buildLamp(placeholder, w, d, h, color);
      break;
    case 'plant':
      _buildPlant(placeholder, w, d, h, color);
      break;
    default:
      _buildBox(placeholder, w, d, h, color);
  }

  // If this object came from IKEA (or has an image), stamp its product photo onto the mesh.
  _applyProductTexture(placeholder, obj, w, d, h);
  group.add(placeholder);

  if (obj.model_url) {
    const loader = new GLTFLoader();
    const modelUrl = (() => {
      const u = String(obj.model_url || '').trim();
      if (!u) return u;
      if (u.startsWith('/')) return u;
      if (u.startsWith('http://') || u.startsWith('https://')) return `/model?u=${encodeURIComponent(u)}`;
      return u;
    })();
    loader.load(
      modelUrl,
      (gltf) => {
        const model = gltf.scene;

        // Ensure shadows
        model.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
          }
        });

        // Compute original bounding box
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());

        if (size.x > 0 && size.y > 0 && size.z > 0) {
          // Scale to target dimensions
          model.scale.set(w / size.x, h / size.y, d / size.z);
          
          // Recompute bounding box after scale
          const newBox = new THREE.Box3().setFromObject(model);
          const newSize = newBox.getSize(new THREE.Vector3());
          const newCenter = newBox.getCenter(new THREE.Vector3());

          // Shift model so its exact center aligns with local (0,0,0)
          // because our placeholders extend from -w/2 to w/2, and -h/2 to h/2 locally.
          model.position.x -= newCenter.x;
          model.position.y -= newCenter.y;
          model.position.z -= newCenter.z;
        }

        // Swap
        group.remove(placeholder);
        group.add(model);
      },
      undefined,
      (error) => {
        console.warn(`[GLTF] Failed to load 3D model for ${obj.id}:`, error);
        // On failure, the placeholder simply remains.
      }
    );
  }

  // Position: center of object in X/Z, bottom at Y=0
  group.position.set(
    obj.x * SCALE + w / 2,
    h / 2,
    obj.z * SCALE + d / 2,
  );
  group.rotation.y = -(obj.rotation || 0) * Math.PI / 180;

  return group;
}

// ─────────────────────── BUILDERS ───────────────────────────────────────────

function _box(w, h, d, color, roughness = 0.8, metalness = 0.05) {
  const geo = new THREE.BoxGeometry(w, h, d);
  const mat = new THREE.MeshStandardMaterial({ color, roughness, metalness });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function _buildBox(group, w, d, h, color) {
  const body = _box(w, h, d, color);
  group.add(body);
  // Thin top accent
  const top = _box(w * 0.95, 0.02, d * 0.95, color.clone().multiplyScalar(1.3));
  top.position.y = h / 2 + 0.01;
  group.add(top);
}

function _buildBed(group, w, d, h, color) {
  // Mattress
  const mattressH = h * 0.5;
  const mattress = _box(w, mattressH, d * 0.8, new THREE.Color(0xdcd0c0));
  mattress.position.y = mattressH / 2 - h / 2 + h * 0.3;
  group.add(mattress);

  // Bed frame
  const frame = _box(w, h * 0.35, d, color);
  frame.position.y = 0;
  group.add(frame);

  // Headboard
  const hb = _box(w, h * 0.9, 0.05, color.clone().multiplyScalar(0.85));
  hb.position.set(0, h * 0.2, -(d / 2 - 0.025));
  group.add(hb);

  // Pillow
  const pillow = _box(w * 0.38, mattressH * 0.4, d * 0.15, new THREE.Color(0xfafafa), 0.95);
  pillow.position.set(-w * 0.2, mattressH * 0.5, -(d * 0.28));
  group.add(pillow);
  const pillow2 = pillow.clone();
  pillow2.position.x = w * 0.2;
  group.add(pillow2);
}

function _buildSofa(group, w, d, h, color) {
  const legH = h * 0.15;
  const seatH = h * 0.4;
  const backH = h * 0.6;
  const dark = color.clone().multiplyScalar(0.75);

  // Seat
  const seat = _box(w, seatH, d * 0.65, color);
  seat.position.y = legH + seatH / 2 - h / 2;
  group.add(seat);

  // Backrest
  const back = _box(w, backH, d * 0.25, dark);
  back.position.set(0, legH + backH / 2 - h / 2, d * 0.37);
  group.add(back);

  // Armrests
  for (const sx of [-1, 1]) {
    const arm = _box(d * 0.15, h * 0.55, d, dark);
    arm.position.set(sx * (w / 2 - d * 0.075), leg => leg, 0);
    arm.position.y = legH + h * 0.25 - h / 2;
    group.add(arm);
  }

  // Cushions
  const cushionColors = [0x5f9ea0, 0x708090, 0x6b8e8e];
  for (let i = 0; i < 3; i++) {
    const cushion = _box(w * 0.28, seatH * 0.5, d * 0.18, new THREE.Color(cushionColors[i % 3]));
    cushion.position.set(-w * 0.3 + i * w * 0.3, legH + seatH + seatH * 0.2 - h / 2, d * 0.05);
    group.add(cushion);
  }
}

function _buildWardrobe(group, w, d, h, color) {
  const body = _box(w, h, d, color);
  group.add(body);

  // Door lines
  const lineGeo = new THREE.BoxGeometry(0.01, h * 0.85, 0.01);
  const lineMat = new THREE.MeshStandardMaterial({ color: 0x000000, roughness: 1 });
  const line = new THREE.Mesh(lineGeo, lineMat);
  line.position.set(0, 0, d / 2 + 0.01);
  group.add(line);

  // Handles
  for (const sx of [-0.12, 0.12]) {
    const handle = _box(0.03, 0.1, 0.04, new THREE.Color(0x888888), 0.3, 0.8);
    handle.position.set(sx, 0, d / 2 + 0.025);
    group.add(handle);
  }

  // Top trim
  const trim = _box(w + 0.04, 0.05, d + 0.04, color.clone().multiplyScalar(1.2));
  trim.position.y = h / 2 + 0.025;
  group.add(trim);
}

function _buildBookshelf(group, w, d, h, color) {
  // Frame
  const frame = _box(w, h, d, color);
  group.add(frame);

  // Shelves with books
  const shelfCount = Math.max(2, Math.floor(h * 3));
  for (let i = 1; i < shelfCount; i++) {
    const y = -h / 2 + (i / shelfCount) * h;
    const shelf = _box(w * 0.9, 0.03, d * 0.85, color.clone().multiplyScalar(1.2));
    shelf.position.y = y;
    group.add(shelf);

    // Books on shelf
    const bookW = w * 0.07;
    const bookColors = [0xe74c3c, 0x3498db, 0x2ecc71, 0xe67e22, 0x9b59b6, 0x1abc9c];
    let bx = -w * 0.4;
    for (let b = 0; b < 5; b++) {
      const bh = 0.1 + Math.random() * 0.08;
      const book = _box(bookW, bh, d * 0.7, new THREE.Color(bookColors[b % bookColors.length]));
      book.position.set(bx, y + bh / 2 + 0.015, 0);
      group.add(book);
      bx += bookW + 0.01;
    }
  }
}

function _buildDesk(group, w, d, h, color) {
  // Tabletop
  const top = _box(w, 0.04, d, color);
  top.position.y = h / 2 - 0.02;
  group.add(top);

  // Legs
  const legH = h - 0.04;
  for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const leg = _box(0.05, legH, 0.05, color.clone().multiplyScalar(0.8));
    leg.position.set(sx * (w * 0.45), -0.02, sz * (d * 0.4));
    group.add(leg);
  }

  // Monitor (tiny)
  const monitor = _box(w * 0.4, h * 0.5, 0.03, new THREE.Color(0x1a1a2e));
  monitor.position.set(-w * 0.1, h * 0.5, -d * 0.3);
  group.add(monitor);
}

function _buildLamp(group, w, d, h, color) {
  // Pole
  const pole = _box(0.04, h * 0.85, 0.04, new THREE.Color(0x888888), 0.3, 0.8);
  pole.position.y = -h * 0.08;
  group.add(pole);

  // Shade
  const shade = new THREE.ConeGeometry(w * 0.8, h * 0.3, 8);
  const shadeMat = new THREE.MeshStandardMaterial({ color, roughness: 0.7, transparent: true, opacity: 0.9 });
  const shadeMesh = new THREE.Mesh(shade, shadeMat);
  shadeMesh.position.y = h * 0.35;
  shadeMesh.castShadow = true;
  group.add(shadeMesh);

  // Glow point light
  const light = new THREE.PointLight(0xfff5c0, 0.8, 3.5);
  light.position.y = h * 0.25;
  group.add(light);
}

function _buildPlant(group, w, d, h, color) {
  // Pot
  const pot = _box(w * 0.7, h * 0.25, d * 0.7, new THREE.Color(0xb5651d));
  pot.position.y = -h * 0.37;
  group.add(pot);

  // Foliage (sphere)
  const fGeo = new THREE.SphereGeometry(w * 0.65, 8, 8);
  const fMat = new THREE.MeshStandardMaterial({ color, roughness: 0.9 });
  const foliage = new THREE.Mesh(fGeo, fMat);
  foliage.castShadow = true;
  foliage.position.y = h * 0.2;
  group.add(foliage);

  // Stem
  const stem = _box(0.03, h * 0.4, 0.03, new THREE.Color(0x3a7d44));
  stem.position.y = -h * 0.1;
  group.add(stem);
}
