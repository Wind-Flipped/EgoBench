"""
Kimi API module
"""
import os
import base64
from openai import OpenAI

class KimiAPI:
    """Kimi API client class"""

    def __init__(self, api_key=None):
        """
        Initialize Kimi client

        Args:
            api_key: Kimi API key (falls back to KIMI_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get("KIMI_API_KEY", "")
        if not self.api_key:
            raise ValueError("Kimi API key not provided. Set KIMI_API_KEY environment variable or pass api_key argument.")
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=os.environ.get("KIMI_API_BASE_URL", "https://api.moonshot.cn/v1")
        )
        self.default_model = "kimi-k2.5"
        self.default_system_prompt = "You are Kimi."
        # Kimi's thinking mode is implemented by selecting different models: kimi-k2-thinking is the thinking model

    def encode_video_to_base64(self, video_path):
        """
        Encode video file to base64 format

        Args:
            video_path: Video file path

        Returns:
            Base64 encoded video URL
        """
        with open(video_path, "rb") as f:
            video_data = f.read()

        # We use standard library base64.b64encode to encode video to base64 format video_url
        video_url = f"data:video/{os.path.splitext(video_path)[1]};base64,{base64.b64encode(video_data).decode('utf-8')}"
        return video_url

    def chat_with_video_file(self, video_path, text, model=None, system_prompt=None, enable_thinking=False):
        """
        Chat with local video file

        Args:
            video_path: Local video file path
            text: User question text
            model: Model name, default is kimi-k2.5
            system_prompt: System prompt
            enable_thinking: Whether to enable thinking mode, uses kimi-k2-thinking model when enabled

        Returns:
            Text content returned by the model
        """
        if model is None:
            # Kimi's thinking mode is implemented by switching models
            model = "kimi-k2-thinking" if enable_thinking else self.default_model
        if system_prompt is None:
            system_prompt = self.default_system_prompt

        # Encode video to base64
        video_url = self.encode_video_to_base64(video_path)

        messages = [
            {"role": "system", "content": system_prompt},
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

        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )

        return completion.choices[0].message.content

    def chat_with_video_url(self, video_url, text, model=None, system_prompt=None, enable_thinking=False):
        """
        Chat with video URL

        Args:
            video_url: Video URL
            text: User question text
            model: Model name, default is kimi-k2.5
            system_prompt: System prompt
            enable_thinking: Whether to enable thinking mode, uses kimi-k2-thinking model when enabled

        Returns:
            Text content returned by the model
        """
        if model is None:
            # Kimi's thinking mode is implemented by switching models
            model = "kimi-k2-thinking" if enable_thinking else self.default_model
        if system_prompt is None:
            system_prompt = self.default_system_prompt

        messages = [
            {"role": "system", "content": system_prompt},
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

        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )

        return completion.choices[0].message.content

    def chat(self, messages, model=None, enable_thinking=False):
        """
        General chat interface

        Args:
            messages: Chat message list
            model: Model name
            enable_thinking: Whether to enable thinking mode, uses kimi-k2-thinking model when enabled

        Returns:
            (response_text, input_tokens, output_tokens)
        """
        if model is None:
            # Kimi's thinking mode is implemented by switching models
            model = "kimi-k2-thinking" if enable_thinking else self.default_model

        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        content = completion.choices[0].message.content

        # Extract token information
        input_tokens = 0
        output_tokens = 0
        if hasattr(completion, 'usage') and completion.usage:
            input_tokens = getattr(completion.usage, 'prompt_tokens', 0) or 0
            output_tokens = getattr(completion.usage, 'completion_tokens', 0) or 0

        return content, input_tokens, output_tokens
