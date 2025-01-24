# pass@k metric using Ollama
# Partha Pratim Ray
# 24/1/2025

import requests
import subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def generate_candidates(prompt, model="codellama:code", n=5):
    """Generate n code candidates from the given LLM using the Ollama API."""
    url = "http://localhost:11434/api/generate"
    candidates = []

    for _ in range(n):
        response = requests.post(
            url,
            json={
                "model": model,
                "prompt": prompt,
                "options": {
                    "temperature": 0.7,
                    "top_k": 50,
                    "top_p": 0.95
                },
                "stream": False
            }
        )
        response_data = response.json()
        candidates.append(response_data.get("response", ""))

    return candidates

def check_correctness(code, test_case):
    """Check if the generated code passes the test case."""
    program = f"{code}\n{test_case}"

    try:
        result = subprocess.run(
            ["python3", "-c", program],
            capture_output=True,
            text=True,
            timeout=3  # Timeout to avoid infinite loops
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

def estimate_pass_at_k(num_samples, num_correct, k):
    """Estimate pass@k for a given problem."""
    if num_samples < k:
        return 1.0 if num_correct > 0 else 0.0
    return 1.0 - np.prod(1.0 - k / np.arange(num_samples - num_correct + 1, num_samples + 1))

def calculate_pass_at_k(candidates, test_case, k_values=[1, 10, 100]):
    """Calculate pass@k for the given candidates and test case."""
    num_samples = len(candidates)
    correct = sum(check_correctness(code, test_case) for code in candidates)

    pass_at_k = {
        f"pass@{k}": estimate_pass_at_k(num_samples, correct, k)
        for k in k_values
        if num_samples >= k
    }

    return pass_at_k

def evaluate_pass_at_k(prompt, test_case, models, n=100, k_values=[1, 10, 100]):
    """Evaluate pass@k for multiple LLMs."""
    results = {}

    for model in models:
        print(f"Evaluating model: {model}")
        candidates = generate_candidates(prompt, model=model, n=n)
        pass_at_k_results = calculate_pass_at_k(candidates, test_case, k_values=k_values)
        results[model] = pass_at_k_results

    return results

if __name__ == "__main__":
    # Example prompt and test case
    test_case = "assert add(2, 3) == 5"
    prompt = "def add(a, b):"

    # List of models to evaluate
    models = [
        "qwen2.5:0.5b-instruct",
        "smollm2:360m-instruct-q8_0",
        "granite3.1-moe",
        "llama3.2:1b",
        "qwen2.5:1.5b",
        "smollm2:1.7b"
    ]

    # Evaluate pass@k for all models
    results = evaluate_pass_at_k(prompt, test_case, models, n=100, k_values=[1, 10, 100])

    # Print results
    for model, pass_at_k_results in results.items():
        print(f"Model: {model}")
        print("Pass@k Results:", pass_at_k_results)
        print("---")
