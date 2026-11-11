from __future__ import annotations

import argparse
import json
from pathlib import Path

from .causal_generator import CAUSAL_TASK_CLASSES, DIFFICULTIES, generate_causal_case
from .generator import TASK_CLASSES, generate_case
from .runner import run_engineering_task
from .tasks import engineering_tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a capped collective-intelligence engineering task")
    parser.add_argument("--task", default="eng-additive-001")
    parser.add_argument("--generated-task-seed", type=int)
    parser.add_argument("--causal-task-seed", type=int)
    parser.add_argument("--task-class", choices=TASK_CLASSES, default="additive")
    parser.add_argument("--difficulty", choices=DIFFICULTIES, default="moderate")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="openai/gpt-6.1-sol")
    parser.add_argument("--max-tokens", type=int, default=1400)
    parser.add_argument("--max-tool-rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261101)
    parser.add_argument("--target-tokens", type=int, default=25_000)
    parser.add_argument("--compute-tolerance", type=float, default=0.10)
    parser.add_argument("--request-timeout-seconds", type=int, default=300)
    parser.add_argument(
        "--condition",
        action="append",
        choices=["single_agent", "independent_vote", "independent_synthesizer", "communicating_collective"],
    )
    args = parser.parse_args()
    tasks = {task.task_id: task for task in engineering_tasks()}
    if args.causal_task_seed is not None:
        task = generate_causal_case(
            args.causal_task_seed, args.task_class, args.difficulty
        ).task
    elif args.generated_task_seed is not None:
        task = generate_case(args.generated_task_seed, args.task_class).task
    elif args.task in tasks:
        task = tasks[args.task]
    else:
        parser.error(f"unknown task: {args.task}; choose from {', '.join(tasks)}")
    conditions = tuple(args.condition) if args.condition else (
        "single_agent",
        "independent_vote",
        "independent_synthesizer",
        "communicating_collective",
    )
    results = run_engineering_task(
        task,
        output=Path(args.output),
        model=args.model,
        conditions=conditions,
        max_tokens=args.max_tokens,
        max_tool_rounds=args.max_tool_rounds,
        seed=args.seed,
        target_tokens=args.target_tokens,
        compute_tolerance=args.compute_tolerance,
        request_timeout_seconds=args.request_timeout_seconds,
    )
    print(json.dumps([result.mapping() for result in results], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
