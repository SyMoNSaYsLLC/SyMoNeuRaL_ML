from __future__ import annotations


def build_fine_tune_plan(data: dict) -> dict:
    examples = data.get("examples") or []
    valid = []
    problems = []
    for i, ex in enumerate(examples):
        prompt = (ex.get("prompt") or "").strip() if isinstance(ex, dict) else ""
        completion = (ex.get("completion") or "").strip() if isinstance(ex, dict) else ""
        if not prompt or not completion:
            problems.append(f"example {i} needs prompt and completion")
        else:
            valid.append({"prompt": prompt, "completion": completion})
    return {
        "base_model": data.get("base_model") or "qwen2.5-coder-1.5b-instruct",
        "output_name": data.get("output_name") or "symoneural-lora-adapter",
        "valid_examples": len(valid),
        "problems": problems,
        "recommended_min_examples": 50,
        "format": {"prompt": "user/task text", "completion": "ideal model answer"},
        "workflow": [
            "collect clean prompt/completion JSONL",
            "validate and dedupe rows",
            "tokenize with the base model tokenizer",
            "train LoRA/PEFT adapter outside the production web server",
            "evaluate adapter with fixed test prompts",
            "export adapter under models/adapters/<output_name>/",
        ],
    }
