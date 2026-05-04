import os
import json
import time
import random
import argparse
import sys
import concurrent.futures

# Add the project root directory to Python's module search path
# Get the absolute path of the current file (main.py)
current_file_path = os.path.abspath(__file__)
# Get the path of the run folder
run_dir = os.path.dirname(current_file_path)
# Get the project root directory (parent directory of run)
project_root = os.path.dirname(run_dir)
# Add the root directory to sys.path so Python can find the tools folder
sys.path.insert(0, os.path.abspath(project_root))

# 1. Import initialization data
from tools.retail.retail_db import RetailDB
from tools.retail.retail_init import retail_init_data1, retail_init_data2, retail_init_data3, retail_init_data4, retail_init_data5, retail_init_data6, retail_init_data7, retail_init_data8, retail_init_data9, retail_init_data10
from tools.kitchen.kitchen_db import KitchenDB
from tools.kitchen.kitchen_init import kitchen_init_data
from tools.restaurant.restaurant_db import RestaurantDB
from tools.restaurant.restaurant_init import restaurant_init_data, restaurant_init_data5
from tools.order.order_db import OrderDB
from tools.order.order_init import order_init_data
from tools.user_words import kitchen_sentences, wine_sentences, retail_sentences, restaurant_sentences, order_sentences
from run.prompts import (
    USER_TEXT_ONLY_PROMPT_EASY,
    USER_TEXT_ONLY_PROMPT_HARD,
    STATIC_USER_PROMPT,
    STATIC_USER_END,
    SERVICE_AGENT_PROMPT_BASE,
    USER_TURN_SUMMARY_PROMPT
)
from run.utils import (
    call_llm,
    execute_tool,
    check_tool_call,
    check_user_contradiction,
    build_message_with_image
)
from run.apis.unified import GEMINI_URL_MAPPING, _CLOUD_URL_MAPPING, KIMI_URL_MAPPING


def get_video_url_for_model(video_url, model_name):
    """Return corresponding video URL based on model name"""
    if not video_url:
        return video_url

    # gemini-3.1-pro-preview uses GEMINI_URL_MAPPING
    if model_name == "gemini-3.1-pro-preview":
        return GEMINI_URL_MAPPING.get(video_url, video_url)

    # kimi-k2.5 uses KIMI_URL_MAPPING
    if model_name == "kimi-k2.5":
        return KIMI_URL_MAPPING.get(video_url, video_url)

    # glm-5v-turbo, qwen3.6-plus, mimo-v2-omni, doubao-seed-2-0-pro-260215 uses _CLOUD_URL_MAPPING
    if model_name in ["glm-5v-turbo", "qwen3.6-plus", "mimo-v2-omni", "doubao-seed-2-0-pro-260215", "Qwen3.5-397B-A17B"]:
        return _CLOUD_URL_MAPPING.get(video_url, video_url)

    # Other models use original OSS link
    return video_url


def run_static_simulation(input_path, tool_info_path, output_path, args=None, service_model_name="qwen3-vl-225b"):
    """
    Static Mode: Send user_instruction to customer service at once, no multi-round interaction
    """
    use_vision = False  # Always use text mode
    # 1. Load tool definitions
    with open(tool_info_path, 'r', encoding='utf-8') as f:
        tools_list = json.load(f)
        tool_descriptions = json.dumps(tools_list, indent=2, ensure_ascii=False)

    # 2. Load scenario inputs
    with open(input_path, 'r', encoding='utf-8') as f:
        scenarios = json.load(f)

    # New: Truncate samples based on num_samples parameter
    if args.num_samples > 0:
        scenarios = scenarios[:args.num_samples]

    all_results = []

    for idx, sc in enumerate(scenarios):
        scenario_id = idx + 1

        print(f"\n{'='*20} Scenario {args.scenario}{args.scenario_number}: {scenario_id} (Static Mode) {'='*20} ")

        if args.scenario == "retail":
            db = RetailDB()
            if args.scenario_number == 1:
                db.init_from_json(retail_init_data1)
            elif args.scenario_number == 2:
                db.init_from_json(retail_init_data2)
            elif args.scenario_number == 3:
                db.init_from_json(retail_init_data3)
            elif args.scenario_number == 4:
                db.init_from_json(retail_init_data4)
            elif args.scenario_number == 5:
                db.init_from_json(retail_init_data5)
            elif args.scenario_number == 6:
                db.init_from_json(retail_init_data6)
            elif args.scenario_number == 7:
                db.init_from_json(retail_init_data7)
            elif args.scenario_number == 8:
                db.init_from_json(retail_init_data8)
            elif args.scenario_number == 9:
                db.init_from_json(retail_init_data9)
            elif args.scenario_number == 10:
                db.init_from_json(retail_init_data10)
        elif args.scenario == "kitchen":
            db = KitchenDB()
            db.init_from_json(kitchen_init_data)
        elif args.scenario == "restaurant":
            db = RestaurantDB()
            if args.scenario_number == 5:
                db.init_from_json(restaurant_init_data5)
            else:
                # 1,2,3,4
                db.init_from_json(restaurant_init_data)
        elif args.scenario == "order":
            db = OrderDB()
            db.init_from_json(order_init_data)


        user_instruction = sc.get("Instruction", "")
        image_path = sc.get("image_path", None)
        # Convert video URL based on model
        image_path = get_video_url_for_model(image_path, args.service_model_name)

        # Generate image description only in text mode
        image_description = sc.get("image_description", "")

        # Record start time
        start_time = time.time()

        history_log = {
            "scenario_id": scenario_id,
            "mode": "text",
            "instruction": user_instruction,
            "image_description": image_description,
            "dialogue": [],
            "tool_calls": [],
            "rounds_count": 0,           # New: Dialogue round count
            "input_tokens": 0,           # New: Input token count
            "output_tokens": 0,          # New: Output token count
            "tool_calls_count": 0,      # New: Tool call count
            "user_response_time_seconds": 0.0, # New: Time used by user agent
            "agent_response_time_seconds": 0.0, # New: Time used by tested agent
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))  # New: Start time
        }

        # --- User Agent Initialization (Static Mode) ---
        user_agent_sys_prompt = STATIC_USER_PROMPT.format(user_instruction=user_instruction)

        user_messages = [
            {"role": "system", "content": user_agent_sys_prompt},
            {"role": "user", "content": "You are a customer in the environment shown in the video, and you need to complete the instructions in **Task**. I am your AI customer service representative; please interact with me in the first person. Let's begin the conversation.\nDear customer, how can I help you?"}
        ]

        # --- Tested Agent (Service Agent) Initialization ---
        service_agent_sys_prompt = SERVICE_AGENT_PROMPT_BASE.format(tool_descriptions=tool_descriptions)

        service_history = []

        # --- Static Mode: One-time interaction ---
        # User Agent generates one message
        user_start_time = time.time()
        user_reply, user_input_tokens, user_output_tokens = call_llm(user_messages, agent_type="user", service_model_name=args.service_model_name)
        history_log["user_response_time_seconds"] += time.time() - user_start_time
        print(f"User Agent: {user_reply}")

        history_log["dialogue"].append({"role": "user", "turn": 0, "content": user_reply + STATIC_USER_END})

        # Service Agent processes user message
        service_history.append({"role": "user", "content": user_reply + STATIC_USER_END})

        # Loop to process service agent's response until no tool calls are returned
        rounds_count = 0
        input_tokens_total = 0
        output_tokens_total = 0
        tool_calls_count = 0

        while True:
            current_service_msgs = [{"role": "system", "content": service_agent_sys_prompt}]

            for i, msg in enumerate(service_history):
                if i == 0 and msg["role"] == "user":
                    current_service_msgs.append({
                        "role": "user",
                        "content": build_message_with_image(msg["content"], image_path, use_vision=True, service_model_name=args.service_model_name)
                    })
                else:
                    current_service_msgs.append(msg)

            agent_start_time = time.time()
            agent_reply, agent_input_tokens, agent_output_tokens = call_llm(current_service_msgs, agent_type="service", service_model_name=args.service_model_name)
            history_log["agent_response_time_seconds"] += time.time() - agent_start_time
            input_tokens_total += agent_input_tokens
            output_tokens_total += agent_output_tokens

            print(f"Tested Agent: {agent_reply}")

            is_tool, tool_call_obj = check_tool_call(agent_reply)

            if is_tool:
                # Increment tool call count
                if isinstance(tool_call_obj, list):
                    tool_calls_count += len(tool_call_obj)
                else:
                    tool_calls_count += 1

                # Execute all found tool calls - returns list of structured results
                tool_results = execute_tool(db, tool_call_obj)

                # Record tool calls and results in one entry per turn
                # tool_results is now a list of dicts with role, tool_name, parameters, content
                history_log["tool_calls"].append({
                    "turn": rounds_count,
                    "calls": tool_call_obj if isinstance(tool_call_obj, list) else [tool_call_obj],
                    "results": tool_results
                })

                # Build combined result string for service history
                result_strings = []
                for res in tool_results:
                    result_strings.append(res.get("content", str(res)))
                combined_result = "; ".join(result_strings)

                service_history.append({"role": "assistant", "content": agent_reply})
                service_history.append({"role": "user", "content": f"Tool execution result: {combined_result}"})

                # Check if tool calls exceed limit
                if tool_calls_count > 200:
                    print(f"Tool calls count ({tool_calls_count}) exceeded 200, stopping interaction.")
                    break

                # Continue loop to check if the agent has more tool calls
                continue
            else:
                # Service agent responds with natural language, record and end
                rounds_count += 1
                history_log["dialogue"].append({"role": "agent", "turn": 0, "content": agent_reply})
                service_history.append({"role": "assistant", "content": agent_reply})
                break # End static mode interaction

        # Update statistics
        history_log["rounds_count"] = rounds_count
        history_log["input_tokens"] = input_tokens_total   # Only count service agent tokens
        history_log["output_tokens"] = output_tokens_total
        history_log["tool_calls_count"] = tool_calls_count

        # Calculate and add execution time
        end_time = time.time()
        execution_time = round(end_time - start_time, 3)
        history_log["execution_time_seconds"] = execution_time

        all_results.append(history_log)

    # 4. Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nCompleted! Results saved to: {output_path}")
    print(f"Statistics Summary: ")
    for idx, result in enumerate(all_results):
        print(f"  Task {idx+1}: {result['rounds_count']} dialogue rounds, {result['input_tokens']} input tokens, {result['output_tokens']} output tokens, {result['tool_calls_count']} tool calls, {result['execution_time_seconds']} seconds")

def run_simulation(input_path, tool_info_path, output_path, args=None, service_model_name="qwen3-vl-225b"):
    """
    Interactive Mode: Multi-round conversation
    """
    use_vision = False  # Always use text mode
    user_sentences = None
    # 1. Load tool definitions
    with open(tool_info_path, 'r', encoding='utf-8') as f:
        tools_list = json.load(f)
        tool_descriptions = json.dumps(tools_list, indent=2, ensure_ascii=False)

    # 2. Load scenario inputs
    with open(input_path, 'r', encoding='utf-8') as f:
        scenarios = json.load(f)

    # New: Truncate samples based on num_samples parameter
    if args.num_samples > 0:
        scenarios = scenarios[:args.num_samples]

    all_results = []
    new_results_list = []

    for idx, sc in enumerate(scenarios):
        scenario_id = idx + 1

        print(f"\n{'='*20} Scenario {args.scenario}{args.scenario_number}: {scenario_id} {'='*20} ")
        if args.scenario == "retail":
            if args.scenario_number <= 5:
                user_sentences = wine_sentences
            else:
                user_sentences = retail_sentences
            db = RetailDB()
            if args.scenario_number == 1:
                db.init_from_json(retail_init_data1)
            elif args.scenario_number == 2:
                db.init_from_json(retail_init_data2)
            elif args.scenario_number == 3:
                db.init_from_json(retail_init_data3)
            elif args.scenario_number == 4:
                db.init_from_json(retail_init_data4)
            elif args.scenario_number == 5:
                db.init_from_json(retail_init_data5)
            elif args.scenario_number == 6:
                db.init_from_json(retail_init_data6)
            elif args.scenario_number == 7:
                db.init_from_json(retail_init_data7)
            elif args.scenario_number == 8:
                db.init_from_json(retail_init_data8)
            elif args.scenario_number == 9:
                db.init_from_json(retail_init_data9)
            elif args.scenario_number == 10:
                db.init_from_json(retail_init_data10)
        elif args.scenario == "kitchen":
            user_sentences = kitchen_sentences
            db = KitchenDB()
            db.init_from_json(kitchen_init_data)
        elif args.scenario == "restaurant":
            user_sentences = restaurant_sentences
            db = RestaurantDB()
            if args.scenario_number == 5:
                db.init_from_json(restaurant_init_data5)
            else:
                db.init_from_json(restaurant_init_data)
        elif args.scenario == "order":
            db = OrderDB()
            db.init_from_json(order_init_data)
            user_sentences = order_sentences

        user_instruction = sc.get("Instruction", "")
        image_path = sc.get("image_path", None)
        # Convert video URL based on model
        image_path = get_video_url_for_model(image_path, args.service_model_name)
        image_description = sc.get("image_description", "")

        start_time = time.time()

        history_log = {
            "scenario_id": scenario_id,
            "mode": "text",
            "instruction": user_instruction,
            "image_description": image_description,
            "dialogue": [],
            "tool_calls": [],
            "rounds_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "tool_calls_count": 0,
            "user_response_time_seconds": 0.0,
            "agent_response_time_seconds": 0.0,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        }

        if args.user_mode == "easy":
            user_agent_sys_prompt = USER_TEXT_ONLY_PROMPT_EASY.format(
                user_instruction=user_instruction,
                image_description=image_description,
                original_user_response="",
                evaluation_feedback="",
                history_summary="",
                service_agent_response="Dear customer, how can I help you?"
            )
        elif args.user_mode == "hard":
            user_agent_sys_prompt = USER_TEXT_ONLY_PROMPT_HARD.format(
                user_instruction=user_instruction,
                image_description=image_description,
                original_user_response="",
                evaluation_feedback="",
                history_summary="",
                service_agent_response="Dear customer, how can I help you?"
            )
        else:
            user_agent_sys_prompt = USER_TEXT_ONLY_PROMPT_EASY.format(
                user_instruction=user_instruction,
                image_description=image_description,
                original_user_response="",
                evaluation_feedback="",
                history_summary="",
                service_agent_response="Dear customer, how can I help you?"
            )

        user_messages = [
            {"role": "system", "content": user_agent_sys_prompt},
            {"role": "user", "content": "You are a customer in the environment shown in the video, and you need to complete the instructions in **Task**. I am your AI customer service representative; please interact with me in the first person. Let's begin the conversation.\nDear customer, how can I help you?"}
        ]

        service_agent_sys_prompt = SERVICE_AGENT_PROMPT_BASE.format(tool_descriptions=tool_descriptions)
        service_history = []

        max_turns = 10
        rounds_count = 0
        input_tokens_total = 0
        output_tokens_total = 0
        tool_calls_count = 0

        accumulated_original_scores = {}
        accumulated_final_scores = {}
        valid_evaluation_count = 0

        last_agent_response_for_check = "Dear customer, how can I help you?"
        summarized_history_str = ""

        # Using a ThreadPoolExecutor for concurrent execution
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        for turn in range(max_turns):
            # --- 1. User Agent Speaks ---
            user_start_time = time.time()
            user_reply, user_input_tok, user_output_tok = call_llm(user_messages, agent_type="user", service_model_name=args.service_model_name)
            user_gen_time = time.time() - user_start_time
            print(f"[Time] User response generation (Turn {turn}): {user_gen_time:.3f} seconds")
            history_log["user_response_time_seconds"] += user_gen_time

            # --- 2. Check phase ---
            evaluation_info = None
            check_start_time = time.time()
            if args.multi_agent_user and args.user_mode in ["easy", "hard"]:
                original_user_reply = user_reply
                user_reply, evaluation_info = check_user_contradiction(
                    user_response=original_user_reply,
                    user_instruction=user_instruction,
                    image_description=image_description if not use_vision else "",
                    multi_agent_user=args.multi_agent_user,
                    last_agent_response=last_agent_response_for_check,
                    history=history_log["dialogue"],
                    summarized_history=summarized_history_str if getattr(args, "summary_user", False) else None,
                    user_mode=args.user_mode
                )

                if evaluation_info:
                    print(f"\n[User Response Evaluation]")
                    if "scores" in evaluation_info:
                        print(f"  Original Scores: {json.dumps(evaluation_info['scores'], ensure_ascii=False)} (Average: {evaluation_info.get('average_score', 'N/A')})")
                    if "corrected_scores" in evaluation_info:
                        print(f"  Corrected Scores: {json.dumps(evaluation_info['corrected_scores'], ensure_ascii=False)} (Average: {evaluation_info.get('corrected_average_score', 'N/A')})")
                    if "reasoning" in evaluation_info:
                        print(f"  Original Reasoning: {json.dumps(evaluation_info['reasoning'], ensure_ascii=False, indent=2)}")
                    if "corrected_reasoning" in evaluation_info:
                        print(f"  Corrected Reasoning: {json.dumps(evaluation_info['corrected_reasoning'], ensure_ascii=False, indent=2)}")

                    if "scores" in evaluation_info:
                        valid_evaluation_count += 1
                        original_scores_dict = evaluation_info["scores"]
                        final_scores_dict = evaluation_info.get("corrected_scores", original_scores_dict)

                        for k, v in original_scores_dict.items():
                            try:
                                accumulated_original_scores[k] = accumulated_original_scores.get(k, 0.0) + float(v)
                            except ValueError:
                                pass

                        for k, v in final_scores_dict.items():
                            try:
                                accumulated_final_scores[k] = accumulated_final_scores.get(k, 0.0) + float(v)
                            except ValueError:
                                pass
                if user_reply != original_user_reply:
                    print(f"User Response Corrected: {user_reply}")

            check_time = time.time() - check_start_time
            if args.multi_agent_user and args.user_mode in ["easy", "hard"]:
                print(f"[Time] Check phase (Turn {turn}): {check_time:.3f} seconds")
                history_log["user_response_time_seconds"] += check_time

            if args.user_mode == "hard":
                user_reply += "  " + user_sentences[random.randint(0, len(user_sentences) - 1)]

            print(f"Final User Response: {user_reply}")

            log_entry = {"role": "user", "turn": turn, "content": user_reply}
            if evaluation_info:
                log_entry["evaluation"] = evaluation_info

            history_log["dialogue"].append(log_entry)

            if "STOP" in user_reply:
                print("Stop signal detected")
                break

            service_history.append({"role": "user", "content": user_reply})
            user_messages.append({"role": "assistant", "content": user_reply})

            # --- 3 & 4. Concurrently Summary and Agent Next Process ---
            # snapshot variables for threads to avoid race condition
            current_user_reply_for_task = user_reply
            current_agent_response_for_task = last_agent_response_for_check
            current_service_history = [msg for msg in service_history]
            current_summarized_history = summarized_history_str

            def generate_summary_task():
                if not getattr(args, "summary_user", False):
                    return None

                sum_start_time = time.time()
                sum_prompt = USER_TURN_SUMMARY_PROMPT.format(
                    user_instruction=user_instruction,
                    agent_response=current_agent_response_for_task,
                    user_response=current_user_reply_for_task,
                    previous_summary=current_summarized_history if current_summarized_history else "None"
                )
                print(f"Generating dialogue summary (Turn {turn})...")
                sum_msgs = [{"role": "user", "content": sum_prompt}]
                turn_summary, _, _ = call_llm(sum_msgs, agent_type="user", service_model_name=args.service_model_name)
                sum_time = time.time() - sum_start_time
                print(f"[Time] Summary generation (Turn {turn}): {sum_time:.3f} seconds")
                print(f"Turn {turn} Summary: {turn_summary}")
                return turn_summary

            def process_agent_task():
                agent_start = time.time()
                inner_input_tokens = 0
                inner_output_tokens = 0
                inner_calls = 0
                inner_rounds = 0
                agent_final_reply = ""
                local_tool_logs = []
                local_dialogue_logs = []
                # local mutable service history copy for tool loops
                local_service_history = [msg for msg in current_service_history]
                # Accumulate tool call count (including previous turns)
                total_tool_calls_so_far = tool_calls_count

                while True:
                    current_service_msgs = [{"role": "system", "content": service_agent_sys_prompt}]
                    for i, msg in enumerate(local_service_history):
                        if i == 0 and msg["role"] == "user":
                            current_service_msgs.append({
                                "role": "user",
                                "content": build_message_with_image(msg["content"], image_path, use_vision=True, service_model_name=args.service_model_name)
                            })
                        else:
                            current_service_msgs.append(msg)

                    if args.service_model_name == "manual":
                        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] --- Manual Service Agent Turn ---")
                        print("Latest User Input:")
                        if service_history and service_history[-1]["role"] == "user":
                            print(service_history[-1]["content"])
                        print("Enter your response (text or JSON tool calls). Type 'END' on a new line to finish:")
                        ml_input = []
                        while True:
                            try:
                                line = input()
                                if line.strip() == "END":
                                    break
                                ml_input.append(line)
                            except EOFError:
                                break
                        agent_reply = "\n".join(ml_input)
                        agent_input_tokens = 0
                        agent_output_tokens = 0
                    else:
                        agent_reply, agent_input_tokens, agent_output_tokens = call_llm(current_service_msgs, agent_type="service", service_model_name=args.service_model_name)
                        inner_input_tokens += agent_input_tokens
                        inner_output_tokens += agent_output_tokens
                    print(f"Tested Agent: {agent_reply}")

                    is_tool, tool_call_obj = check_tool_call(agent_reply)

                    if is_tool:
                        if isinstance(tool_call_obj, list):
                            inner_calls += len(tool_call_obj)
                        else:
                            inner_calls += 1

                        # Execute all found tool calls - returns list of structured results
                        tool_results = execute_tool(db, tool_call_obj)

                        # Record tool calls and results in one entry per turn
                        local_tool_logs.append({
                            "turn": turn,
                            "calls": tool_call_obj if isinstance(tool_call_obj, list) else [tool_call_obj],
                            "results": tool_results
                        })

                        # Build combined result string for service history
                        result_strings = []
                        for res in tool_results:
                            result_strings.append(res.get("content", str(res)))
                        combined_result = "; ".join(result_strings)

                        local_service_history.append({"role": "assistant", "content": agent_reply})
                        local_service_history.append({"role": "user", "content": f"Tool execution result: {combined_result}"})

                        # Check if tool calls exceed limit (including previous turns)
                        if total_tool_calls_so_far + inner_calls > 200:
                            print(f"Tool calls count ({total_tool_calls_so_far + inner_calls}) exceeded 200, stopping interaction.")
                            agent_final_reply = "[Interaction stopped: tool calls exceeded 200]"
                            break

                        continue
                    else:
                        inner_rounds += 1
                        local_dialogue_logs.append({"role": "agent", "turn": turn, "content": agent_reply})
                        local_service_history.append({"role": "assistant", "content": agent_reply})
                        agent_final_reply = agent_reply
                        break

                agent_time = time.time() - agent_start
                print(f"[Time] Agent response generation (Turn {turn}): {agent_time:.3f} seconds")
                return {
                    "reply": agent_final_reply,
                    "input_tokens": inner_input_tokens,
                    "output_tokens": inner_output_tokens,
                    "calls": inner_calls,
                    "rounds": inner_rounds,
                    "tool_logs": local_tool_logs,
                    "dialogue_logs": local_dialogue_logs,
                    "time": agent_time,
                    "updated_history": local_service_history
                }

            # Start concurrency
            future_summary = executor.submit(generate_summary_task)
            future_agent = executor.submit(process_agent_task)

            turn_summary = future_summary.result()
            agent_res = future_agent.result()

            # Merge back agent updates
            input_tokens_total += agent_res["input_tokens"]
            output_tokens_total += agent_res["output_tokens"]
            tool_calls_count += agent_res["calls"]
            rounds_count += agent_res["rounds"]
            history_log["agent_response_time_seconds"] += agent_res["time"]
            history_log["tool_calls"].extend(agent_res["tool_logs"])
            history_log["dialogue"].extend(agent_res["dialogue_logs"])
            service_history = agent_res["updated_history"]

            last_agent_response_for_check = agent_res["reply"]

            if getattr(args, "summary_user", False) and turn_summary:
                summarized_history_str = f"Turn {turn} Dialogue Summary of completed steps: {turn_summary}\n"

            if args.user_mode == "easy":
                user_agent_sys_prompt = USER_TEXT_ONLY_PROMPT_EASY.format(
                    user_instruction=user_instruction,
                    image_description=image_description,
                    original_user_response="",
                    evaluation_feedback="",
                    history_summary=summarized_history_str,
                    service_agent_response=last_agent_response_for_check
                )
            elif args.user_mode == "hard":
                user_agent_sys_prompt = USER_TEXT_ONLY_PROMPT_HARD.format(
                    user_instruction=user_instruction,
                    image_description=image_description,
                    original_user_response="",
                    evaluation_feedback="",
                    history_summary=summarized_history_str,
                    service_agent_response=last_agent_response_for_check
                )
            else:
                user_agent_sys_prompt = USER_TEXT_ONLY_PROMPT_EASY.format(
                    user_instruction=user_instruction,
                    image_description=image_description,
                    original_user_response="",
                    evaluation_feedback="",
                    history_summary=summarized_history_str,
                    service_agent_response=last_agent_response_for_check
                )

            # Update User Messages for Next Turn
            user_messages[0]["content"] = user_agent_sys_prompt

            if getattr(args, "summary_user", False) and turn_summary:
                next_content = f"Please continue the conversation in the first person according to the original settings based on the summary and latest response."
                user_messages = [
                    {"role": "system", "content": user_agent_sys_prompt},
                    {"role": "user", "content": build_message_with_image(next_content, image_path, use_vision)}
                ]
            else:
                user_messages.append({"role": "user", "content": last_agent_response_for_check})

        executor.shutdown(wait=True)

        history_log["rounds_count"] = rounds_count
        history_log["input_tokens"] = input_tokens_total
        history_log["output_tokens"] = output_tokens_total
        history_log["tool_calls_count"] = tool_calls_count

        user_performance = {}
        if valid_evaluation_count > 0:
            for k, v in accumulated_original_scores.items():
                user_performance[f"original_{k}_avg"] = round(v / valid_evaluation_count, 2)
            for k, v in accumulated_final_scores.items():
                user_performance[f"final_{k}_avg"] = round(v / valid_evaluation_count, 2)
        history_log["user_performance"] = user_performance

        end_time = time.time()
        execution_time = round(end_time - start_time, 3)
        history_log["execution_time_seconds"] = execution_time
        all_results.append(history_log)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nCompleted! Results saved to: {output_path}")
    print(f"Statistics Summary: ")
    for idx, result in enumerate(all_results):
        print(f"  Task {idx+1}: {result['rounds_count']} dialogue rounds, {result['input_tokens']} input tokens, {result['output_tokens']} output tokens, {result['tool_calls_count']} tool calls, {result['execution_time_seconds']} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run dialogue simulation in three modes")
    parser.add_argument(
        "--service_model_name",
        choices=["qwen3-vl-225b", "glm-4.5v", "Qwen3.5-397B-A17B", "manual", "gemini-3.1-pro-preview",
                 "glm-5v-turbo", "qwen3.6-plus", "mimo-v2-omni", "kimi-k2.5", "doubao-seed-2-0-pro-260215"],
        default="qwen3-vl-225b",
        help="Tested agent model name"
    )

    parser.add_argument(
        "--scenario",
        choices=["retail", "kitchen", "restaurant", "order"],
        default="retail",
        help="Task scenario"
    )

    parser.add_argument(
        "--user_mode",
        type=str,
        choices=["easy", "hard", "static"],
        default="easy",
        help="User mode: easy(Simple), hard(Hard), static(Static - one-time interaction)"
    )

    parser.add_argument(
        "--scenario_number",
        type=int,
        default=1,
        help="Task scenario number"
    )

    parser.add_argument(
        "--multi_agent_user",
        action="store_true",
        help="When True, use LLM to check if user response contradicts the task in easy and hard modes, and correct if contradictory"
    )

    parser.add_argument(
        "--summary_user",
        action="store_true",
        help="When True, add a summary module after the user answers to avoid lengthy history information"
    )

    parser.add_argument(
        "--num_samples",
        type=int,
        default=0,
        help="Number of samples to test from the beginning of the scenario. 0 means test all samples."
    )

    args = parser.parse_args()

    INPUT_JSON = f"./scenarios/final/{args.scenario}{args.scenario_number}.json"
    TOOL_INFO_JSON = f"./tools/{args.scenario}/{args.scenario}_tools.json"
    OUTPUT_JSON = f"./results/{args.service_model_name}/{args.scenario}{args.scenario_number}_{args.user_mode}.json"
    if not os.path.exists(os.path.dirname(OUTPUT_JSON)):
        os.makedirs(os.path.dirname(OUTPUT_JSON))

    if args.user_mode == "static":
        run_static_simulation(INPUT_JSON, TOOL_INFO_JSON, OUTPUT_JSON, args=args, service_model_name=args.service_model_name)
    else:
        run_simulation(INPUT_JSON, TOOL_INFO_JSON, OUTPUT_JSON, args=args, service_model_name=args.service_model_name)