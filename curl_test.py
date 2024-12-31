# curl test

### Prompt Types
"""
Explanation
Logical
Creative
Numerical
Comparative
"""

import subprocess
import json
import time

# Flask server URL
FLASK_URL = "http://192.168.238.79:5000/generate"

# Prompts to send
PROMPTS = [
    "Explain quantum mechanics.",
    "What are the three laws of motion?",
    "Write a short story about a robot discovering emotions.",
    "What is the next number in the series: 1, 4, 9, 16?",
    "Compare the features of Python and Java programming languages."
]

# Function to send a prompt using curl and return the response
def send_prompt(prompt):
    try:
        print(f"[DEBUG] Sending prompt: {prompt}")
        # Prepare the JSON payload
        payload = json.dumps({"prompt": prompt})

        # Use subprocess to execute the curl command
        result = subprocess.run(
            [
                "curl", "-X", "POST", FLASK_URL, "-H", "Content-Type: application/json", "-d", payload
            ],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"[ERROR] Curl failed: {result.stderr}")
            return None

        # Parse and return the response
        response = json.loads(result.stdout)
        print(f"[DEBUG] Received response: {response}")
        return response
    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        return None

# Iterate through the prompts and send them one by one
def main():
    for prompt in PROMPTS:
        response = send_prompt(prompt)
        time.sleep(1)  # Add a delay between requests to avoid overloading the server

if __name__ == "__main__":
    main()

