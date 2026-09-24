"""
Kimi API module
"""
import base64
import copy
import mimetypes
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from urllib.parse import unquote, urlparse

import requests
from openai import OpenAI
# os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-bundle.crt"
# os.environ["SSL_CERT_DIR"]="/etc/ssl/certs"
# os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-bundle.crt"

_DEFAULT_MAX_VIDEO_BYTES = 64 * 1024 * 1024
_DEFAULT_MAX_BASE64_VIDEO_BYTES = 6 * 1024 * 1024
_DEFAULT_VIDEO_DOWNLOAD_TIMEOUT = 120
_VIDEO_DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def _compress_video(payload, mime_type, target_bytes):
    """Transcode a video to H.264/AAC and keep it below target_bytes."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            "video must be compressed for Base64 transport, but ffmpeg/ffprobe "
            "is not installed"
        )

    input_suffix = mimetypes.guess_extension(mime_type) or ".mp4"
    with tempfile.TemporaryDirectory(prefix="kimi-video-") as temp_dir:
        input_path = os.path.join(temp_dir, f"input{input_suffix}")
        output_path = os.path.join(temp_dir, "output.mp4")
        with open(input_path, "wb") as input_file:
            input_file.write(payload)

        probe = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        duration = float(probe.stdout.strip())
        if duration <= 0:
            raise ValueError("could not determine a positive video duration")

        # Leave room for the MP4 container and variable-rate encoder overhead.
        total_bitrate = max(96_000, int(target_bytes * 8 * 0.82 / duration))
        audio_bitrate = min(48_000, max(24_000, total_bitrate // 4))
        video_bitrate = max(72_000, total_bitrate - audio_bitrate)

        for attempt in range(2):
            command = [
                ffmpeg,
                "-y",
                "-v", "error",
                "-i", input_path,
                "-vf",
                "scale=w='min(960,iw)':h=-2:force_original_aspect_ratio=decrease,fps=10",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-b:v", str(video_bitrate),
                "-maxrate", str(video_bitrate),
                "-bufsize", str(video_bitrate * 2),
                "-c:a", "aac",
                "-b:a", str(audio_bitrate),
                "-movflags", "+faststart",
                output_path,
            ]
            try:
                subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    timeout=max(180, int(duration * 4)),
                )
            except subprocess.CalledProcessError as error:
                detail = error.stderr.decode("utf-8", errors="replace")[-1000:]
                raise RuntimeError(f"ffmpeg failed to compress video: {detail}") from error

            output_size = os.path.getsize(output_path)
            if output_size <= target_bytes:
                with open(output_path, "rb") as output_file:
                    return output_file.read()

            # Tighten the bitrate once using the measured first-pass size.
            ratio = target_bytes / output_size * 0.85
            video_bitrate = max(72_000, int(video_bitrate * ratio))

        raise ValueError(
            f"compressed video is still too large: {output_size} bytes; "
            f"target is {target_bytes} bytes"
        )


@lru_cache(maxsize=2)
def _video_to_data_url(
    video_source,
    max_video_bytes,
    max_base64_video_bytes,
    download_timeout,
):
    """Download/read a video and return a cached Base64 data URL."""
    if not isinstance(video_source, str) or not video_source:
        raise ValueError("video source must be a non-empty string")

    if video_source.startswith("data:video/"):
        return video_source
    if video_source.startswith("data:"):
        raise ValueError("only video data URLs are supported")

    if video_source.startswith(("http://", "https://")):
        with requests.get(
            video_source,
            stream=True,
            allow_redirects=True,
            timeout=(10, download_timeout),
        ) as response:
            response.raise_for_status()
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_video_bytes:
                raise ValueError(
                    f"video is too large: {content_length} bytes; "
                    f"limit is {max_video_bytes} bytes"
                )

            payload = bytearray()
            for chunk in response.iter_content(_VIDEO_DOWNLOAD_CHUNK_SIZE):
                if not chunk:
                    continue
                payload.extend(chunk)
                if len(payload) > max_video_bytes:
                    raise ValueError(
                        f"video exceeds the {max_video_bytes}-byte limit"
                    )

            mime_type = response.headers.get("Content-Type", "")
            mime_type = mime_type.split(";", 1)[0].strip().lower()
            source_for_guess = response.url
    else:
        if video_source.startswith("file://"):
            video_path = unquote(urlparse(video_source).path)
        else:
            video_path = video_source
        if not os.path.isfile(video_path):
            raise ValueError(f"unsupported or missing video source: {video_source}")
        file_size = os.path.getsize(video_path)
        if file_size > max_video_bytes:
            raise ValueError(
                f"video is too large: {file_size} bytes; "
                f"limit is {max_video_bytes} bytes"
            )
        with open(video_path, "rb") as video_file:
            payload = video_file.read()
        mime_type = ""
        source_for_guess = video_path

    if not payload:
        raise ValueError("video source returned no data")

    if not mime_type.startswith("video/"):
        mime_type = mimetypes.guess_type(source_for_guess)[0] or ""
    if not mime_type.startswith("video/"):
        raise ValueError(f"video source returned unsupported content type: {mime_type}")

    if len(payload) > max_base64_video_bytes:
        payload = _compress_video(payload, mime_type, max_base64_video_bytes)
        mime_type = "video/mp4"

    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


class KimiAPI:
    """Kimi API client class"""

    def __init__(
        self,
        api_key=None,
        max_video_bytes=None,
        max_base64_video_bytes=None,
        video_download_timeout=None,
    ):
        """
        Initialize Kimi client

        Args:
            api_key: Kimi API key
            max_video_bytes: Maximum accepted source video size
            max_base64_video_bytes: Compression target before Base64 encoding
            video_download_timeout: Video download read timeout in seconds
        """
        self.api_key = api_key or os.environ.get("KIMI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Kimi API key not provided. Set KIMI_API_KEY or pass api_key."
            )
        self.max_video_bytes = int(
            max_video_bytes
            if max_video_bytes is not None
            else os.environ.get("KIMI_MAX_VIDEO_BYTES", _DEFAULT_MAX_VIDEO_BYTES)
        )
        self.max_base64_video_bytes = int(
            max_base64_video_bytes
            if max_base64_video_bytes is not None
            else os.environ.get(
                "KIMI_MAX_BASE64_VIDEO_BYTES",
                _DEFAULT_MAX_BASE64_VIDEO_BYTES,
            )
        )
        self.video_download_timeout = float(
            video_download_timeout
            if video_download_timeout is not None
            else os.environ.get(
                "KIMI_VIDEO_DOWNLOAD_TIMEOUT",
                _DEFAULT_VIDEO_DOWNLOAD_TIMEOUT,
            )
        )
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=os.environ.get(
                "KIMI_API_BASE_URL", "https://api.moonshot.cn/v1"
            ),
        )
        self.default_model = os.environ.get("KIMI_MODEL", "kimi-k2.6")

    def _prepare_video(self, video_source):
        return _video_to_data_url(
            video_source,
            self.max_video_bytes,
            self.max_base64_video_bytes,
            self.video_download_timeout,
        )

    def _prepare_messages(self, messages):
        prepared = copy.deepcopy(messages)
        for message in prepared:
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if item.get("type") != "video_url":
                    continue
                video = item.get("video_url")
                if not isinstance(video, dict) or not video.get("url"):
                    raise ValueError("video_url content must contain a url")
                video["url"] = self._prepare_video(video["url"])
        return prepared

    def chat_with_video(self, video_url, text, model=None, enable_thinking=False):
        """
        Chat with video

        Args:
            video_url: Video URL
            text: User question text
            model: Model name, default is kimi-k2.6
            enable_thinking: Whether to enable thinking mode, default is False

        Returns:
            Text content returned by the model
        """
        if model is None:
            model = self.default_model

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {
                            "url": video_url
                        }
                    },
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]

        kwargs = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "extra_body": {"enable_thinking": enable_thinking}
        }

        completion = self.client.chat.completions.create(**kwargs)

        return completion.choices[0].message.content

    def chat(self, messages, model=None, enable_thinking=False):
        """
        General chat interface

        Args:
            messages: Chat message list
            model: Model name
            enable_thinking: Whether to enable thinking mode, default is False

        Returns:
            (response_text, input_tokens, output_tokens)
        """
        if model is None:
            model = self.default_model

        kwargs = {
            "model": model,
            "messages": self._prepare_messages(messages),
            "extra_body": {"enable_thinking": enable_thinking}
        }

        completion = self.client.chat.completions.create(**kwargs)
        content = completion.choices[0].message.content

        # Extract token information
        input_tokens = 0
        output_tokens = 0
        if hasattr(completion, 'usage') and completion.usage:
            input_tokens = getattr(completion.usage, 'prompt_tokens', 0) or 0
            output_tokens = getattr(completion.usage, 'completion_tokens', 0) or 0

        return content, input_tokens, output_tokens


if __name__ == "__main__":
    # Test code
    api = KimiAPI()
    video_path = os.path.join("video", "retail1.mp4")
    result = api.chat_with_video(video_path, "What does the video show?")
    print(result)
    # messages = [
    #     {"role": "system", "content": "You are a helpful assistant."},
    #     {"role": "user", "content": "Who are you?"}
    # ]
    # result, input_tokens, output_tokens = api.chat(
    #     messages=messages,
    #     model=None,
    #     enable_thinking=False
    # )
    # print("result:", result)
