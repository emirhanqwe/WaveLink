import asyncio , os , threading
import io , json
from typing import Any, Optional
import requests , spotipy
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from PIL import Image
from spotipy.oauth2 import SpotifyOAuth
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

with open("config.json", "r") as f:
    config = json.load(f)

SPOTIFY_CLIENT_ID = config.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = config.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = config.get("SPOTIFY_REDIRECT_URI")

spotify_client = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-currently-playing user-read-playback-state",
        cache_path=".spotify_cache",
    )
)

DEFAULT_COLOR = "#6366f1"
LAST_SPOTIFY_LOOKUP = {"song_id": None, "data": None}


async def get_windows_media_info() -> Optional[dict[str, Any]]:
    try:
        managers = await MediaManager.request_async()
        session = managers.get_current_session()
        if session is None:
            return None

        media_info = await session.try_get_media_properties_async()
        playback_info = session.get_playback_info()
        timeline = session.get_timeline_properties()

        position_ms = timeline.position.total_seconds() * 1000 if timeline else 0

        return {
            "title": media_info.title if media_info else "unknown",
            "artist": media_info.artist if media_info else "unknown",
            "is_playing": playback_info.playback_status == 4 if playback_info else False,
            "position_ms": position_ms,
        }
    except Exception as exc:
        print(f"Windows media error: {exc}")
        return None


def get_dominant_color(image_url: Optional[str]) -> str:
    if not image_url:
        return DEFAULT_COLOR

    try:
        response = requests.get(image_url, timeout=5)
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content)).convert("RGB").resize((1, 1))
        pixel = image.getpixel((0, 0))
        red, green, blue = pixel
        return f"#{red:02x}{green:02x}{blue:02x}"
    except Exception as exc:
        print(f"Album color error: {exc}")
        return DEFAULT_COLOR


def get_spotify_data(title: str, artist: str) -> dict[str, Any]:
    global LAST_SPOTIFY_LOOKUP

    song_id = f"{title}-{artist}"
    if song_id == LAST_SPOTIFY_LOOKUP["song_id"]:
        return LAST_SPOTIFY_LOOKUP["data"]

    fallback_data = {
        "title": title,
        "artist": artist,
        "cover_url": None,
        "duration_ms": 0,
        "color": DEFAULT_COLOR,
    }

    try:
        query = f"track:{title} artist:{artist}"
        results = spotify_client.search(q=query, type="track", limit=1)

        if not results["tracks"]["items"]:
            results = spotify_client.search(q=title, type="track", limit=1)

        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            cover_url = track["album"]["images"][0]["url"] if track["album"]["images"] else None
            dominant_color = get_dominant_color(cover_url) if cover_url else DEFAULT_COLOR

            data = {
                "title": track["name"],
                "artist": track["artists"][0]["name"],
                "cover_url": cover_url,
                "duration_ms": track["duration_ms"],
                "color": dominant_color,
            }
            LAST_SPOTIFY_LOOKUP = {"song_id": song_id, "data": data}
            return data
    except Exception as exc:
        print(f"Spotify query error: {exc}")

    LAST_SPOTIFY_LOOKUP = {"song_id": song_id, "data": fallback_data}
    return fallback_data


def build_emit_payload(media_info: dict[str, Any], spotify_data: Optional[dict[str, Any]]) -> dict[str, Any]:
    if spotify_data:
        return {
            "title": spotify_data["title"],
            "artist": spotify_data["artist"],
            "is_playing": media_info["is_playing"],
            "cover_url": spotify_data.get("cover_url"),
            "position_ms": media_info["position_ms"],
            "duration_ms": spotify_data.get("duration_ms", 0),
            "color": spotify_data.get("color", DEFAULT_COLOR),
        }

    return {
        "title": media_info["title"],
        "artist": media_info["artist"],
        "is_playing": media_info["is_playing"],
        "cover_url": None,
        "position_ms": media_info["position_ms"],
        "duration_ms": 0,
        "color": DEFAULT_COLOR,
    }

def background_emitter() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    previous_title = None
    previous_artist = None
    cached_spotify_result = None

    while True:
        try:
            media_info = loop.run_until_complete(get_windows_media_info())
            if not media_info:
                socketio.sleep(1)
                continue

            current_title = media_info["title"]
            current_artist = media_info["artist"]

            if current_title == previous_title and current_artist == previous_artist:
                spotify_data = cached_spotify_result
            else:
                spotify_data = get_spotify_data(current_title, current_artist)
                previous_title = current_title
                previous_artist = current_artist
                cached_spotify_result = spotify_data

            payload = build_emit_payload(media_info, spotify_data)
            socketio.emit("update_media", payload)
        except Exception as exc:
            print(f"Emitter error: {exc}")

        socketio.sleep(1)

async def execute_control(action: str, position_ms: Optional[float] = None) -> bool:
    managers = await MediaManager.request_async()
    session = managers.get_current_session()

    if session is None:
        return False

    if action == "play_pause":
        await session.try_toggle_play_pause_async()
    elif action == "next":
        await session.try_skip_next_async()
    elif action == "prev":
        await session.try_skip_previous_async()
    elif action == "seek" and position_ms is not None:
        position_ticks = int(position_ms * 10000)
        await session.try_change_playback_position_async(position_ticks)

    return True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/control/<action>", methods=["POST"])
def control_media(action):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        if action == "seek":
            data = request.get_json(silent=True) or {}
            position_ms = float(data.get("position_ms", 0))
            loop.run_until_complete(execute_control("seek", position_ms))
        else:
            loop.run_until_complete(execute_control(action))

        return jsonify({"status": "success"})
    except Exception as exc:
        print(f"control error: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        loop.close()

if __name__ == "__main__":
    emitter_thread = threading.Thread(target=background_emitter, daemon=True, name="WaveLinkEmitter")
    emitter_thread.start()

    print(f"Wavelink is running on http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)