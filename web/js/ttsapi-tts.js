/**
 * TTS API Integration
 * Integration with https://ttsapi.site
 */
import { log } from './ui-utils.js';

const TTS_API_URL = 'https://ttsapi.site/v1/audio/speech';
const TTS_VOICES_API_URL = 'https://ttsapi.site/api/voices';

/**
 * Fetch available voices from TTS API
 * @returns {Promise<Array>} List of voices
 */
export async function fetchTtsApiVoices() {
  try {
    const response = await fetch(TTS_VOICES_API_URL);
    if (!response.ok) {
      throw new Error(`Failed to fetch voices: ${response.status}`);
    }
    const data = await response.json();
    return data.voices || [];
  } catch (error) {
    log('error', `Failed to fetch TTS API voices: ${error.message}`);
    return [{ id: 'alloy', name: 'Alloy', description: 'Default voice (fallback)' }];
  }
}

/**
 * Generate audio from text using TTS API
 * @param {string} text The text to speak
 * @param {string} voiceId The voice ID to use
 * @returns {Promise<Blob>} Audio blob
 */
export async function generateTtsApiAudio(text, voiceId) {
  const response = await fetch(TTS_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini-tts',
      input: text,
      voice: voiceId,
      response_format: 'mp3',
      speed: 1.0
    })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `TTS API error: ${response.status}`);
  }

  return await response.blob();
}
