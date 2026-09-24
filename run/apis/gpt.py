"""
GPT API module
"""
import os
import time
import random
from openai import OpenAI

def call_gpt_api(messages, video_url, max_retries, base_delay):
    """Call GPT API"""
    api_key = os.environ.get("OPENAI_API_KEY", os.environ.get("API_KEY", ""))
    if not api_key:
        raise ValueError("Set OPENAI_API_KEY (or API_KEY) before using the GPT user model.")
    client = OpenAI(
        api_key=api_key,
        base_url=os.environ.get(
            "OPENAI_API_BASE_URL",
            os.environ.get("LLM_API_BASE_URL", "https://api.openai.com/v1"),
        ),
    )
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_USER_MODEL", "gpt-5.5"),
                messages=messages,
                stream=False
            )
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage') and response.usage:
                input_tokens = getattr(response.usage, 'prompt_tokens', 0) or 0
                output_tokens = getattr(response.usage, 'completion_tokens', 0) or 0

            # Safety check: handle content being None
            content = response.choices[0].message.content
            if content is None:
                print(f"[LLM Warning] Service(GPT) returned None content, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    print(f"Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return "Error: GPT API returned empty content", input_tokens, output_tokens

            return content, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(GPT) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(GPT) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0

if __name__ == "__main__":
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who are you?"}
    ]

    result, input_tokens, output_tokens = call_gpt_api(
        messages=test_messages,
        video_url=None,
        max_retries=3,
        base_delay=1
    )

    print("result:", result)
    print("input_tokens:", input_tokens)
    print("output_tokens:", output_tokens)
