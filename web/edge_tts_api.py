"""
Edge TTS API handlers for MCP Web Tester.
"""

import asyncio
import io
import logging

try:
    import edge_tts
except ImportError:
    import subprocess
    import sys
    print("Installing edge-tts...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts"])
    import edge_tts

logger = logging.getLogger('MCP_HUB')


async def get_edge_tts_voices():
    """Get list of Edge TTS voices filtered for en-US and vi-VN."""
    voices = await edge_tts.list_voices()
    # Filter for en-US and vi-VN voices
    filtered_voices = [
        {
            "id": v["ShortName"],
            "name": v["ShortName"],
            "description": v.get("FriendlyName", v["ShortName"])
        }
        for v in voices
        if "en-US" in v.get("Locale", "") or "vi-VN" in v.get("Locale", "")
    ]
    return filtered_voices


async def synthesize_speech(text: str, voice: str = "en-US-AriaNeural") -> bytes:
    """Synthesize speech from text using Edge TTS."""
    communicate = edge_tts.Communicate(text, voice)
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    return audio_data.getvalue()


def handle_voices_request(handler):
    """Handle GET /api/edge-tts/voices request."""
    try:
        voices = asyncio.run(get_edge_tts_voices())
        handler.send_json_response({"voices": voices})
    except Exception as e:
        logger.error(f"Failed to fetch Edge TTS voices: {e}")
        handler.send_json_response({"error": str(e)}, 500)


def handle_synthesize_request(handler, body: dict):
    """Handle POST /api/edge-tts/synthesize request."""
    try:
        text = body.get("text", "")
        voice = body.get("voice", "en-US-AriaNeural")
        
        if not text:
            handler.send_json_response({"error": "Text is required"}, 400)
            return
        
        audio_bytes = asyncio.run(synthesize_speech(text, voice))
        
        handler.send_response(200)
        handler.send_header("Content-Type", "audio/mpeg")
        handler.send_header("Content-Length", str(len(audio_bytes)))
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(audio_bytes)
        
    except Exception as e:
        logger.error(f"Edge TTS synthesis failed: {e}")
        handler.send_json_response({"error": str(e)}, 500)
