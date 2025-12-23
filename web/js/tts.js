import { log } from './ui-utils.js';
import { fetchTtsApiVoices, generateTtsApiAudio } from './ttsapi-tts.js';
import { listVoicesApi as fetchEdgeTtsVoices, generateEdgeAudio } from '../libs/edge-tts.js';

// ============================================
// State
// ============================================
let currentAudio = null;
let currentSpeakingButton = null;
let selectedVoice = 'vi-VN-HoaiMyNeural';

// TTS Provider: 'ttsapi' or 'edge-tts'
let ttsProvider = 'edge-tts';

// Available voices from the API (loaded dynamically)
let availableVoices = [];
let edgeTtsVoices = [];

// Audio queue state for sentence-based playback
let audioQueue = [];
let isPlayingQueue = false;
let stopRequested = false;

// Configuration: minimum text length to trigger sentence splitting
const MIN_TEXT_LENGTH_FOR_SPLITTING = 200; // characters

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
  <option value="edge-tts" ${ttsProvider === 'edge-tts' ? 'selected' : ''}>Edge TTS</option>
    <option value="ttsapi" ${ttsProvider === 'ttsapi' ? 'selected' : ''}>TTS API</option>
  `;
}

// ============================================
// Sentence Splitting
// ============================================

/**
 * Split text into sentences for faster TTS playback
 * @param {string} text - The text to split
 * @returns {string[]} - Array of sentences
 */
function splitIntoSentences(text) {
  if (!text || text.length < MIN_TEXT_LENGTH_FOR_SPLITTING) {
    return [text];
  }

  // Split on sentence-ending punctuation and newlines
  // This regex matches sentences ending with . ! ? or double newlines
  const sentences = text.match(/[^.!?\n]+[.!?]+[\s]*/g) || [];

  // If regex didn't work well, return original text
  if (sentences.length === 0) {
    return [text];
  }

  // Filter out empty sentences and trim whitespace
  return sentences
    .map(s => s.trim())
    .filter(s => s.length > 0);
}

/**
 * Generate audio using the current TTS provider
 * @param {string} text - Text to synthesize
 * @returns {Promise<Blob>} - Audio blob
 */
async function generateAudio(text) {
  if (ttsProvider === 'edge-tts') {
    return await generateEdgeAudio(text, selectedVoice);
  } else {
    return await generateTtsApiAudio(text, selectedVoice);
  }
}

// ============================================
// Speech Playback
// ============================================

export async function speakText(text, button) {
  // If already playing, stop it
  if ((currentAudio || isPlayingQueue) && currentSpeakingButton === button) {
    stopPlayback();
    resetSpeakButton(button);
    return;
  }

  // Stop any ongoing audio
  stopPlayback();
  if (currentSpeakingButton) {
    resetSpeakButton(currentSpeakingButton);
  }

  // Update button to loading state
  setSpeakButtonLoading(button);
  currentSpeakingButton = button;
  stopRequested = false;

  try {
    const sentences = splitIntoSentences(text);

    if (sentences.length === 1) {
      // Short text - play directly without queue
      await playSingleAudio(sentences[0], button);
    } else {
      // Long text - use queue-based playback
      log('info', `Splitting into ${sentences.length} sentences for faster playback`);
      await playWithQueue(sentences, button);
    }

  } catch (error) {
    resetSpeakButton(button);
    currentAudio = null;
    currentSpeakingButton = null;
    log('error', `TTS error: ${error.message}`);
  }
}

/**
 * Play a single audio clip (for short text)
 */
async function playSingleAudio(text, button) {
  const audioBlob = await generateAudio(text);
  const audioUrl = URL.createObjectURL(audioBlob);
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
}

/**
 * Play sentences with queue - prioritize first sentence
 * 1. Synthesize first sentence immediately
 * 2. Start playing first sentence
 * 3. While playing, synthesize remaining sentences in batches
 */
async function playWithQueue(sentences, button) {
  const MAX_CONCURRENT_REQUESTS = 3; // Limit concurrent API calls

  isPlayingQueue = true;
  audioQueue = [];

  // Track which sentences are ready
  const readyAudios = new Map();
  let currentPlayIndex = 0;
  let isPlaying = false;
  let playbackPromise = null;

  /**
   * Try to play the next sentence in order (non-blocking)
   */
  const tryPlayNext = () => {
    if (isPlaying || stopRequested) return;

    if (readyAudios.has(currentPlayIndex)) {
      isPlaying = true;
      const blob = readyAudios.get(currentPlayIndex);
      readyAudios.delete(currentPlayIndex);
      const indexToPlay = currentPlayIndex;
      currentPlayIndex++;

      playbackPromise = playAudioBlob(blob, button, indexToPlay, sentences.length)
        .then(() => {
          isPlaying = false;
          // Continue playing next if available
          tryPlayNext();
        })
        .catch(() => {
          isPlaying = false;
          tryPlayNext();
        });
    }
  };

  /**
   * Synthesize a single sentence
   */
  const synthesizeSentence = async (sentence, index) => {
    try {
      const blob = await generateAudio(sentence);
      if (!stopRequested) {
        readyAudios.set(index, blob);
        // Try to play immediately (non-blocking)
        tryPlayNext();
      }
      return { index, success: true };
    } catch (error) {
      log('error', `Failed to synthesize sentence ${index + 1}: ${error.message}`);
      return { index, success: false };
    }
  };

  // STEP 1: Prioritize first sentence - synthesize and play immediately
  if (sentences.length > 0 && !stopRequested) {
    log('info', `Synthesizing first sentence...`);
    await synthesizeSentence(sentences[0], 0);
  }

  // STEP 2: Process remaining sentences in batches with limited concurrency
  if (sentences.length > 1 && !stopRequested) {
    let sentenceIndex = 1; // Start from second sentence
    const inProgress = new Set();

    while (sentenceIndex < sentences.length && !stopRequested) {
      // Fill up to MAX_CONCURRENT_REQUESTS
      while (inProgress.size < MAX_CONCURRENT_REQUESTS && sentenceIndex < sentences.length && !stopRequested) {
        const index = sentenceIndex;
        const sentence = sentences[index];
        sentenceIndex++;

        const promise = synthesizeSentence(sentence, index).then(result => {
          inProgress.delete(promise);
          return result;
        });
        inProgress.add(promise);
      }

      // Wait for at least one to complete before adding more
      if (inProgress.size > 0) {
        await Promise.race(inProgress);
      }
    }

    // Wait for all remaining synthesis to complete
    if (inProgress.size > 0) {
      await Promise.all(inProgress);
    }
  }

  // Wait for all audio to finish playing
  while ((currentPlayIndex < sentences.length || isPlaying) && !stopRequested) {
    tryPlayNext();
    await new Promise(resolve => setTimeout(resolve, 50));
  }

  // Wait for final playback to complete
  if (playbackPromise) {
    await playbackPromise;
  }

  // Cleanup
  isPlayingQueue = false;
  if (!stopRequested) {
    resetSpeakButton(button);
    currentSpeakingButton = null;
  }
}

/**
 * Play a single audio blob and wait for it to finish
 */
function playAudioBlob(blob, button, index, total) {
  return new Promise((resolve) => {
    if (stopRequested) {
      resolve();
      return;
    }

    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    currentAudio = audio;

    audio.onplay = () => {
      setSpeakButtonPlaying(button);
      button.title = `Playing ${index + 1}/${total}...`;
    };

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
      resolve();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
      log('error', `Audio playback error on sentence ${index + 1}`);
      resolve();
    };

    audio.play().catch(() => {
      URL.revokeObjectURL(audioUrl);
      resolve();
    });
  });
}

/**
 * Stop all playback
 */
function stopPlayback() {
  stopRequested = true;

  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }

  audioQueue = [];
  isPlayingQueue = false;
  currentSpeakingButton = null;
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
