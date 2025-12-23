import { log } from './ui-utils.js';
import { fetchTtsApiVoices, generateTtsApiAudio } from './ttsapi-tts.js';
import { listVoicesApi as fetchEdgeTtsVoices, generateEdgeAudio } from '../libs/edge-tts.js';

// ============================================
// State
// ============================================
let currentAudio = null;
let currentSpeakingButton = null;
let selectedVoice = 'alloy';

// TTS Provider: 'ttsapi' or 'edge-tts'
let ttsProvider = 'ttsapi';

// Available voices from the API (loaded dynamically)
let availableVoices = [];
let edgeTtsVoices = [];

// ============================================
// TTS Provider Management
// ============================================

export function getTtsProvider() {
  return ttsProvider;
}

export function setTtsProvider(provider) {
  if (provider === 'ttsapi' || provider === 'edge-tts') {
    ttsProvider = provider;
    log('info', `TTS provider set to: ${provider}`);

    // Update voice dropdown with the correct voices
    const voiceSelect = document.getElementById('voiceSelect');
    if (voiceSelect) {
      voiceSelect.innerHTML = getVoiceOptionsHtml();
    }

    // Update all voice selects in chat
    document.querySelectorAll('.tts-voice-select').forEach(select => {
      select.innerHTML = getVoiceOptionsHtml();
    });
  }
}

// ============================================
// Voice Fetching
// ============================================

export async function fetchVoices() {
  try {
    // Fetch voices from both providers
    const [ttsApiVoicesResult, edgeTtsVoicesResult] = await Promise.allSettled([
      fetchTtsApiVoices(),
      fetchEdgeTtsVoices()
    ]);

    if (ttsApiVoicesResult.status === 'fulfilled') {
      availableVoices = ttsApiVoicesResult.value;
      log('info', `Loaded ${availableVoices.length} TTS API voices`);
    } else {
      log('warning', `Failed to fetch TTS API voices: ${ttsApiVoicesResult.reason}`);
      availableVoices = [{ id: 'alloy', name: 'Alloy', description: 'Default voice' }];
    }

    if (edgeTtsVoicesResult.status === 'fulfilled') {
      edgeTtsVoices = edgeTtsVoicesResult.value;
      log('info', `Loaded ${edgeTtsVoices.length} Edge TTS voices`);
    } else {
      log('warning', `Failed to fetch Edge TTS voices: ${edgeTtsVoicesResult.reason}`);
      edgeTtsVoices = [{ id: 'en-US-AriaNeural', name: 'en-US-AriaNeural', description: 'Default Edge voice' }];
    }

    // Update voice dropdown if it exists
    const voiceSelect = document.getElementById('voiceSelect');
    if (voiceSelect) {
      voiceSelect.innerHTML = getVoiceOptionsHtml();
    }

    return ttsProvider === 'edge-tts' ? edgeTtsVoices : availableVoices;
  } catch (error) {
    log('error', `Failed to fetch TTS voices: ${error.message}`);
    availableVoices = [{ id: 'alloy', name: 'Alloy', description: 'Default voice' }];
    edgeTtsVoices = [{ id: 'en-US-AriaNeural', name: 'en-US-AriaNeural', description: 'Default Edge voice' }];
    return availableVoices;
  }
}

// ============================================
// Voice Selection
// ============================================
export function setTtsVoice(voiceId) {
  selectedVoice = voiceId;
  log('info', `TTS voice set to: ${voiceId}`);
}

export function getVoiceOptionsHtml() {
  const voices = ttsProvider === 'edge-tts' ? edgeTtsVoices : availableVoices;

  if (voices.length === 0) {
    return '<option value="alloy">Loading voices...</option>';
  }
  return voices.map(voice => {
    const isSelected = voice.id === selectedVoice;
    return `<option value="${voice.id}" ${isSelected ? 'selected' : ''}>${voice.name}</option>`;
  }).join('');
}

export function getTtsProviderOptionsHtml() {
  return `
    <option value="ttsapi" ${ttsProvider === 'ttsapi' ? 'selected' : ''}>TTS API</option>
    <option value="edge-tts" ${ttsProvider === 'edge-tts' ? 'selected' : ''}>Edge TTS</option>
  `;
}

// ============================================
// Speech Playback
// ============================================
export async function speakText(text, button) {
  // If already playing, stop it
  if (currentAudio && currentSpeakingButton === button) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    resetSpeakButton(button);
    currentAudio = null;
    currentSpeakingButton = null;
    return;
  }

  // Stop any ongoing audio
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    if (currentSpeakingButton) {
      resetSpeakButton(currentSpeakingButton);
    }
  }

  // Update button to loading state
  setSpeakButtonLoading(button);
  currentSpeakingButton = button;

  try {
    let audioBlob;

    if (ttsProvider === 'edge-tts') {
      audioBlob = await generateEdgeAudio(text, selectedVoice);
    } else {
      audioBlob = await generateTtsApiAudio(text, selectedVoice);
    }

    // Get audio blob and create URL
    const audioUrl = URL.createObjectURL(audioBlob);

    // Create and play audio
    const audio = new Audio(audioUrl);
    currentAudio = audio;

    audio.onplay = () => {
      setSpeakButtonPlaying(button);
    };

    audio.onended = () => {
      resetSpeakButton(button);
      currentAudio = null;
      currentSpeakingButton = null;
      URL.revokeObjectURL(audioUrl);
    };

    audio.onerror = () => {
      resetSpeakButton(button);
      currentAudio = null;
      currentSpeakingButton = null;
      URL.revokeObjectURL(audioUrl);
      log('error', 'Audio playback error');
    };

    await audio.play();

  } catch (error) {
    resetSpeakButton(button);
    currentAudio = null;
    currentSpeakingButton = null;
    log('error', `TTS error: ${error.message}`);
  }
}

// ============================================
// Button State Management
// ============================================
export function setSpeakButtonLoading(button) {
  button.innerHTML = `
    <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
      <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
    </svg>
  `;
  button.classList.add('loading');
  button.title = 'Loading...';
}

export function setSpeakButtonPlaying(button) {
  button.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="5" width="4" height="14" rx="1"/>
      <rect x="14" y="5" width="4" height="14" rx="1"/>
    </svg>
  `;
  button.classList.remove('loading');
  button.classList.add('speaking');
  button.title = 'Stop speaking';
}

export function resetSpeakButton(button) {
  button.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z"/>
    </svg>
  `;
  button.classList.remove('speaking', 'loading');
  button.title = 'Speak message';
}
