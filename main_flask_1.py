# flask implementation

# v1


#######################################
## Binding to all addresses process for ollama to be done before running the code

############ DO BELOW FOR UBUNTU MACHINE

# sudo gedit /etc/systemd/system/ollama.service.d/override.conf

#put below lines and save
"""
[Service]
Environment="OLLAMA_HOST=0.0.0.0"

"""
# sudo systemctl daemon-reload

# sudo systemctl restart ollama

### Try from other machine in same network

# curl http://ip-of-the-machine:11434/api/version

# it must show the version
######################################



############ DO BELOW FOR RASPBERRY PI

# sudo mkdir -p /etc/systemd/system/ollama.service.d

# sudo nano /etc/systemd/system/ollama.service.d/override.conf


#put below lines and save
"""
[Service]
Environment="OLLAMA_HOST=0.0.0.0"

"""
# sudo systemctl daemon-reload

# sudo systemctl restart ollama

### Try from other machine in same network

# curl http://ip-of-the-machine:11434/api/version

# it must show the version
######################################
###################################################################

######################

# peer1 models

# qwen2.5:0.5b-instruct, smollm2:360m-instruct-q8_0

# Not testing below as large size: 
#llama3.2:1b-instruct-q4_K_M, smollm2:1.7b-instruct-q4_K_M, granite3-moe:1b-instruct-q4_K_M, qwen2.5:1.5b-instruct-q4_K_M, 
#####################

# peer2 models
  
# granite3.1-moe:1b, llama3.2:1b, qwen2.5:1.5b, smollm2:1.7b  

####################

# PEER1_URL = "http://192.168.238.79:11434/api/generate"   # Machine 1’s Ollama

# PEER2_URL = "http://192.168.238.209:11434/api/generate"   # Machine 2’s Ollama

#################

# curl -X POST http://192.168.238.79:5000/generate -H "Content-Type: application/json"  -d '{"prompt": "Explain quantum mechanics."}'

#### Optional

# model can be specified


# curl -X POST http://<PEER1_IP>:5000/generate -H "Content-Type: application/json"      -d '{"model": "smollm2:360m-instruct-q8_0", "prompt": "Discuss relativity"}'


import time
import csv
import os
import json
import requests
from datetime import datetime

from flask import Flask, request, jsonify

app = Flask(__name__)

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
# Peer1's local Ollama endpoint (on this machine)
# If Ollama is bound to 127.0.0.1:11434, we can use local loopback:
PEER1_URL = "http://192.168.238.79:11434/api/generate"

# This is our default model for Peer1 if the user doesn't specify one in the JSON.
DEFAULT_PEER1_MODEL = "qwen2.5:0.5b-instruct"

# Peer2's Ollama endpoint (on machine 2) - replace with your actual IP
PEER2_URL = "http://192.168.238.209:11434/api/generate"
# This is the default model for Peer2 summarization
DEFAULT_PEER2_MODEL = "smollm2:1.7b"

CSV_FILENAME = "llm_interactions.csv"

# -----------------------------------------------------------------------------
# CSV FUNCTIONS
# -----------------------------------------------------------------------------
def init_csv():
    """
    Create the CSV file if it doesn't exist or if it's empty, and write column headers.
    """
    headers = [
        "timestamp",
        "prompt",

        # Peer1 columns
        "peer1_llm",
        "peer1_total_duration",
        "peer1_load_duration",
        "peer1_prompt_eval_count",
        "peer1_prompt_eval_duration",
        "peer1_eval_count",
        "peer1_eval_duration",
        "peer1_token_per_second",
        "peer1_network_duration",
        "peer1_response_ollama",

        # Peer2 columns
        "peer2_llm",
        "peer2_total_duration",
        "peer2_load_duration",
        "peer2_prompt_eval_count",
        "peer2_prompt_eval_duration",
        "peer2_eval_count",
        "peer2_eval_duration",
        "peer2_token_per_second",
        "peer2_network_duration",
        "peer2_response_ollama",
    ]

    # Only write headers if file doesn't exist OR file is empty
    if not os.path.exists(CSV_FILENAME) or os.path.getsize(CSV_FILENAME) == 0:
        with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        print(f"[DEBUG] CSV file initialized with headers: {headers}")
    else:
        print("[DEBUG] CSV file already exists and is not empty. Skipping header write.")


def append_to_csv(row: dict):
    """
    Append a single row of data to CSV in the correct column order.
    """
    with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            row.get("timestamp", ""),
            row.get("prompt", ""),

            # Peer1
            row.get("peer1_llm", ""),
            row.get("peer1_total_duration", 0),
            row.get("peer1_load_duration", 0),
            row.get("peer1_prompt_eval_count", 0),
            row.get("peer1_prompt_eval_duration", 0),
            row.get("peer1_eval_count", 0),
            row.get("peer1_eval_duration", 0),
            row.get("peer1_token_per_second", 0.0),
            row.get("peer1_network_duration", 0),
            row.get("peer1_response_ollama", ""),

            # Peer2
            row.get("peer2_llm", ""),
            row.get("peer2_total_duration", 0),
            row.get("peer2_load_duration", 0),
            row.get("peer2_prompt_eval_count", 0),
            row.get("peer2_prompt_eval_duration", 0),
            row.get("peer2_eval_count", 0),
            row.get("peer2_eval_duration", 0),
            row.get("peer2_token_per_second", 0.0),
            row.get("peer2_network_duration", 0),
            row.get("peer2_response_ollama", ""),
        ])

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS TO CALL PEER1 & PEER2
# -----------------------------------------------------------------------------
def call_peer1_generate(model_name: str, user_prompt: str) -> dict:
    """
    Calls /api/generate on Peer1 (Machine 1) with the given model & prompt.
    """
    print(f"[DEBUG] Generating text on Peer1: model='{model_name}', prompt length={len(user_prompt)}")
    start_time_ns = time.time_ns()

    request_data = {
        "model": model_name,   # e.g. "qwen2.5:0.5b-instruct"
        "prompt": user_prompt,
        "stream": False
    }

    try:
        resp = requests.post(PEER1_URL, json=request_data)
        resp.raise_for_status()
    except Exception as e:
        end_time_ns = time.time_ns()
        print("[ERROR] Peer1 generate call failed:", e)
        return {
            "peer1_llm": model_name,
            "peer1_total_duration": 0,
            "peer1_load_duration": 0,
            "peer1_prompt_eval_count": 0,
            "peer1_prompt_eval_duration": 0,
            "peer1_eval_count": 0,
            "peer1_eval_duration": 0,
            "peer1_token_per_second": 0.0,
            "peer1_network_duration": end_time_ns - start_time_ns,
            "peer1_response_ollama": f"Error: {str(e)}",
        }

    end_time_ns = time.time_ns()

    # Attempt to parse the JSON response from Ollama
    try:
        result_json = resp.json()
    except json.JSONDecodeError as je:
        print("[ERROR] Peer1 JSON parse error:", je)
        result_json = {}

    # Extract Ollama-specific fields
    total_duration = result_json.get("total_duration", 0)
    load_duration = result_json.get("load_duration", 0)
    prompt_eval_count = result_json.get("prompt_eval_count", 0)
    prompt_eval_duration = result_json.get("prompt_eval_duration", 0)
    eval_count = result_json.get("eval_count", 0)
    eval_duration = result_json.get("eval_duration", 0)
    text_generated = result_json.get("response", "")

    # Calculate tokens/sec if eval_duration > 0
    token_per_second = 0.0
    if eval_duration > 0:
        token_per_second = eval_count / eval_duration * 1e9

    print("[DEBUG] Peer1 done. Generated text length:", len(text_generated))

    return {
        "peer1_llm": model_name,
        "peer1_total_duration": total_duration,
        "peer1_load_duration": load_duration,
        "peer1_prompt_eval_count": prompt_eval_count,
        "peer1_prompt_eval_duration": prompt_eval_duration,
        "peer1_eval_count": eval_count,
        "peer1_eval_duration": eval_duration,
        "peer1_token_per_second": token_per_second,
        "peer1_network_duration": end_time_ns - start_time_ns,
        "peer1_response_ollama": text_generated,
    }


def call_peer2_operations(model_name: str, text_to_summarize: str) -> dict:
    """
    Calls /api/generate on Peer2 (Machine 2) to summarize the text using a second model.
    """
    print(f"[DEBUG] Summarizing on Peer2: model='{model_name}', text length={len(text_to_summarize)}")
    start_time_ns = time.time_ns()

    request_data = {
        "model": model_name,  # e.g. "granite3.1-moe:1b"
        "prompt": f"Summarize the following text in 2 lines:\n\n{text_to_summarize}",
        "stream": False
    }

    try:
        resp = requests.post(PEER2_URL, json=request_data)
        resp.raise_for_status()
    except Exception as e:
        end_time_ns = time.time_ns()
        print("[ERROR] Peer2 summarize call failed:", e)
        return {
            "peer2_llm": model_name,
            "peer2_total_duration": 0,
            "peer2_load_duration": 0,
            "peer2_prompt_eval_count": 0,
            "peer2_prompt_eval_duration": 0,
            "peer2_eval_count": 0,
            "peer2_eval_duration": 0,
            "peer2_token_per_second": 0.0,
            "peer2_network_duration": end_time_ns - start_time_ns,
            "peer2_response_ollama": f"Error: {str(e)}",
        }

    end_time_ns = time.time_ns()

    # Attempt to parse JSON
    try:
        result_json = resp.json()
    except json.JSONDecodeError as je:
        print("[ERROR] Peer2 JSON parse error:", je)
        result_json = {}

    total_duration = result_json.get("total_duration", 0)
    load_duration = result_json.get("load_duration", 0)
    prompt_eval_count = result_json.get("prompt_eval_count", 0)
    prompt_eval_duration = result_json.get("prompt_eval_duration", 0)
    eval_count = result_json.get("eval_count", 0)
    eval_duration = result_json.get("eval_duration", 0)
    summarized_text = result_json.get("response", "")

    # Calculate tokens/sec
    token_per_second = 0.0
    if eval_duration > 0:
        token_per_second = eval_count / eval_duration * 1e9

    print("[DEBUG] Peer2 done. Summary length:", len(summarized_text))
    return {
        "peer2_llm": model_name,
        "peer2_total_duration": total_duration,
        "peer2_load_duration": load_duration,
        "peer2_prompt_eval_count": prompt_eval_count,
        "peer2_prompt_eval_duration": prompt_eval_duration,
        "peer2_eval_count": eval_count,
        "peer2_eval_duration": eval_duration,
        "peer2_token_per_second": token_per_second,
        "peer2_network_duration": end_time_ns - start_time_ns,
        "peer2_response_ollama": summarized_text,
    }

# -----------------------------------------------------------------------------
# FLASK ENDPOINT
# -----------------------------------------------------------------------------
@app.route("/generate", methods=["POST"])
def generate_and_operations():
    """
    JSON body with:
      {
        "prompt": "the user prompt"   (required)
        "model": "optional peer1 model name"  (optional)
      }
    1. We use the given (or default) model on Peer1 to generate text.
    2. Summarize that text on Peer2 using the default summarization model.
    3. Log everything to CSV.
    4. Return the final summary to the user.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body provided."}), 400

    user_prompt = data.get("prompt", "")
    if not user_prompt:
        return jsonify({"error": "No prompt field provided in JSON."}), 400

    # If the user didn't specify "model", use DEFAULT_PEER1_MODEL
    peer1_model = data.get("model", DEFAULT_PEER1_MODEL)
    print(f"[DEBUG] Received prompt='{user_prompt}', Peer1 model='{peer1_model}'")

    # Step 1: Generate text from Peer1
    peer1_results = call_peer1_generate(peer1_model, user_prompt)

    # Step 2: Summarize with Peer2
    peer2_results = call_peer2_operations(DEFAULT_PEER2_MODEL, peer1_results["peer1_response_ollama"])

    # Merge for CSV
    row = {
        "timestamp": datetime.now().isoformat(),
        "prompt": user_prompt,
        **peer1_results,
        **peer2_results,
    }
    append_to_csv(row)

    # Final summary is the Peer2 text
    final_summary = peer2_results["peer2_response_ollama"]
    return jsonify({
        "peer1_text": peer1_results["peer1_response_ollama"],
        "peer2_summary": final_summary,
        "final_summary": final_summary
    })


def main():
    init_csv()
    # Run the Flask server on Machine 1, accessible via IP on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
