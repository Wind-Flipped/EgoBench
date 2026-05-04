"""
Qwen API module
"""
import os
from openai import OpenAI

class Qwen3_5_API:
    """Qwen API client class"""

    def __init__(self, api_key=None):
        """
        Initialize Qwen client

        Args:
            api_key: Qwen API key (falls back to API_KEY env var)
        """
        self.api_key = api_key or os.environ.get("API_KEY", "")
        if not self.api_key:
            raise ValueError("Qwen API key not provided. Set API_KEY environment variable or pass api_key argument.")
        os.environ["DASHSCOPE_API_KEY"] = self.api_key
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=os.environ.get("LLM_API_BASE_URL", "https://api.example.com/v1")
        )
        self.default_model = "qwen3.5-397b-a17b"

    def chat_with_video(self, video_url, text, model=None, enable_thinking=False):
        """
        Chat with video

        Args:
            video_url: Video URL
            text: User question text
            model: Model name, default is qwen3.6-plus
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
            "messages": messages,
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
            "messages": messages,
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
