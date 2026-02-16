import os
from llama_cpp import Llama

# Checking the path you showed in screenshots
MODEL_PATH = "/data/data/com.termux/files/home/models/Qwen2.5-3B-Instruct-Q4_K_M.gguf"

print(f"--- DIAGNOSTIC CHECK ---")
print(f"Target: {MODEL_PATH}")

if not os.path.exists(MODEL_PATH):
    print("❌ CRITICAL: Model file is MISSING at this path.")
    exit()

# check size (should be > 1GB)
size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
print(f"Size: {size_mb:.2f} MB")

if size_mb < 100:
    print("❌ CRITICAL: File is too small. You downloaded a broken HTML link, not the model.")
    exit()

try:
    print("⚡ Attempting to load Neural Network...")
    # n_gpu_layers=0 is safest for Termux
    llm = Llama(model_path=MODEL_PATH, n_gpu_layers=0, verbose=False)
    print("✅ SUCCESS: Brain is ONLINE.")

    print("⚡ Generating test thought...")
    res = llm.create_chat_completion(
        messages=[{"role": "user", "content": "Say 'Ready for combat'."}],
        max_tokens=10
    )
    print("🤖 RESPONSE:", res['choices'][0]['message']['content'])

except Exception as e:
    print(f"❌ CRITICAL FAILURE: {e}")
