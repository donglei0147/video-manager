from app.api.errors import api_error
from app.db.models import Video


def ensure_has_audio(video: Video) -> None:
    if not video.has_audio:
        raise api_error(400, "NO_AUDIO_TRACK", "该视频无音频轨，无法截取或合并")
