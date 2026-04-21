/**
 * voice_input.js — Phase 5.3 (v1)
 * Browser Web Speech API → text commands.
 */

export function initVoiceInput({
  toggleButton,
  statusEl,
  transcriptEl,
  onText,
} = {}) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (statusEl) statusEl.textContent = 'Unavailable';
    if (toggleButton) {
      toggleButton.disabled = true;
      toggleButton.textContent = 'Voice Unsupported';
    }
    return { supported: false };
  }

  const rec = new SpeechRecognition();
  rec.lang = navigator.language || 'en-US';
  rec.interimResults = true;
  rec.continuous = true;

  let listening = false;
  let lastFinal = '';

  function setStatus(s) {
    if (statusEl) statusEl.textContent = s;
    if (toggleButton) toggleButton.textContent = listening ? 'Stop Listening' : 'Start Listening';
  }

  rec.onstart = () => { listening = true; setStatus('Listening'); };
  rec.onend = () => { listening = false; setStatus('Idle'); };
  rec.onerror = (e) => { listening = false; setStatus(`Error: ${e.error || 'unknown'}`); };

  rec.onresult = (event) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      const text = (res?.[0]?.transcript || '').trim();
      if (!text) continue;
      if (res.isFinal) lastFinal = text;
      else interim += (interim ? ' ' : '') + text;
    }

    if (transcriptEl) {
      transcriptEl.textContent = interim ? `… ${interim}` : (lastFinal ? `✓ ${lastFinal}` : '');
    }
    if (lastFinal && typeof onText === 'function') {
      const t = lastFinal;
      lastFinal = '';
      onText(t);
    }
  };

  async function start() {
    try { rec.start(); } catch {}
  }
  async function stop() {
    try { rec.stop(); } catch {}
  }

  if (toggleButton) {
    toggleButton.addEventListener('click', () => {
      if (listening) stop();
      else start();
    });
  }

  setStatus('Idle');
  return { supported: true, start, stop };
}

