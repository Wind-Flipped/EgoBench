#!/usr/bin/env python3
"""Generate three simulated-user responses for semantic prompt review."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run.prompts import (  # noqa: E402
    STATIC_USER_PROMPT,
    USER_TEXT_ONLY_PROMPT_EASY,
    USER_TEXT_ONLY_PROMPT_HARD,
)
from run.test.run_csv_samples import (  # noqa: E402
    DEFAULT_CSV_PATH,
    call_llm,
    load_samples,
)


VALIDATION_CASES = (
    {
        "mode": "easy",
        "sample_id": "warehouse_018",
        "source_expression": "今天是2026年八月的第二个星期六",
    },
    {
        "mode": "hard",
        "sample_id": "warehouse_041",
        "source_expression": "今天是2026年八月的第四个星期日",
    },
    {
        "mode": "static",
        "sample_id": "warehouse_013",
        "source_expression": "今天是2026年8月10日后的第四天",
    },
)
OPENING_MESSAGE = (
    "You are a customer in the environment shown in the video, and you need "
    "to complete the instructions in **Task**. I am your AI customer service "
    "representative; please interact with me in the first person. Let's begin "
    "the conversation.\nDear customer, how can I help you?"
)


def build_prompt(mode: str, instruction: str, image_description: str) -> str:
    if mode == "static":
        return STATIC_USER_PROMPT.format(user_instruction=instruction)

    template = (
        USER_TEXT_ONLY_PROMPT_EASY
        if mode == "easy"
        else USER_TEXT_ONLY_PROMPT_HARD
    )
    return template.format(
        user_instruction=instruction,
        image_description=image_description,
        original_user_response="",
        evaluation_feedback="",
        history_summary="",
        service_agent_response="Dear customer, how can I help you?",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-model", default="GPT-5.5")
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            PROJECT_ROOT
            / "test_results/prompt_validation/three_samples_three_modes.json"
        ),
    )
    args = parser.parse_args()

    samples = {
        sample.sample_id: sample
        for sample in load_samples(
            DEFAULT_CSV_PATH,
            [case["sample_id"] for case in VALIDATION_CASES],
        )
    }
    results = []
    for case in VALIDATION_CASES:
        mode = case["mode"]
        sample = samples[case["sample_id"]]
        messages = [
            {
                "role": "system",
                "content": build_prompt(
                    mode, sample.instruction, sample.video_description
                ),
            },
            {"role": "user", "content": OPENING_MESSAGE},
        ]
        started = time.monotonic()
        response, input_tokens, output_tokens = call_llm(
            messages,
            agent_type="user",
            service_model_name="Qwen3.5-397B-A17B",
            user_model_name=args.user_model,
        )
        result = {
            "mode": mode,
            "sample_id": sample.sample_id,
            "source_expression": case["source_expression"],
            "response": response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        results.append(result)
        print(f"[{mode}/{sample.sample_id}]: {response}")

    payload = {
        "user_model": args.user_model,
        "tested_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "review_method": "manual semantic review",
        "results": results,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
