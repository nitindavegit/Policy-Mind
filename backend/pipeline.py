# backend/pipeline.py
import json
import re
import ast
from typing import Dict, Any

from backend.llm import call_phi3
from backend.vector_store import search_chunks


def extract_first_json_block(text: str) -> str:
    """
    Extract first valid JSON object from messy string.
    Handles markdown, unquoted keys, and broken syntax.
    """
    # Remove noise and markdown
    text = re.sub(r'```json|```', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?i)(end of document|thank you|system:|assistant:)', '', text)
    text = text.strip()

    # Fix common JSON issues
    # Fix unquoted keys like `ner:` 
    text = re.sub(r'([a-zA-Z_]\w*)\s*:', r'"\1":', text)
    
    # Fix malformed numbers like 00.95 → 0.95
    text = re.sub(r':\s*0+(\d+\.\d+)', r': \1', text)
    text = re.sub(r':\s*0+(\d+)', r': \1', text)
    
    # Fix null/true/false
    text = re.sub(r':\s*null\b', ': null', text, flags=re.IGNORECASE)
    text = re.sub(r':\s*true\b', ': true', text, flags=re.IGNORECASE)
    text = re.sub(r':\s*false\b', ': false', text, flags=re.IGNORECASE)

    # Find first '{' and balance braces
    start = text.find('{')
    if start == -1:
        return ""

    brace_count = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
        if brace_count == 0:
            candidate = text[start:i+1]
            
            # Try to fix truncated JSON by adding missing closing braces
            if candidate.count('{') > candidate.count('}'):
                missing_braces = candidate.count('{') - candidate.count('}')
                candidate += '}' * missing_braces
            
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError as e:
                # Try to fix common issues
                fixed = fix_json_syntax(candidate)
                try:
                    json.loads(fixed)
                    return fixed
                except:
                    # Fallback: try ast.literal_eval
                    try:
                        parsed = ast.literal_eval(candidate.replace("null", "None").replace("true", "True").replace("false", "False"))
                        if isinstance(parsed, dict):
                            return json.dumps(parsed)
                    except:
                        continue
    
    # If no complete JSON found, try to extract from truncated text
    return try_fix_truncated_json(text)


def fix_json_syntax(json_str: str) -> str:
    """Fix common JSON syntax issues"""
    # Remove trailing commas
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Fix unquoted strings that should be quoted
    json_str = re.sub(r':\s*([a-zA-Z][a-zA-Z0-9\s]*[a-zA-Z0-9])\s*(?=[,}])', r': "\1"', json_str)
    
    # Fix missing quotes around string values
    json_str = re.sub(r':\s*([^",{\[\]}\s][^",{\[\]]*[^",{\[\]}\s])\s*(?=[,}])', r': "\1"', json_str)
    
    return json_str


def try_fix_truncated_json(text: str) -> str:
    """Try to extract valid JSON from truncated text"""
    lines = text.split('\n')
    for i in range(len(lines), 0, -1):
        candidate = '\n'.join(lines[:i])
        
        # Find the last complete key-value pair
        brace_count = 0
        last_complete = -1
        
        for j, char in enumerate(candidate):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == ',' and brace_count == 1:
                last_complete = j
        
        if last_complete > 0:
            # Truncate at last complete field and close JSON
            truncated = candidate[:last_complete] + '}'
            try:
                json.loads(truncated)
                return truncated
            except:
                continue
    
    return ""


def extract_policy_duration(text: str) -> int:
    match = re.search(r"(\d+)\s*(month|year|week|day)s?", text, re.IGNORECASE)
    if not match:
        return 0
    val = int(match.group(1))
    unit = match.group(2).lower()
    if unit == "year":
        return val * 12
    elif unit == "week":
        return val // 4
    elif unit == "day":
        return val // 30
    else:
        return val


def parse_query_to_json(query: str) -> dict:
    # Extract duration
    duration_months = extract_policy_duration(query)

    # Extract age
    age_match = re.search(r"(\d+)[-]?\s*year[- ]old", query, re.IGNORECASE)
    age = int(age_match.group(1)) if age_match else None

    # Extract gender
    gender = "male" if "male" in query.lower() else "female" if "female" in query.lower() else "other"

    # Extract procedure (basic)
    procedures = ["knee surgery", "cataract surgery", "angioplasty", "appendectomy"]
    procedure = next((p for p in procedures if p in query.lower()), "unknown procedure")

    # Extract location
    location_match = re.search(r"in\s+([a-zA-Z\s]+?)(?:,|$)", query, re.IGNORECASE)
    location = location_match.group(1).strip() if location_match else "unknown"

    # Simplified LLM prompt with better instructions
    prompt = f"""
Extract information from this query and return ONLY a JSON object with these exact fields:

Query: "{query}"

Return this JSON structure (replace values with extracted data):
{{
  "age": {age if age else "null"},
  "gender": "{gender}",
  "procedure": "{procedure}",
  "location": "{location}",
  "policy_duration_months": {duration_months}
}}

IMPORTANT: Return ONLY the JSON object above. No explanations, no markdown, no extra text.
"""

    try:
        raw_response = call_phi3(prompt)
        json_str = extract_first_json_block(raw_response)
        
        if json_str:
            result = json.loads(json_str)
            # Validate and set defaults
            result.setdefault("age", age)
            result.setdefault("gender", gender)
            result.setdefault("procedure", procedure)
            result.setdefault("location", location)
            result.setdefault("policy_duration_months", duration_months)
            return result
        else:
            raise ValueError("No valid JSON found in LLM response")
            
    except Exception as e:
        print(f"❌ LLM parsing failed: {e}")
        # Fallback to rule-based extraction
        return {
            "age": age,
            "gender": gender,
            "procedure": procedure,
            "location": location,
            "policy_duration_months": duration_months
        }


def run_pipeline(user_query: str) -> dict:
    try:
        structured = parse_query_to_json(user_query)
        print(f"✅ Parsed query: {structured}")
    except Exception as e:
        return {
            "decision": "error",
            "amount": None,
            "confidence": 0.0,
            "justification": [],
            "error_message": f"Failed to parse query: {str(e)}",
            "raw_query": user_query,
            "user_friendly_response": "Sorry, I couldn't understand your query. Please try rephrasing it."
        }

    # Search relevant clauses
    search_query = f"{structured.get('procedure', '')} coverage waiting period exclusion"
    try:
        similar_chunks = search_chunks(search_query, k=4)
    except Exception as e:
        return {
            "decision": "error",
            "amount": None,
            "confidence": 0.0,
            "justification": [],
            "error_message": f"Failed to search clauses: {str(e)}",
            "user_friendly_response": "Sorry, there was an error processing your request. Please try again."
        }

    # Format clause context
    clause_text = "\n".join([
        f"[{c.get('clause_id', 'N/A')}] {c['text'][:400]}..." for c in similar_chunks
    ])

    # Use rule-based logic first, then try LLM for enhancement
    decision_result = make_rule_based_decision(structured)
    
    # Try to get LLM insights but don't rely on them
    try:
        llm_decision = get_llm_decision_simple(structured, clause_text)
        if llm_decision and not llm_decision.get('error'):
            # Merge LLM insights with rule-based decision
            decision_result['justification'] = llm_decision.get('justification', decision_result['justification'])
            if 'confidence' in llm_decision:
                decision_result['confidence'] = llm_decision['confidence']
    except Exception as e:
        print(f"⚠️ LLM decision failed, using rule-based: {e}")
    
    decision_result['query_structured'] = structured
    
    # Generate user-friendly response
    decision_result['user_friendly_response'] = generate_user_friendly_response(
        structured, decision_result
    )
    
    return decision_result


def generate_user_friendly_response(structured: dict, decision_result: dict) -> str:
    """Generate a natural language response for the user"""
    
    decision = decision_result.get('decision', 'unknown')
    procedure = structured.get('procedure', 'the procedure')
    age = structured.get('age', 'unknown')
    duration_months = structured.get('policy_duration_months', 0)
    amount = decision_result.get('amount')
    confidence = decision_result.get('confidence', 0.0)
    
    # Get the main reason from justification
    justifications = decision_result.get('justification', [])
    main_reason = justifications[0].get('match_reason', '') if justifications else ''
    
    # Generate response based on decision
    if decision == 'approved':
        response = f"✅ **Good news!** Your {procedure} is covered under your policy."
        
        if amount:
            response += f" Coverage amount: {amount}."
        
        if duration_months >= 1:
            response += f" Since your policy has been active for {duration_months} months, the waiting period requirements have been met."
        
        if main_reason and 'waiting period passed' in main_reason.lower():
            response += " All waiting periods have been satisfied."
            
    elif decision == 'rejected':
        response = f"❌ **Unfortunately**, your {procedure} claim cannot be approved at this time."
        
        if duration_months < 1:
            response += f" Your policy has been active for only {duration_months} months, but there's a 30-day waiting period for most procedures."
        elif 'pre-existing' in main_reason.lower():
            response += " This appears to be related to a pre-existing condition, which has a longer waiting period."
        elif 'age' in main_reason.lower():
            response += f" Additional medical review may be required due to age-related factors."
        else:
            response += f" Reason: {main_reason}"
            
    elif decision == 'conditional':
        response = f"⚠️ **Conditional approval** for your {procedure}."
        
        if amount:
            response += f" Coverage: {amount}."
        
        response += " Additional documentation or medical review may be required before final approval."
        
        if main_reason:
            response += f" {main_reason}"
            
    else:
        response = f"We've reviewed your {procedure} request but need more information to make a determination."
    
    # Add confidence indicator (subtle)
    if confidence >= 0.9:
        confidence_text = ""  # High confidence, no need to mention
    elif confidence >= 0.7:
        confidence_text = ""  # Medium confidence, still don't mention
    else:
        confidence_text = " Please contact customer service for final confirmation."
    
    response += confidence_text
    
    # Add helpful next steps
    if decision == 'approved':
        response += "\n\n**Next steps:** You can proceed with your treatment. Keep all medical bills and documents for claim submission."
    elif decision == 'rejected':
        response += "\n\n**Next steps:** Contact customer service for more details or wait for the required waiting period to complete."
    elif decision == 'conditional':
        response += "\n\n**Next steps:** Please submit additional medical documentation as requested by our claims team."
    
    return response


def generate_simple_response(structured: dict, decision: str, duration_months: int) -> str:
    """Simple fallback response generator"""
    procedure = structured.get('procedure', 'the procedure')
    
    if decision == 'approved':
        return f"✅ Yes, {procedure} is covered under your policy since you've completed the waiting period."
    elif decision == 'rejected':
        if duration_months < 1:
            return f"❌ {procedure} is not covered yet. Your policy needs to be active for at least 30 days."
        else:
            return f"❌ {procedure} is not covered under your current policy terms."
    else:
        return f"Your {procedure} request requires additional review. Please contact customer service."


def make_rule_based_decision(structured: dict) -> dict:
    """Rule-based decision logic that doesn't depend on LLM"""
    duration = structured.get('policy_duration_months', 0)
    procedure = structured.get('procedure', '').lower()
    age = structured.get('age')
    
    # Basic insurance rules
    if duration < 1:  # Less than 30 days
        return {
            "decision": "rejected",
            "amount": None,
            "confidence": 0.9,
            "justification": [
                {
                    "clause": "Code-Excl03",
                    "match_reason": "30-day waiting period has not passed",
                    "relevance_score": 0.95
                }
            ]
        }
    
    # Check for common exclusions
    if 'pre-existing' in procedure or 'chronic' in procedure:
        return {
            "decision": "rejected",
            "amount": None,
            "confidence": 0.85,
            "justification": [
                {
                    "clause": "Code-Excl01",
                    "match_reason": "Pre-existing condition exclusion applies",
                    "relevance_score": 0.9
                }
            ]
        }
    
    # Age-based checks
    if age and age > 80:
        return {
            "decision": "conditional",
            "amount": "Subject to medical review",
            "confidence": 0.7,
            "justification": [
                {
                    "clause": "Age-Related",
                    "match_reason": "Advanced age requires additional review",
                    "relevance_score": 0.8
                }
            ]
        }
    
    # Special procedures that might need longer waiting periods
    specified_diseases = ['cataract', 'hernia', 'kidney stone', 'gallbladder']
    if any(disease in procedure for disease in specified_diseases):
        if duration < 24:  # 24 months for specified diseases
            return {
                "decision": "rejected",
                "amount": None,
                "confidence": 0.8,
                "justification": [
                    {
                        "clause": "Code-Excl02",
                        "match_reason": "Specified diseases require 24-month waiting period",
                        "relevance_score": 0.85
                    }
                ]
            }
    
    # Default approval for standard cases
    return {
        "decision": "approved",
        "amount": "Up to Sum Insured",
        "confidence": 0.8,
        "justification": [
            {
                "clause": "Standard Coverage",
                "match_reason": f"Waiting period passed ({duration} months), standard procedure coverage applies",
                "relevance_score": 0.85
            }
        ]
    }


def get_llm_decision_simple(structured: dict, clause_text: str) -> dict:
    """Try to get LLM decision with very simple prompt"""
    simple_prompt = f"""
Claim: {structured.get('procedure', 'unknown')} for {structured.get('age', 'unknown')} year old
Policy: {structured.get('policy_duration_months', 0)} months old

Decision (approved/rejected/conditional):
Confidence (0.0-1.0):
Reason:

JSON format:
{{"decision": "approved", "confidence": 0.8, "reason": "waiting period passed"}}
"""
    
    try:
        from backend.llm import get_simple_llm_response
        result = get_simple_llm_response(simple_prompt)
        
        if result and not result.get('error'):
            # Convert simple response to full format
            return {
                "decision": result.get('decision', 'approved'),
                "confidence": result.get('confidence', 0.7),
                "justification": [
                    {
                        "clause": "LLM Analysis",
                        "match_reason": result.get('reason', 'LLM decision'),
                        "relevance_score": result.get('confidence', 0.7)
                    }
                ]
            }
    except Exception as e:
        print(f"Simple LLM decision failed: {e}")
    
    return {"error": "llm_failed"}