"""
Unified API module - integrates all LLM API calls
"""
import os
import time
import random
import requests
from openai import OpenAI

# Import model APIs
from .zhipu import ZhipuAPI
from .qwen import QwenAPI
from .mimo import MimoAPI
from .kimi import KimiAPI
from .doubao import DoubaoAPI
from .qwen3_5 import Qwen3_5_API

# Video URL mapping - original URL to public Cloud URL
# To customize these URLs, set the VIDEO_URL_MAPPING environment variable with a JSON object
import json
_DEFAULT_CLOUD_URL_MAPPING = {
    # Retail
    "retail1.mp4": "https://cloud.example.edu/retail1/?dl=1",
    "retail2.mp4": "https://cloud.example.edu/retail2/?dl=1",
    "retail3.mp4": "https://cloud.example.edu/retail3/?dl=1",
    "retail4.mp4": "https://cloud.example.edu/retail4/?dl=1",
    "retail5.mp4": "https://cloud.example.edu/retail5/?dl=1",
    "retail6.mp4": "https://cloud.example.edu/retail6/?dl=1",
    "retail7.mp4": "https://cloud.example.edu/retail7/?dl=1",
    "retail8.mp4": "https://cloud.example.edu/retail8/?dl=1",
    "retail9.mp4": "https://cloud.example.edu/retail9/?dl=1",
    "retail10.mp4": "https://cloud.example.edu/retail10/?dl=1",

    # Kitchen
    "kitchen1.mp4": "https://cloud.example.edu/kitchen1/?dl=1",
    "deep_fried.mp4": "https://cloud.example.edu/deep_fried/?dl=1",
    "Green%20Pepper%20Chicken.mp4": "https://cloud.example.edu/green_pepper_chicken/?dl=1",
    "dumplings.mp4": "https://cloud.example.edu/dumplings/?dl=1",

    # Restaurant
    "restaurant1.mp4": "https://cloud.example.edu/restaurant1/?dl=1",
    "restaurant2.mp4": "https://cloud.example.edu/restaurant2/?dl=1",
    "restaurant3.mp4": "https://cloud.example.edu/restaurant3/?dl=1",
    "restaurant4.mp4": "https://cloud.example.edu/restaurant4/?dl=1",
    "restaurant5.mp4": "https://cloud.example.edu/restaurant5/?dl=1",

    # Order - annie series
    "afrikana_annie_1.mp4": "https://cloud.example.edu/afrikana_annie_1/?dl=1",
    "annie_butcher_1.mp4": "https://cloud.example.edu/annie_butcher_1/?dl=1",
    "annie_meraki_1.mp4": "https://cloud.example.edu/annie_meraki_1/?dl=1",
    "annie_pauhana_1.mp4": "https://cloud.example.edu/annie_pauhana_1/?dl=1",
    "sunny_annie_1.mp4": "https://cloud.example.edu/sunny_annie_1/?dl=1",

    # Order - greek series
    "afrikana_greek.mp4": "https://cloud.example.edu/afrikana_greek/?dl=1",
    "butcher_greek.mp4": "https://cloud.example.edu/butcher_greek/?dl=1",
    "greek_annie_1.mp4": "https://cloud.example.edu/greek_annie_1/?dl=1",
    "meraki_greek.mp4": "https://cloud.example.edu/meraki_greek/?dl=1",
    "pauhana_greek.mp4": "https://cloud.example.edu/pauhana_greek/?dl=1",
    "sunny_greek.mp4": "https://cloud.example.edu/sunny_greek/?dl=1",
}

# Load custom URL mapping from environment variable if available
_VIDEO_URL_MAPPING_ENV = os.environ.get("VIDEO_URL_MAPPING", "")
if _VIDEO_URL_MAPPING_ENV:
    try:
        _CLOUD_URL_MAPPING = json.loads(_VIDEO_URL_MAPPING_ENV)
    except json.JSONDecodeError:
        _CLOUD_URL_MAPPING = _DEFAULT_CLOUD_URL_MAPPING
else:
    _CLOUD_URL_MAPPING = _DEFAULT_CLOUD_URL_MAPPING

# Gemini video URL mapping
# To customize these URLs, set the GEMINI_URL_MAPPING environment variable with a JSON object
_DEFAULT_GEMINI_URL_MAPPING = {
    # Retail
    "retail1.mp4": "gs://example_cloud_storage/benchmark_videos/retail1.mp4",
    "retail2.mp4": "gs://example_cloud_storage/benchmark_videos/retail2.mp4",
    "retail3.mp4": "gs://example_cloud_storage/benchmark_videos/retail3.mp4",
    "retail4.mp4": "gs://example_cloud_storage/benchmark_videos/retail4.mp4",
    "retail5.mp4": "gs://example_cloud_storage/benchmark_videos/retail5.mp4",
    "retail6.mp4": "gs://example_cloud_storage/benchmark_videos/retail6.mp4",
    "retail7.mp4": "gs://example_cloud_storage/benchmark_videos/retail7.mp4",
    "retail8.mp4": "gs://example_cloud_storage/benchmark_videos/retail8.mp4",
    "retail9.mp4": "gs://example_cloud_storage/benchmark_videos/retail9.mp4",
    "retail10.mp4": "gs://example_cloud_storage/benchmark_videos/retail10.mp4",

    # Kitchen
    "kitchen1.mp4": "gs://example_cloud_storage/benchmark_videos/kitchen1.mp4",
    "deep_fried.mp4": "gs://example_cloud_storage/benchmark_videos/deep_fried.mp4",
    "Green%20Pepper%20Chicken.mp4": "gs://example_cloud_storage/benchmark_videos/Green_Pepper_Chicken.mp4",
    "dumplings.mp4": "gs://example_cloud_storage/benchmark_videos/dumplings.mp4",

    # Restaurant
    "restaurant1.mp4": "gs://example_cloud_storage/benchmark_videos/restaurant1.mp4",
    "restaurant2.mp4": "gs://example_cloud_storage/benchmark_videos/restaurant2.mp4",
    "restaurant3.mp4": "gs://example_cloud_storage/benchmark_videos/restaurant3.mp4",
    "restaurant4.mp4": "gs://example_cloud_storage/benchmark_videos/restaurant4.mp4",
    "restaurant5.mp4": "gs://example_cloud_storage/benchmark_videos/restaurant5.mp4",

    # Order - annie series
    "afrikana_annie_1.mp4": "gs://example_cloud_storage/benchmark_videos/afrikana_annie_1.mp4",
    "annie_butcher_1.mp4": "gs://example_cloud_storage/benchmark_videos/annie_butcher_1.mp4",
    "annie_meraki_1.mp4": "gs://example_cloud_storage/benchmark_videos/annie_meraki_1.mp4",
    "annie_pauhana_1.mp4": "gs://example_cloud_storage/benchmark_videos/annie_pauhana_1.mp4",
    "sunny_annie_1.mp4": "gs://example_cloud_storage/benchmark_videos/sunny_annie_1.mp4",

    # Order - greek series
    "afrikana_greek.mp4": "gs://example_cloud_storage/benchmark_videos/afrikana_greek.mp4",
    "butcher_greek.mp4": "gs://example_cloud_storage/benchmark_videos/butcher_greek.mp4",
    "greek_annie_1.mp4": "gs://example_cloud_storage/benchmark_videos/greek_annie_1.mp4",
    "meraki_greek.mp4": "gs://example_cloud_storage/benchmark_videos/meraki_greek.mp4",
    "pauhana_greek.mp4": "gs://example_cloud_storage/benchmark_videos/pauhana_greek.mp4",
    "sunny_greek.mp4": "gs://example_cloud_storage/benchmark_videos/sunny_greek.mp4",
}

# Load custom URL mapping from environment variable if available
_GEMINI_URL_MAPPING_ENV = os.environ.get("GEMINI_URL_MAPPING", "")
if _GEMINI_URL_MAPPING_ENV:
    try:
        GEMINI_URL_MAPPING = json.loads(_GEMINI_URL_MAPPING_ENV)
    except json.JSONDecodeError:
        GEMINI_URL_MAPPING = _DEFAULT_GEMINI_URL_MAPPING
else:
    GEMINI_URL_MAPPING = _DEFAULT_GEMINI_URL_MAPPING

# Kimi video URL mapping
# To customize these URLs, set the KIMI_URL_MAPPING environment variable with a JSON object
_DEFAULT_KIMI_URL_MAPPING = {
    # Retail
    "retail1.mp4": "ms://example_media_service/retail1",
    "retail2.mp4": "ms://example_media_service/retail2",
    "retail3.mp4": "ms://example_media_service/retail3",
    "retail4.mp4": "ms://example_media_service/retail4",
    "retail5.mp4": "ms://example_media_service/retail5",
    "retail6.mp4": "ms://example_media_service/retail6",
    "retail7.mp4": "ms://example_media_service/retail7",
    "retail8.mp4": "ms://example_media_service/retail8",
    "retail9.mp4": "ms://example_media_service/retail9",
    "retail10.mp4": "ms://example_media_service/retail10",

    # Kitchen
    "kitchen1.mp4": "ms://example_media_service/kitchen1",
    "deep_fried.mp4": "ms://example_media_service/deep_fried",
    "Green%20Pepper%20Chicken.mp4": "ms://example_media_service/green_pepper_chicken",
    "dumplings.mp4": "ms://example_media_service/dumplings",

    # Restaurant
    "restaurant1.mp4": "ms://example_media_service/restaurant1",
    "restaurant2.mp4": "ms://example_media_service/restaurant2",
    "restaurant3.mp4": "ms://example_media_service/restaurant3",
    "restaurant4.mp4": "ms://example_media_service/restaurant4",
    "restaurant5.mp4": "ms://example_media_service/restaurant5",

    # Order - annie series
    "afrikana_annie_1.mp4": "ms://example_media_service/afrikana_annie_1",
    "annie_butcher_1.mp4": "ms://example_media_service/annie_butcher_1",
    "annie_meraki_1.mp4": "ms://example_media_service/annie_meraki_1",
    "annie_pauhana_1.mp4": "ms://example_media_service/annie_pauhana_1",
    "sunny_annie_1.mp4": "ms://example_media_service/sunny_annie_1",

    # Order - greek series
    "afrikana_greek.mp4": "ms://example_media_service/afrikana_greek",
    "butcher_greek.mp4": "ms://example_media_service/butcher_greek",
    "greek_annie_1.mp4": "ms://example_media_service/greek_annie_1",
    "meraki_greek.mp4": "ms://example_media_service/meraki_greek",
    "pauhana_greek.mp4": "ms://example_media_service/pauhana_greek",
    "sunny_greek.mp4": "ms://example_media_service/sunny_greek",
}

# Load custom URL mapping from environment variable if available
_KIMI_URL_MAPPING_ENV = os.environ.get("KIMI_URL_MAPPING", "")
if _KIMI_URL_MAPPING_ENV:
    try:
        KIMI_URL_MAPPING = json.loads(_KIMI_URL_MAPPING_ENV)
    except json.JSONDecodeError:
        KIMI_URL_MAPPING = _DEFAULT_KIMI_URL_MAPPING
else:
    KIMI_URL_MAPPING = _DEFAULT_KIMI_URL_MAPPING

# User model config - only use Qwen3.5-397B-A17B
USER_MODEL_CONFIG = {
    "name": "Qwen3.5-397B-A17B",
    "token": os.environ.get("API_KEY", ""),
    "url": os.environ.get("LLM_API_BASE_URL", "https://api.example.com/v1/chat/completions")
}



def extract_video_url_from_messages(messages):
    """Extract video URL from messages"""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "video_url":
                    return item.get("video_url", {}).get("url")
    return None


def call_llm(messages, agent_type="service", service_model_name="qwen3-vl-225b", enable_thinking=False):
    """
    Unified LLM call interface

    Args:
        messages: Message list
        agent_type: "service" or "user"
        service_model_name: Service model name
        enable_thinking: Whether to enable thinking mode

    Returns:
        (response_text, input_tokens, output_tokens)
    """
    MAX_RETRIES = 3
    BASE_DELAY = 10

    if agent_type == "user":
        # User model only uses Qwen3.5-397B-A17B
        return _call_user_model(messages, MAX_RETRIES, BASE_DELAY, enable_thinking)
    else:
        # Service model
        return _call_service_model(messages, service_model_name, MAX_RETRIES, BASE_DELAY, enable_thinking)


def _call_user_model(messages, max_retries, base_delay, enable_thinking):
    """Call user model - only uses Qwen3.5-397B-A17B"""
    last_error = None

    for attempt in range(max_retries):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {USER_MODEL_CONFIG['token']}"
            }

            payload = {
                "model": USER_MODEL_CONFIG["name"],
                "messages": messages,
                "stream": False,
                "chat_template_kwargs": {
                    "enable_thinking": enable_thinking
                }
            }

            response = requests.post(
                USER_MODEL_CONFIG["url"],
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            return result['choices'][0]['message']['content'], input_tokens, output_tokens

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(last_error)
                print(f"[LLM Retry] User attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] User failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


def _call_service_model(messages, model_name, max_retries, base_delay, enable_thinking):
    """Call service model"""
    NEWLINE = chr(10)

    # Extract and convert video URL from messages
    video_url = extract_video_url_from_messages(messages)

    # Select API based on model type
    if model_name in ["zhipu", "glm-5v-turbo"]:
        return _call_zhipu_api(messages, video_url, NEWLINE, max_retries, base_delay, enable_thinking)
    elif model_name in ["qwen", "qwen3.6-plus"]:
        return _call_qwen_api(messages, video_url, NEWLINE, max_retries, base_delay, enable_thinking)
    elif model_name in ["mimo", "mimo-v2-omni"]:
        return _call_mimo_api(messages, video_url, NEWLINE, max_retries, base_delay, enable_thinking)
    elif model_name in ["kimi", "kimi-k2.5"]:
        return _call_kimi_api(messages, video_url, NEWLINE, max_retries, base_delay, enable_thinking)
    elif model_name in ["doubao", "doubao-seed-2-0-pro-260215"]:
        return _call_doubao_api(messages, video_url, NEWLINE, max_retries, base_delay, enable_thinking)
    elif model_name == "gemini-3.1-pro-preview":
        return _call_gemini_api(messages, video_url, max_retries, base_delay)
    elif model_name == "qwen3-vl-225b":
        return _call_qwen3_vl_api(messages, max_retries, base_delay, enable_thinking)
    elif model_name == "Qwen3.5-397B-A17B":
        return _call_qwen3_5_api(messages, video_url, NEWLINE, max_retries, base_delay, enable_thinking)
    else:
        # Other models use generic API
        return _call_generic_api(messages, model_name, max_retries, base_delay, enable_thinking)


def _call_zhipu_api(messages, video_url, newline, max_retries, base_delay, enable_thinking):
    """Call Zhipu API"""
    last_error = None
    for attempt in range(max_retries):
        try:
            api = ZhipuAPI()
            result, input_tokens, output_tokens = api.chat(messages, thinking_enabled=enable_thinking)
            return result, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(zhipu) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(zhipu) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


def _call_qwen_api(messages, video_url, newline, max_retries, base_delay, enable_thinking):
    """Call Qwen API"""
    last_error = None
    for attempt in range(max_retries):
        try:
            api = QwenAPI()
            result, input_tokens, output_tokens = api.chat(messages, enable_thinking=enable_thinking)
            return result, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(qwen) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(qwen) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0

def _call_qwen3_5_api(messages, video_url, newline, max_retries, base_delay, enable_thinking):
    """Call Qwen API"""
    last_error = None
    for attempt in range(max_retries):
        try:
            api = Qwen3_5_API()
            result, input_tokens, output_tokens = api.chat(messages, enable_thinking=enable_thinking)
            return result, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(qwen) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(qwen) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


def _call_mimo_api(messages, video_url, newline, max_retries, base_delay, enable_thinking):
    """Call Mimo API"""
    last_error = None
    for attempt in range(max_retries):
        try:
            api = MimoAPI()
            result, input_tokens, output_tokens = api.chat(messages)
            return result, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(mimo) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(mimo) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


def _call_kimi_api(messages, video_url, newline, max_retries, base_delay, enable_thinking):
    """Call Kimi API"""
    last_error = None
    for attempt in range(max_retries):
        try:
            api = KimiAPI()
            result, input_tokens, output_tokens = api.chat(messages)
            return result, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(kimi) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(kimi) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


def _call_doubao_api(messages, video_url, newline, max_retries, base_delay, enable_thinking):
    """Call Doubao API"""
    last_error = None
    for attempt in range(max_retries):
        try:
            api = DoubaoAPI()
            result, input_tokens, output_tokens = api.chat(messages, enable_thinking=enable_thinking)
            return result, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(doubao) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(doubao) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


def _call_gemini_api(messages, video_url, max_retries, base_delay):
    """Call Gemini API"""
    GEMINI_API_KEY = os.environ.get("API_KEY", "")
    if not GEMINI_API_KEY:
        raise ValueError("API_KEY environment variable not set for Gemini API.")
    client = OpenAI(
        api_key=GEMINI_API_KEY,
        base_url=os.environ.get("LLM_API_BASE_URL", "https://api.example.com/v1")
    )
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gemini-3.1-pro-preview",
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
                print(f"[LLM Warning] Service(gemini) returned None content, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    print(f"Retrying in {wait_time:.2f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return "Error: Gemini API returned empty content", input_tokens, output_tokens

            return content, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(gemini) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(gemini) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


def _call_qwen3_vl_api(messages, max_retries, base_delay, enable_thinking):
    """Call Qwen3-VL-225B API"""
    API_KEY = os.environ.get("API_KEY", "")
    if not API_KEY:
        raise ValueError("API_KEY environment variable not set for Qwen3-VL API.")
    BASE_URL = os.environ.get("LLM_API_BASE_URL", "https://api.example.com/v1")
    MODEL_NAME = "city_guide_vl_235b"

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=32768,
                temperature=0.7,
                extra_body={"enable_thinking": enable_thinking}
            )
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage') and response.usage:
                input_tokens = getattr(response.usage, 'prompt_tokens', 0) or 0
                output_tokens = getattr(response.usage, 'completion_tokens', 0) or 0
            return response.choices[0].message.content, input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service(Std) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service(Std) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0


# Model config mapping
MODEL_CONFIGS = {
    "qwen3_30b_a3b": {"name": "Qwen3-30B-A3B-Instruct-2507", "token": os.environ.get("API_KEY", "")},
    "qwen3_235b_a22b": {"name": "Qwen3-235B-A22B-Instruct-2507-Pro", "token": os.environ.get("API_KEY", "")},
    "Qwen3.5-397B-A17B": {"name": "Qwen3.5-397B-A17B", "token": os.environ.get("API_KEY", "")},
    "DeepSeek-R1": {"name": "DeepSeek-R1", "token": os.environ.get("API_KEY", "")},
    "DeepSeek-V3": {"name": "DeepSeek-V3", "token": os.environ.get("API_KEY", "")},
    "DeepSeek-V3.2": {"name": "DeepSeek-V3.2", "token": os.environ.get("API_KEY", "")},
    "qwen3-vl-225b": {"name": "Qwen3-VL-235B-A22B-Instruct", "token": os.environ.get("API_KEY", "")},
    "glm-4.5v": {"name": "GLM-4.5V", "token": os.environ.get("API_KEY", "")},
}


def _call_generic_api(messages, model_name, max_retries, base_delay, enable_thinking):
    """Call Generic API (other models)"""
    url = os.environ.get("LLM_API_BASE_URL", "https://api.example.com/v1/chat/completions")
    config = MODEL_CONFIGS.get(model_name, {})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.get('token', '')}"
    }

    if "glm-4" in model_name:
        payload = {
            "model": config.get("name", model_name),
            "messages": messages,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False}
        }
    else:
        payload = {
            "model": config.get("name", model_name),
            "messages": messages,
            "stream": False
        }

    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            return result['choices'][0]['message']['content'], input_tokens, output_tokens
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                print(f"[LLM Retry] Service({model_name}) attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"[LLM Error] Service({model_name}) failed after {max_retries} attempts: {str(e)}")
                return f"Error: {str(e)}", 0, 0