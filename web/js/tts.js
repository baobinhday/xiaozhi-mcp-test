/**
 * Text-to-Speech Module
 * Custom TTS API integration for audio playback
 */

// ============================================
// Configuration
// ============================================
const TTS_API_URL = 'https://ttsapi.site/v1/audio/speech';

// ============================================
// State
// ============================================
let currentAudio = null;
let currentSpeakingButton = null;
let selectedVoice = 'alloy';

// Available voices from the API (loaded dynamically)
let availableVoices = [];

// ============================================
// Voice Fetching
// ============================================
const TTS_VOICES_API_URL = 'https://ttsapi.site/api/voices';

async function fetchVoices() {
  try {
    const response = await fetch(TTS_VOICES_API_URL);
    if (!response.ok) {
      throw new Error(`Failed to fetch voices: ${response.status}`);
    }
    const data = await response.json();
    availableVoices = data.voices || [];
    log('info', `Loaded ${availableVoices.length} TTS voices`);

    // Update voice dropdown if it exists
    const voiceSelect = document.getElementById('voiceSelect');
    if (voiceSelect) {
      voiceSelect.innerHTML = getVoiceOptionsHtml();
    }

    return availableVoices;
  } catch (error) {
    log('error', `Failed to fetch TTS voices: ${error.message}`);
    // Fallback to default voice
    availableVoices = [{ id: 'alloy', name: 'Alloy', description: 'Default voice' }];
    return availableVoices;
  }
}

// ============================================
// Voice Selection
// ============================================
function setTtsVoice(voiceId) {
  selectedVoice = voiceId;
  log('info', `TTS voice set to: ${voiceId}`);
}

function getVoiceOptionsHtml() {
  if (availableVoices.length === 0) {
    return '<option value="alloy">Loading voices...</option>';
  }
  return availableVoices.map(voice => {
    const isSelected = voice.id === selectedVoice;
    return `<option value="${voice.id}" ${isSelected ? 'selected' : ''}>${voice.name}</option>`;
  }).join('');
}

// ============================================
// Speech Playback
// ============================================
async function speakText(text, button) {
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
    const response = await fetch(TTS_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini-tts',
        input: text,
        voice: selectedVoice,
        response_format: 'mp3', // "mp3", "wav", "opus", "aac", "flac", "pcm"
        speed: 1.0
      })
    });

    if (!response.ok) {
      throw new Error(`TTS API error: ${response.status}`);
    }

    // Get audio blob and create URL
    const audioBlob = await response.blob();
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
function setSpeakButtonLoading(button) {
  button.innerHTML = `
    <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
      <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
    </svg>
  `;
  button.classList.add('loading');
  button.title = 'Loading...';
}

function setSpeakButtonPlaying(button) {
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

function resetSpeakButton(button) {
  button.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z"/>
    </svg>
  `;
  button.classList.remove('speaking', 'loading');
  button.title = 'Speak message';
}
