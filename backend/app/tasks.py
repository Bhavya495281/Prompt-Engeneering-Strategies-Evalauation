TASKS = [
    {
        "id": "reverse_string",
        "title": "Reverse a string",
        "function": "reverse_string",
        "signature": "def reverse_string(s: str) -> str",
        "description": "Return the input string reversed.",
        "tests": [
            {"args": ["abc"], "expected": "cba"},
            {"args": [""], "expected": ""},
            {"args": ["a"], "expected": "a"},
            {"args": ["hello world"], "expected": "dlrow olleh"},
            {"args": ["racecar"], "expected": "racecar"},
        ],
        "reference": "def reverse_string(s: str) -> str:\n    \"\"\"Return s reversed.\"\"\"\n    return s[::-1]\n",
        "buggy": "def reverse_string(s):\n    return s[1:][::-1]\n",
    },
    {
        "id": "is_prime",
        "title": "Prime number check",
        "function": "is_prime",
        "signature": "def is_prime(n: int) -> bool",
        "description": "Return True if n is a prime number, otherwise False. Numbers below 2 are not prime.",
        "tests": [
            {"args": [0], "expected": False},
            {"args": [1], "expected": False},
            {"args": [2], "expected": True},
            {"args": [3], "expected": True},
            {"args": [4], "expected": False},
            {"args": [17], "expected": True},
            {"args": [18], "expected": False},
            {"args": [97], "expected": True},
            {"args": [100], "expected": False},
            {"args": [-5], "expected": False},
        ],
        "reference": (
            "def is_prime(n: int) -> bool:\n    \"\"\"Return True if n is prime.\"\"\"\n"
            "    if n < 2:\n        return False\n"
            "    i = 2\n    while i * i <= n:\n        if n % i == 0:\n            return False\n        i += 1\n"
            "    return True\n"
        ),
        "buggy": "def is_prime(n):\n    for i in range(2, n):\n        if n % i == 0:\n            return False\n    return True\n",
    },
    {
        "id": "sort_list",
        "title": "Sort a list",
        "function": "sort_list",
        "signature": "def sort_list(lst: list) -> list",
        "description": "Return a new list with the elements of lst sorted in ascending order. Do not use the built-in sorted() or list.sort(); implement a sorting algorithm yourself.",
        "tests": [
            {"args": [[3, 1, 2]], "expected": [1, 2, 3]},
            {"args": [[]], "expected": []},
            {"args": [[5]], "expected": [5]},
            {"args": [[2, 2, 1, 1]], "expected": [1, 1, 2, 2]},
            {"args": [[-1, 5, 0, -10]], "expected": [-10, -1, 0, 5]},
            {"args": [[9, 8, 7, 6, 5, 4, 3, 2, 1]], "expected": [1, 2, 3, 4, 5, 6, 7, 8, 9]},
        ],
        "reference": (
            "def sort_list(lst: list) -> list:\n    \"\"\"Insertion sort; returns a new list.\"\"\"\n"
            "    out = list(lst)\n"
            "    for i in range(1, len(out)):\n        key = out[i]\n        j = i - 1\n"
            "        while j >= 0 and out[j] > key:\n            out[j + 1] = out[j]\n            j -= 1\n"
            "        out[j + 1] = key\n    return out\n"
        ),
        "buggy": "def sort_list(lst):\n    out = list(lst)\n    for i in range(len(out)):\n        for j in range(len(out) - 1):\n            if out[j] < out[j + 1]:\n                out[j], out[j + 1] = out[j + 1], out[j]\n    return out\n",
    },
    {
        "id": "factorial",
        "title": "Factorial",
        "function": "factorial",
        "signature": "def factorial(n: int) -> int",
        "description": "Return n! for a non-negative integer n. Raise ValueError if n is negative.",
        "tests": [
            {"args": [0], "expected": 1},
            {"args": [1], "expected": 1},
            {"args": [5], "expected": 120},
            {"args": [10], "expected": 3628800},
            {"args": [-3], "raises": "ValueError"},
        ],
        "reference": (
            "def factorial(n: int) -> int:\n    \"\"\"Return n!.\"\"\"\n"
            "    if n < 0:\n        raise ValueError(\"n must be non-negative\")\n"
            "    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result\n"
        ),
        "buggy": "def factorial(n):\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result\n",
    },
    {
        "id": "find_largest",
        "title": "Largest element",
        "function": "find_largest",
        "signature": "def find_largest(arr: list)",
        "description": "Return the largest element of a non-empty list of numbers. Raise ValueError if the list is empty. Do not use the built-in max().",
        "tests": [
            {"args": [[1, 5, 3]], "expected": 5},
            {"args": [[-1, -5, -3]], "expected": -1},
            {"args": [[7]], "expected": 7},
            {"args": [[2, 2, 2]], "expected": 2},
            {"args": [[0, -4, 12, 11]], "expected": 12},
            {"args": [[]], "raises": "ValueError"},
        ],
        "reference": (
            "def find_largest(arr: list):\n    \"\"\"Return the largest element.\"\"\"\n"
            "    if not arr:\n        raise ValueError(\"empty list\")\n"
            "    best = arr[0]\n    for x in arr[1:]:\n        if x > best:\n            best = x\n    return best\n"
        ),
        "buggy": "def find_largest(arr):\n    best = 0\n    for x in arr:\n        if x > best:\n            best = x\n    return best\n",
    },
]

TASK_MAP = {t["id"]: t for t in TASKS}

def public_task(t):
    return {k: t[k] for k in ("id", "title", "description", "signature")} | {"n_tests": len(t["tests"])}
