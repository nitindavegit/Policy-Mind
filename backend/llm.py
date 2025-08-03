# backend/llm.py
from ollama import Client
import torch
import json
import re

# Use phi3:mini for better instruction-following
client = Client(host="http://localhost:11434")

if torch.cuda.is_available():
    print("⚡ Using GPU")
else:
    print("🔧 Using CPU")


def call_phi3(prompt: str, max_retries: int = 2) -> str:
    """
    Calls Phi-3 with strict instruction to return only valid JSON.
    Includes retry logic for better reliability.
    """
    
    for attempt in range(max_retries + 1):
        print(f"\n{'='*60}")
        print(f"📤 ATTEMPT {attempt + 1}: SENDING PROMPT TO LLM")
        print(f"Prompt length: {len(prompt)} chars")
        print(prompt[:300] + ("..." if len(prompt) > 300 else ""))
        print("="*60)

        try:
            # Try different approaches based on attempt number
            if attempt == 0:
                # First attempt: Direct prompt
                system_msg = "You are a JSON assistant. Return only valid JSON, no other text."
                full_prompt = f"{system_msg}\n\n{prompt.strip()}"
                options = {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_ctx": 2048,
                    "num_predict": 512
                }
            else:
                # Retry attempts: Simpler, more direct
                full_prompt = f"Return valid JSON only:\n{prompt.strip()}"
                options = {
                    "temperature": 0.0,
                    "top_p": 0.7,
                    "num_ctx": 1024,
                    "num_predict": 256
                }

            response = client.generate(
                model="phi3:latest",
                prompt=full_prompt,
                options=options
            )
            
            raw_content = response.get('response', '').strip()
            
            print(f"\n📥 RAW LLM RESPONSE (attempt {attempt + 1}):")
            print(f"Length: {len(raw_content)} chars")
            print(repr(raw_content)[:200] + ("..." if len(repr(raw_content)) > 200 else ""))
            
            # Check if response is empty
            if not raw_content:
                print(f"❌ Empty response on attempt {attempt + 1}")
                if attempt < max_retries:
                    continue
                else:
                    return '{"error": "empty_response"}'

            # Clean the response
            content = clean_llm_response(raw_content)

            print(f"\n📥 CLEANED RESPONSE (attempt {attempt + 1}):")
            print(f"Length: {len(content)} chars")
            print(content)
            print("="*60)

            # Validate it's proper JSON
            if content:
                try:
                    json.loads(content)
                    print("✅ Valid JSON confirmed")
                    return content
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON on attempt {attempt + 1}: {e}")
                    if attempt < max_retries:
                        continue
                    else:
                        # Try to fix common issues one more time
                        fixed_content = emergency_json_fix(content)
                        try:
                            json.loads(fixed_content)
                            print("✅ Emergency fix successful")
                            return fixed_content
                        except:
                            return content  # Return anyway for further processing
            else:
                print(f"❌ Cleaned content is empty on attempt {attempt + 1}")
                if attempt < max_retries:
                    continue

        except Exception as e:
            print(f"❌ LLM Request Failed on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries:
                return '{"error": "llm_failed"}'
            continue

    return '{"error": "all_attempts_failed"}'


def clean_llm_response(response: str) -> str:
    """Clean and fix common issues in LLM responses"""
    
    # Remove markdown and noise
    response = re.sub(r'```json|```', '', response, flags=re.IGNORECASE)
    response = re.sub(r'(?i)(end of document|thank you|system:|assistant:|here is|here\'s)', '', response)
    
    # Remove leading/trailing whitespace and newlines
    response = response.strip()
    
    # Fix common JSON issues
    # Fix malformed numbers like 00.95 → 0.95
    response = re.sub(r':\s*0+(\d+\.\d+)', r': \1', response)
    response = re.sub(r':\s*0+(\d+)(?!\d)', r': \1', response)
    
    # Fix unquoted keys
    response = re.sub(r'([a-zA-Z_]\w*)\s*:', r'"\1":', response)
    
    # Fix trailing commas
    response = re.sub(r',(\s*[}\]])', r'\1', response)
    
    # Ensure proper string quoting for common values
    response = re.sub(r':\s*approved(?![a-zA-Z])', ': "approved"', response)
    response = re.sub(r':\s*rejected(?![a-zA-Z])', ': "rejected"', response)
    response = re.sub(r':\s*conditional(?![a-zA-Z])', ': "conditional"', response)
    response = re.sub(r':\s*male(?![a-zA-Z])', ': "male"', response)
    response = re.sub(r':\s*female(?![a-zA-Z])', ': "female"', response)
    
    # Fix "Up to Sum Insured" which might be unquoted
    response = re.sub(r':\s*Up to Sum Insured', ': "Up to Sum Insured"', response)
    
    # If response doesn't start with {, try to find and extract JSON
    if not response.startswith('{'):
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
    
    # Handle truncated JSON - if it's cut off, try to close it properly
    if response.startswith('{') and not response.endswith('}'):
        # Count unclosed braces and brackets
        open_braces = response.count('{') - response.count('}')
        open_brackets = response.count('[') - response.count(']')
        
        # Add missing closing characters
        response += ']' * open_brackets + '}' * open_braces
    
    return response


def emergency_json_fix(content: str) -> str:
    """Last resort JSON fixing for malformed responses"""
    if not content.strip():
        return '{"error": "empty_content"}'
    
    # If it looks like truncated JSON, try to complete it
    if content.startswith('{') and not content.endswith('}'):
        # Count unmatched braces
        open_count = content.count('{')
        close_count = content.count('}')
        
        if open_count > close_count:
            # Add missing closing braces
            content += '}' * (open_count - close_count)
    
    # If still not valid, create a simple error JSON
    try:
        json.loads(content)
        return content
    except:
        return '{"error": "malformed_json", "raw_content": "' + content.replace('"', '\\"')[:100] + '"}'


def test_llm_json_extraction():
    """Test function to verify LLM JSON extraction works"""
    test_prompt = """
Extract age, gender, and procedure from: "45-year old male needs knee surgery"

Return JSON:
{
  "age": number,
  "gender": "male"|"female",
  "procedure": "string"
}
"""
    
    try:
        result = call_phi3(test_prompt)
        parsed = json.loads(result)
        print(f"✅ Test successful: {parsed}")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def get_simple_llm_response(prompt: str) -> dict:
    """Simplified LLM call with guaranteed JSON response"""
    try:
        response = call_phi3(prompt)
        return json.loads(response)
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        return {"error": str(e), "fallback": True}


if __name__ == "__main__":
    # Run test when module is executed directly
    test_llm_json_extraction()