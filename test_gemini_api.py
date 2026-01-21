#!/usr/bin/env python3
"""
Quick test script to verify Gemini API with the new google-genai package
Per official docs: https://ai.google.dev/gemini-api/docs/quickstart

Updated for Gemini 3 thought signature validation:
https://ai.google.dev/gemini-api/docs/thought-signatures
"""
from google import genai
from google.genai import types
import os

def test_gemini_api():
    """Test the Gemini API connection and model availability"""
    
    # Prompt for API key if not in environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = input("Enter your Gemini API key: ")
    
    # Create client per official API pattern
    client = genai.Client(api_key=api_key)
    
    print("✓ API client created successfully\n")
    
    # List available models
    print("Available models:")
    try:
        models = client.models.list()
        for m in models:
            print(f"  - {m.name}")
    except Exception as e:
        print(f"  Could not list models: {e}")
    
    print("\nTesting gemini-flash-latest model with thinking config...")
    
    # Test the model with thinking config for Gemini 3+ thought signature validation
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                {
                    "parts": [
                        {"text": "Say hello in one sentence!"}
                    ]
                }
            ],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=256
                )
            )
        )
        print(f"✓ Model response: {response.text}")
        print("\n✅ SUCCESS! gemini-flash-latest is working with thinking config!")
    except Exception as e:
        print(f"❌ Error with gemini-flash-latest: {e}")
        print("\nTrying gemini-pro-latest instead...")
        try:
            response = client.models.generate_content(
                model="gemini-pro-latest",
                contents=[
                    {
                        "parts": [
                            {"text": "Say hello in one sentence!"}
                        ]
                    }
                ],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=256
                    )
                )
            )
            print(f"✓ Model response: {response.text}")
            print("\n✅ SUCCESS! gemini-pro-latest is working!")
        except Exception as e2:
            print(f"❌ Error with gemini-pro-latest: {e2}")

if __name__ == "__main__":
    test_gemini_api()
