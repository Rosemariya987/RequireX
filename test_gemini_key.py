"""
Quick diagnostic: confirms whether your GEMINI_API_KEY in .env actually works.
Run this from the project root (same folder as your .env):

    python test_gemini_key.py

It will tell you clearly: VALID KEY / INVALID KEY / NO KEY FOUND, plus which
model responded, so you know for certain whether REQUIRE-X is really calling
Gemini or silently falling back to the rule-based engine.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed — run: pip install python-dotenv")

api_key = os.environ.get("GEMINI_API_KEY", "")

if not api_key:
    print("❌ NO KEY FOUND: GEMINI_API_KEY is not set in your environment or .env file.")
    exit(1)

print(f"Found key starting with: {api_key[:8]}... (length: {len(api_key)})")
print("Attempting a live call to Gemini...\n")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    # Try to list models first — this alone proves the key is valid
    models = [m.name for m in genai.list_models() if "generateContent" in getattr(m, "supported_generation_methods", [])]
    if not models:
        print("⚠️  Key accepted but no usable models returned. Check API access/quota in Google AI Studio.")
        exit(1)

    print(f"✅ KEY IS VALID. {len(models)} usable model(s) found, e.g.: {models[0]}")

    # Now try an actual generation call, same as REQUIRE-X does
    model = genai.GenerativeModel(model_name=models[0].replace("models/", ""))
    response = model.generate_content("Reply with exactly: OK")
    print(f"✅ Live generation call succeeded. Response: {response.text.strip()}")
    print("\nYour REQUIRE-X app SHOULD be using Gemini, not the offline fallback.")
    print("If your app is still showing offline-mode results, restart Streamlit fully")
    print("(the running process cached the old .env at startup).")

except Exception as e:
    print(f"❌ INVALID KEY OR CALL FAILED: {e}")
    print("\nThis is the exact exception REQUIRE-X's LLMProvider catches silently")
    print("before falling back to rule-based mode. This is why your ambiguity/")
    print("architecture/test-gen results looked templated rather than LLM-generated.")