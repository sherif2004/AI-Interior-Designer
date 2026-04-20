/**
 * AR Preview module using WebXR API.
 * Enables immersive AR session to walk around the designed room at 1:1 scale.
 */

let _scene = null;
let _renderer = null;
let _arSession = null;
let _arBtn = null;

/**
 * Initialize the AR module.
 * @param {THREE.Scene} scene - The existing Three.js scene
 * @param {THREE.WebGLRenderer} renderer - The existing renderer
 */
export function initAR(scene, renderer) {
  _scene = scene;
  _renderer = renderer;
  _arBtn = document.getElementById('btn-ar');

  if (!_arBtn) return;

  checkARSupport();
}

async function checkARSupport() {
  if (!_arBtn) return;

  const supported = !!(navigator.xr && await navigator.xr.isSessionSupported('immersive-ar').catch(() => false));

  if (supported) {
    _arBtn.style.display = 'flex';
    _arBtn.addEventListener('click', startAR);
    _arBtn.title = 'View your room in Augmented Reality';
  } else {
    _arBtn.style.display = 'none';
    // Show info tooltip on desktop
    const hint = document.getElementById('ar-hint');
    if (hint) hint.style.display = 'inline';
  }
}

export async function startAR() {
  if (!navigator.xr) {
    showARModal('Not Supported', 'Your browser does not support WebXR. Try Chrome on Android or Safari on iOS 16+.');
    return;
  }

  try {
    const supported = await navigator.xr.isSessionSupported('immersive-ar');
    if (!supported) {
      showARModal('AR Not Available', 'Augmented Reality is not supported on this device or browser.\n\nTry:\n• Chrome on Android 8+\n• Safari on iOS 16+ (experimental)\n• A WebXR-compatible headset');
      return;
    }

    // Request immersive AR session
    _arSession = await navigator.xr.requestSession('immersive-ar', {
      requiredFeatures: ['hit-test', 'local-floor'],
      optionalFeatures: ['dom-overlay'],
      domOverlay: { root: document.getElementById('ar-overlay') },
    });

    // Update renderer for AR
    _renderer.xr.enabled = true;
    _renderer.xr.setSession(_arSession);

    // Show AR overlay UI
    const overlay = document.getElementById('ar-overlay');
    if (overlay) overlay.style.display = 'flex';

    _arSession.addEventListener('end', () => {
      _arSession = null;
      if (overlay) overlay.style.display = 'none';
      _renderer.xr.enabled = false;
    });

    // AR render loop
    _renderer.setAnimationLoop((_time, frame) => {
      if (frame) {
        // Standard AR rendering — scene is already loaded
        _renderer.render(_scene, _getARCamera());
      }
    });

  } catch (e) {
    showARModal('AR Error', `Failed to start AR: ${e.message}`);
  }
}

function _getARCamera() {
  // The XR camera is managed by the renderer automatically
  return null; // WebXR renderer handles this
}

export function exitAR() {
  if (_arSession) {
    _arSession.end();
  }
}

function showARModal(title, message) {
  // Remove existing modal
  const existing = document.getElementById('ar-error-modal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = 'ar-error-modal';
  modal.className = 'ar-modal-overlay';
  modal.innerHTML = `
    <div class="ar-modal">
      <div class="ar-modal-icon">📱</div>
      <h3 class="ar-modal-title">${title}</h3>
      <p class="ar-modal-body">${message.replace(/\n/g, '<br/>')}</p>
      <button class="btn btn-accent" onclick="document.getElementById('ar-error-modal').remove()">Got it</button>
    </div>
  `;
  document.body.appendChild(modal);
}

/**
 * Check if AR is likely supported (for UI purposes).
 * @returns {Promise<boolean>}
 */
export async function isARSupported() {
  if (!navigator.xr) return false;
  try {
    return await navigator.xr.isSessionSupported('immersive-ar');
  } catch {
    return false;
  }
}
