#!/usr/bin/env python3
"""
Quick test script to verify Gemini API with the new google-genai package
Per official docs: https://ai.google.dev/gemini-api/docs/quickstart
"""
from google import genai
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
    
    print("\nTesting gemini-2.5-flash model...")
    
    # Test the model with proper content structure
    # Per official API: contents should be array of content objects with parts
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "parts": [
                        {"text": "Say hello in one sentence!"}
                    ]
                }
            ]
        )
        print(f"✓ Model response: {response.text}")
        print("\n✅ SUCCESS! gemini-2.5-flash is working with the official SDK!")
    except Exception as e:
        print(f"❌ Error with gemini-2.5-flash: {e}")
        print("\nTrying gemini-1.5-flash instead...")
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    {
                        "parts": [
                            {"text": "Say hello in one sentence!"}
                        ]
                    }
                ]
            )
            print(f"✓ Model response: {response.text}")
            print("\n✅ SUCCESS! gemini-1.5-flash is working!")
        except Exception as e2:
            print(f"❌ Error with gemini-1.5-flash: {e2}")

if __name__ == "__main__":
    test_gemini_api()
