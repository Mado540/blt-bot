import os
from llama_cpp import Llama

# PATH FROM YOUR SCREENSHOTS
path = "/data/data/com.termux/files/home/models/Qwen2.5-3B-Instruct-Q4_K_M.gguf"

print(f"🔎 INSPECTING: {path}")

# 1. CHECK HEADER (Is it actually a GGUF?)
try:
    if not os.path.exists(path):
        print("❌ FILE MISSING.")
        exit()
        
    with open(path, "rb") as f:
        header = f.read(4)
        print(f"🧬 MAGIC BYTES: {header}")
        
        if header != b'GGUF':
            print("❌ INVALID FILE: This is not a GGUF model. It is corrupted.")
            print(f"   (Bytes found: {header})")
            exit()
        else:
            print("✅ FILE INTEGRITY: PASSED (Valid GGUF Header)")
except Exception as e:
    print(f"❌ READ ERROR: {e}")
    exit()

# 2. THE ANDROID FIX (Disable MMAP)
print("⚡ ATTEMPTING LOAD WITH use_mmap=False ...")
try:
    # use_mmap=False forces the file to be read into RAM normally
    # This bypasses Android's restriction.
    llm = Llama(
        model_path=path, 
        n_gpu_layers=0, 
        use_mmap=False,   # <--- THE MAGIC FIX
        verbose=True      # <--- Show us what C++ is saying
    )
    print("🎉 SUCCESS: BRAIN LOADED!")
    
    # Test generation
    res = llm.create_chat_completion(
        messages=[{"role": "user", "content": "System status?"}],
        max_tokens=10
    )
    print("🤖 RESPONSE:", res['choices'][0]['message']['content'])

except Exception as e:
    print(f"💀 LOAD FAILURE: {e}")
