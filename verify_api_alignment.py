#!/usr/bin/env python3
"""
Minimal example demonstrating exact Gemini API usage per official docs.
Reference: https://ai.google.dev/gemini-api/docs/quickstart

This script shows the three key patterns:
1. Client initialization
2. Text-only content generation
3. Multimodal (text + image) content generation
"""

from google import genai
import base64
import os

def example_1_text_only():
    """Example 1: Text-only generation (most common)"""
    print("=" * 60)
    print("EXAMPLE 1: Text-Only Generation")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY") or input("Enter your Gemini API key: ")
    
    # Initialize client
    client = genai.Client(api_key=api_key)
    print("✓ Client initialized")
    
    # Prepare content per official API structure
    contents = [
        {
            "parts": [
                {"text": "Explain quantum computing in one sentence."}
            ]
        }
    ]
    
    # Generate content with thinking config for Gemini 3+ models
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=contents
    )
    
    # Access response
    print(f"\n📝 Response:\n{response.text}\n")
    print("✅ Text-only generation successful!\n")


def example_2_simplified_text():
    """Example 2: Simplified text (SDK may accept shorthand)"""
    print("=" * 60)
    print("EXAMPLE 2: Simplified Text Pattern")
    print("=" * 60)
    
    api_key = os.getenv("GEMINI_API_KEY") or input("Enter your Gemini API key: ")
    client = genai.Client(api_key=api_key)
    
    # Some SDKs accept string directly and wrap it automatically
    # This is implementation-specific behavior
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents="What is the speed of light?"
        )
        print(f"\n📝 Response:\n{response.text}\n")
        print("✅ Simplified pattern works (SDK auto-wraps)!\n")
    except Exception as e:
        print(f"❌ Simplified pattern not supported: {e}")
        print("Using full structure instead...\n")
        
        # Fall back to full structure
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[{"parts": [{"text": "What is the speed of light?"}]}]
        )
        print(f"\n📝 Response:\n{response.text}\n")
        print("✅ Full structure works!\n")


def example_3_multimodal():
    """Example 3: Multimodal (text + image) - structure required"""
    print("=" * 60)
    print("EXAMPLE 3: Multimodal (Text + Image)")
    print("=" * 60)
    print("Note: This example shows the structure; skipping actual image\n")
    
    # Example structure for reference
    example_contents = [
        {
            "parts": [
                {"text": "What's in this image?"},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": "base64_encoded_image_bytes_here"
                    }
                }
            ]
        }
    ]
    
    print("📋 Multimodal content structure:")
    print("```python")
    print("contents = [")
    print("    {")
    print("        'parts': [")
    print("            {'text': 'What\\'s in this image?'},")
    print("            {")
    print("                'inline_data': {")
    print("                    'mime_type': 'image/jpeg',")
    print("                    'data': base64_image_data")
    print("                }")
    print("            }")
    print("        ]")
    print("    }")
    print("]")
    print("```")
    print("\n✓ Multimodal structure documented\n")


def example_4_list_models():
    """Example 4: List available models"""
    print("=" * 60)
    print("EXAMPLE 4: List Available Models")
    print("=" * 60)
    
    api_key = os.getenv("GEMINI_API_KEY") or input("Enter your Gemini API key: ")
    client = genai.Client(api_key=api_key)
    
    print("\n📋 Available models:\n")
    try:
        models = client.models.list()
        for m in models:
            print(f"  • {m.name}")
        print("\n✅ Models listed successfully!\n")
    except Exception as e:
        print(f"❌ Error listing models: {e}\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("GEMINI API - OFFICIAL PATTERNS DEMONSTRATION")
    print("Per: https://ai.google.dev/gemini-api/docs")
    print("=" * 60 + "\n")
    
    try:
        example_1_text_only()
        example_2_simplified_text()
        example_3_multimodal()
        example_4_list_models()
        
        print("=" * 60)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 60)
        print("\n✅ Your implementation is aligned with official Gemini API!")
        print("\nKey Points:")
        print("  1. Use: from google import genai")
        print("  2. Initialize: client = genai.Client(api_key=key)")
        print("  3. Structure: contents = [{'parts': [{'text': '...'}]}]")
        print("  4. Call: client.models.generate_content(model=..., contents=...)")
        print("  5. Access: response.text")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("\nMake sure your API key is valid and has access to Gemini models.")
