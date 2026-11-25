STRATEGIES = {
    "zero_shot": {"name": "Zero-Shot", "description": "Task only, no examples."},
    "few_shot": {"name": "Few-Shot", "description": "Two solved examples before the task."},
    "cot": {"name": "Chain-of-Thought", "description": "Reason step by step, then write code."},
    "role_based": {"name": "Role-Based", "description": "Act as a senior Python developer."},
    "iterative": {"name": "Iterative Refinement", "description": "Fix the code using test feedback (up to 3 attempts)."},
}
BASE_SYSTEM = (
    "You are a code generator. Write Python 3 code only. "
    "Return the complete function inside ONE ```python code block. "
    "No input(), no printing, no external libraries."
)

FEW_SHOT_EXAMPLES = '''Example 1
Task: Return the sum of two numbers.
Signature: def add(a: int, b: int) -> int
```python
def add(a: int, b: int) -> int:
    """Return a + b."""
    return a + b
```

Example 2
Task: Return True if n is even. Raise TypeError if n is not an int.
Signature: def is_even(n: int) -> bool
```python
def is_even(n: int) -> bool:
    """Return True when n is even."""
    if not isinstance(n, int):
        raise TypeError("n must be an int")
    return n % 2 == 0
```
'''


def _task_block(task):
    return f"Task: {task['description']}\nSignature: {task['signature']}"

def build_prompt(strategy: str, task: dict, feedback: dict | None = None):
    """Return (system_prompt, user_prompt). `feedback` is used by the iterative strategy."""
    system, task_block = BASE_SYSTEM, _task_block(task)

    if strategy == "zero_shot":
        user = task_block
    elif strategy == "few_shot":
        user = f"Here are solved examples:\n\n{FEW_SHOT_EXAMPLES}\nNow solve this one in the same style.\n{task_block}"
    elif strategy == "cot":
        system = BASE_SYSTEM.replace("Return the complete function inside ONE",
                                     "First reason step by step, then put the final function inside ONE")
        user = (f"{task_block}\n\nBefore coding: (1) restate the requirement, (2) list edge cases, "
                "(3) outline the algorithm. Then give the final code.")
    elif strategy == "role_based":
        system = ("You are a senior Python developer with 10 years of experience who writes correct, "
                  "readable, secure code and handles edge cases. " + BASE_SYSTEM)
        user = task_block
    elif strategy == "iterative":
        if not feedback:
            user = task_block
        else:
            user = (f"{task_block}\n\nYour previous solution:\n```python\n{feedback['code']}\n```\n"
                    f"It failed these checks:\n{feedback['report']}\n\nFix the code and return the corrected function.")
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    return system, user
