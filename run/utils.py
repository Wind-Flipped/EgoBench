import os
import sys
import json
import base64
import re
import time
import random
import mimetypes
from urllib.parse import urlparse
import requests

# Key: Add project root to Python module search path
current_file_path = os.path.abspath(__file__)
run_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(run_dir)
sys.path.insert(0, os.path.abspath(project_root))

from run.prompts import (
    USER_CONTRADICTION_CHECK_PROMPT,
    USER_RESPONSE_CORRECTION_PROMPT,
    USER_TEXT_ONLY_PROMPT_EASY,
    USER_TEXT_ONLY_PROMPT_HARD,
)
from run.apis import call_llm


# --- Media processing utility functions ---

def is_url(path):
    """Check if path is a URL"""
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_media_type_from_url(url):
    """Get media type from URL"""
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type and mime_type.startswith('video'):
        return 'video'
    elif mime_type and mime_type.startswith('image'):
        return 'image'
    else:
        parsed_url = urlparse(url)
        ext = os.path.splitext(parsed_url.path)[1].lower()
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
        if ext in video_exts:
            return 'video'
        return 'image'


def get_media_mime_type_from_url(url):
    """Get specific MIME type from URL"""
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type:
        return mime_type

    parsed_url = urlparse(url)
    ext = os.path.splitext(parsed_url.path)[1].lower()
    mime_map = {
        '.mp4': 'video/mp4',
        '.avi': 'video/avi',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return mime_map.get(ext, 'image/jpeg')


def encode_image(image_path):
    """Encode image file"""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def encode_video(video_path):
    """Encode video file"""
    if not video_path or not os.path.exists(video_path):
        return None
    with open(video_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def download_media_from_url(url):
    """Download media content from URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Failed to download media: {e}")
        return None


def get_media_type(file_path):
    """Determine media type based on file extension"""
    if is_url(file_path):
        return get_media_type_from_url(file_path)
    else:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('video'):
            return 'video'
        elif mime_type and mime_type.startswith('image'):
            return 'image'
        else:
            ext = os.path.splitext(file_path)[1].lower()
            video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
            if ext in video_exts:
                return 'video'
            return 'image'


def get_media_mime_type(file_path):
    """Get specific MIME type"""
    if is_url(file_path):
        return get_media_mime_type_from_url(file_path)
    else:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type

        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            '.mp4': 'video/mp4',
            '.avi': 'video/avi',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_map.get(ext, 'image/jpeg')


def build_message_with_media(text, media_path=None, use_vision=False, service_model_name="qwen3-vl-225b"):
    """Determine whether to include media files and message format based on use_vision parameter and service_model_name"""
    content = [{"type": "text", "text": text}]

    if use_vision and media_path:
        media_type = "video"
        mime_type = get_media_mime_type(media_path)

        # Build different message formats for different models
        if service_model_name in ["glm-5v-turbo", "qwen3.6-plus", "mimo-v2-omni", "kimi-k2.5"]:
            if media_type == 'video':
                content.append({"type": "video_url", "video_url": {"url": media_path}})
            else:
                content.append({"type": "image_url", "image_url": {"url": media_path}})

        elif service_model_name == "gemini-3.1-pro-preview":
            # Gemini format
            if is_url(media_path):
                if media_type == 'video':
                    content.append({
                        "type": "input_audio",
                        "input_audio": {"data": media_path, "format": "video/mp4"}
                    })
                else:
                    content.append({"type": "image_url", "image_url": {"url": media_path}})
            else:
                if media_type == 'video':
                    base64_media = encode_video(media_path)
                    if base64_media:
                        content.append({
                            "type": "input_audio",
                            "input_audio": {"data": base64_media, "format": mime_type}
                        })
                else:
                    base64_media = encode_image(media_path)
                    if base64_media:
                        content.append({"type": "image_url", "image_url": {"url": f"{mime_type};base64,{base64_media}"}})
        else:
            # Default format
            if media_type == 'video':
                content.append({"type": "video_url", "video_url": {"url": media_path}})
            else:
                content.append({"type": "image_url", "image_url": {"url": media_path}})

    return content


def build_message_with_image(text, image_path=None, use_vision=False, service_model_name="qwen3-vl-225b"):
    """Backward compatible function, recommend using build_message_with_media"""
    return build_message_with_media(text, image_path, use_vision, service_model_name)


# --- Tool execution functions ---

def execute_tool(db_instance, tool_calls_data):
    """Parse and execute one or more tool calls, return structured results containing role, tool_name, parameters, content"""
    if isinstance(tool_calls_data, dict):
        tool_calls_data = [tool_calls_data]
    elif not isinstance(tool_calls_data, list):
        return [{"role": "tool", "tool_name": "unknown", "parameters": {}, "content": json.dumps({"error": "Invalid tool call format. Expected dict or list."}, ensure_ascii=False)}]

    results = []
    for tool_call_obj in tool_calls_data:
        try:
            method_name = tool_call_obj.get("tool_name") or tool_call_obj.get("name")
            if not method_name:
                results.append({
                    "role": "tool",
                    "tool_name": "unknown",
                    "parameters": {},
                    "content": json.dumps({"error": "Missing tool identifier ('tool_name' or 'name')"}, ensure_ascii=False)
                })
                continue

            params = tool_call_obj.get("parameters", tool_call_obj.get("arguments", {}))

            print(f"  [Tool Execution] Calling: {method_name} Parameters: {params}")

            if hasattr(db_instance, method_name):
                method = getattr(db_instance, method_name)
                result = method(**params)
                print(f"  [Tool Execution] Return result: {result}")
                results.append({
                    "role": "tool",
                    "tool_name": method_name,
                    "parameters": params,
                    "content": json.dumps(result, ensure_ascii=False, default=str)
                })
            else:
                results.append({
                    "role": "tool",
                    "tool_name": method_name,
                    "parameters": params,
                    "content": json.dumps({"error": f"Tool '{method_name}' not found"}, ensure_ascii=False)
                })
        except Exception as e:
            results.append({
                "role": "tool",
                "tool_name": tool_call_obj.get("tool_name") or tool_call_obj.get("name") or "unknown",
                "parameters": tool_call_obj.get("parameters", tool_call_obj.get("arguments", {})),
                "content": json.dumps({"error": str(e)}, ensure_ascii=False)
            })

    return results


# --- Tool call check functions ---

def check_tool_call(response_text):
    """
    Extract all JSON format strings containing tool calls from text
    Recognition rules: JSON object/array contains tool_call, tool_name or name keywords
    Returns: (whether tool call was found, extracted tool call JSON list)
    """
    text = response_text.strip()

    # Unified recognition condition, add support for "name"
    def is_tool_call(obj):
        return isinstance(obj, dict) and ("tool_call" in obj or "tool_name" in obj or "name" in obj)

    # Try parsing entire text as JSON first
    try:
        data = json.loads(text)
        if isinstance(data, list) and len(data) > 0:
            tool_calls = [item for item in data if is_tool_call(item)]
            if tool_calls:
                return True, tool_calls
        elif is_tool_call(data):
            return True, [data]
    except json.JSONDecodeError:
        pass

    # Regex to extract all possible JSON object fragments
    json_pattern = r'\{([^{}]|(\{[^{}]*\}))*\}'
    potential_jsons = re.findall(json_pattern, text, re.DOTALL)

    valid_tool_calls = []
    for match in potential_jsons:
        json_str = match[0] if isinstance(match, tuple) else match
        if not json_str.startswith('{'):
            json_str = '{' + json_str
        if not json_str.endswith('}'):
            json_str = json_str + '}'

        try:
            obj = json.loads(json_str)
            if is_tool_call(obj):
                valid_tool_calls.append(obj)
        except (json.JSONDecodeError, ValueError):
            continue

    # Additional handling for JSON array scenario
    if not valid_tool_calls:
        array_pattern = r'\[.*\]'
        array_matches = re.findall(array_pattern, text, re.DOTALL)

        for arr_str in array_matches:
            try:
                arr = json.loads(arr_str)
                if isinstance(arr, list):
                    for item in arr:
                        if is_tool_call(item):
                            valid_tool_calls.append(item)
            except (json.JSONDecodeError, ValueError):
                continue

    if valid_tool_calls:
        return True, valid_tool_calls
    return False, None

# --- User response evaluation functions ---

def _evaluate_user_response_internal(user_response, user_instruction, last_agent_response, history_str=""):
    """Internal helper function: build prompt and call LLM to evaluate user response"""
    eval_user_content = f"""
[User Original Instruction]
{user_instruction}

[Interaction Process]
{history_str}

[Service Agent Response]
{last_agent_response}

[Simulated User Response]
{user_response}
"""

    contradiction_check_messages = [
        {"role": "system", "content": USER_CONTRADICTION_CHECK_PROMPT},
        {"role": "user", "content": eval_user_content}
    ]

    eval_response_text, _, _ = call_llm(contradiction_check_messages, agent_type="user")

    evaluation_result = {}
    try:
        import re
        code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", eval_response_text, re.DOTALL)
        if code_block_match:
            evaluation_result = json.loads(code_block_match.group(1))
        else:
            try:
                evaluation_result = json.loads(eval_response_text)
            except:
                start = eval_response_text.find('{')
                end = eval_response_text.rfind('}')
                if start != -1 and end != -1:
                    json_str = eval_response_text[start:end+1]
                    evaluation_result = json.loads(json_str)
                else:
                    return {"error": "No JSON found", "raw": eval_response_text}
    except Exception as e:
        return {"error": str(e), "raw": eval_response_text}

    return evaluation_result


def check_user_contradiction(user_response, user_instruction, image_description="", multi_agent_user=False, last_agent_response="", history=[], summarized_history=None, user_mode="easy"):
    """
    Check if user response contradicts the task (based on scoring mechanism)
    If multi_agent_user is True and there is a contradiction (any dimension <= 2 points), use LLM to correct user response
    :param user_mode: User difficulty mode ("easy" or "hard"), used to select corresponding correction prompt
    :return: (corrected_response, evaluation_result)
    """
    if not multi_agent_user:
        return user_response, None

    # Build history conversation string
    if summarized_history:
        history_str = summarized_history
    else:
        history_str = ""
        for item in history:
            role = "User" if item["role"] == "user" else "Service Agent"
            content = item["content"]
            history_str += f"{role}: {content}\n"

    # 1. Evaluate original user response
    print("Evaluating user response (Corrections Check)...")
    evaluation_result = _evaluate_user_response_internal(user_response, user_instruction, last_agent_response, history_str)

    if "error" in evaluation_result:
        print(f"Evaluation failed: {evaluation_result['error']}")
        return user_response, evaluation_result

    scores = evaluation_result.get("scores", {})

    try:
        score_values = [float(v) for v in scores.values()]
        avg_score = round(sum(score_values) / len(score_values), 2) if score_values else 0
    except:
        avg_score = 0
    evaluation_result["average_score"] = avg_score

    # Check if correction is needed
    needs_correction = False
    for k, v in scores.items():
        try:
            if float(v) <= 0:
                needs_correction = True
                break
        except:
            pass

    corrected_response = user_response
    evaluation_result["original_response"] = user_response

    if needs_correction:
        print(f"Low score detected (average: {avg_score}), starting to correct user response... (Scores: {scores})")

        # Select corresponding prompt based on user_mode
        if user_mode == "hard":
            correction_prompt_template = USER_TEXT_ONLY_PROMPT_HARD
        else:
            correction_prompt_template = USER_TEXT_ONLY_PROMPT_EASY

        correction_input = correction_prompt_template.format(
            user_instruction=user_instruction,
            image_description=image_description,
            original_user_response=user_response,
            evaluation_feedback=evaluation_result.get("suggestion", ""),
            history_summary=history_str,
            service_agent_response=last_agent_response
        )

        correction_messages = [{"role": "user", "content": correction_input}]
        corrected_response_text, _, _ = call_llm(correction_messages, agent_type="user")

        cleaned_response = corrected_response_text.strip()
        if cleaned_response.startswith("```"):
            lines = cleaned_response.split('\n')
            if len(lines) >= 2:
                cleaned_response = '\n'.join(lines[1:-1])

        corrected_response = cleaned_response.strip()
        print(f"User response corrected: {corrected_response}")

        evaluation_result["correction_applied"] = True
        evaluation_result["corrected_response"] = corrected_response

        print("Evaluating corrected response...")
        corrected_evaluation = _evaluate_user_response_internal(corrected_response, user_instruction, last_agent_response, history_str)

        if "error" not in corrected_evaluation:
            corrected_scores = corrected_evaluation.get("scores", {})
            evaluation_result["corrected_scores"] = corrected_scores

            try:
                c_values = [float(v) for v in corrected_scores.values()]
                c_avg_score = round(sum(c_values) / len(c_values), 2) if c_values else 0
            except:
                c_avg_score = 0
            evaluation_result["corrected_average_score"] = c_avg_score

            print(f"Corrected scores: {corrected_scores} (average: {c_avg_score})")
        else:
            evaluation_result["corrected_evaluation_error"] = corrected_evaluation.get("error")

    else:
        evaluation_result["correction_applied"] = False
        print(f"Scores passed (average: {avg_score})")

    return corrected_response, evaluation_result