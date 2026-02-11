import google.generativeai as genai
import os

# Paste your key here directly to test
os.environ["GOOGLE_API_KEY"] = "AIzaSyD4LHyMXpnAKjGAQ2NHxwN6Ib9BjLB2KII"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

print("Checking available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")