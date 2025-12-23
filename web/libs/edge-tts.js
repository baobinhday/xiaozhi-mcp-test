/**
 * Edge TTS Integration (via Python backend)
 * Calls the server-side Edge TTS API endpoints
 */

/**
 * Fetch available voices from Edge TTS via backend
 * @returns {Promise<Array>} List of voices
 */
export async function listVoicesApi() {
  try {
    const response = await fetch('/api/edge-tts/voices');
    if (!response.ok) {
      throw new Error(`Failed to fetch voices: ${response.status}`);
    }
    const data = await response.json();
    return data.voices || [];
  } catch (error) {
    console.error('Failed to fetch Edge TTS voices:', error);
    // Return default voices as fallback
    return [
      { id: 'en-US-AriaNeural', name: 'en-US-AriaNeural', description: 'Microsoft Aria (Female)' },
      { id: 'en-US-GuyNeural', name: 'en-US-GuyNeural', description: 'Microsoft Guy (Male)' },
      { id: 'vi-VN-HoaiMyNeural', name: 'vi-VN-HoaiMyNeural', description: 'Microsoft HoaiMy (Female)' },
      { id: 'vi-VN-NamMinhNeural', name: 'vi-VN-NamMinhNeural', description: 'Microsoft NamMinh (Male)' }
    ];
  }
}

/**
 * Generate audio from text using Edge TTS via backend
 * @param {string} text The text to speak
 * @param {string} voiceId The voice ID to use (ShortName)
 * @returns {Promise<Blob>} Audio blob
 */
export async function generateEdgeAudio(text, voiceId) {
  const response = await fetch('/api/edge-tts/synthesize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: text,
      voice: voiceId || 'en-US-AriaNeural'
    })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Edge TTS API error: ${response.status}`);
  }

  return await response.blob();
}