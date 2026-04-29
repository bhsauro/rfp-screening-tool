#!/usr/bin/env python3
"""
Simple RFP Screener - POC
Demonstrates: LLM extraction → Rules-based scoring → Recommendation
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

# Load API key from .env
load_dotenv()

# Scoring weights
WEIGHTS = {
    "service_fit": 0.30,
    "win_likelihood": 0.20,
    "deadline_feasibility": 0.15,
    "strategic_fit": 0.15,
    "revenue_value": 0.10,
    "proposal_effort": 0.10,
}


def load_prompt():
    """Load prompt from external file."""
    prompt_path = Path(__file__).parent / "prompt.txt"
    with open(prompt_path, 'r') as f:
        return f.read()


def load_company_context():
    """Load company context from external file."""
    context_path = Path(__file__).parent / "company_context.txt"
    with open(context_path, 'r') as f:
        return f.read()


def load_mock_response():
    """Load mock response from external file."""
    mock_path = Path(__file__).parent / "mock_response.json"
    with open(mock_path, 'r') as f:
        return json.load(f)


def parse_rfp(rfp_text):
    """Use Claude to parse RFP and extract structured data."""
    client = anthropic.Anthropic()
    company_context = load_company_context()
    prompt = load_prompt()

    # Combine context + prompt + RFP
    full_prompt = f"{company_context}\n\n{prompt}{rfp_text}"

    response = client.messages.create(
        model="claude-opus-4-7",  # Update this to working model
        max_tokens=3000,
        messages=[{"role": "user", "content": full_prompt}]
    )

    # Clean response and parse JSON (improved cleanup)
    text = response.content[0].text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    return json.loads(text.strip())


def validate_score(score, category):
    """Validate that a score is numeric and between 1-5."""
    if not isinstance(score, (int, float)):
        raise ValueError(f"{category}: score must be numeric, got {type(score).__name__}")

    if score < 1 or score > 5:
        raise ValueError(f"{category}: score must be 1-5, got {score}")

    return float(score)


def calculate_score(llm_result):
    """Apply rules-based scoring using weights.

    Note: Always calculates score for demo purposes, even if eligibility fails.
    Recommendation logic will still account for eligibility status.
    """
    # Calculate weighted score with validation
    total = 0
    for category, weight in WEIGHTS.items():
        score = llm_result["scores"][category]["score"]
        validated_score = validate_score(score, category)
        total += validated_score * weight

    return round(total, 2)


def get_recommendation(weighted_score, eligibility):
    """Determine recommendation based on score and eligibility.

    Note: Eligibility fail/unclear will override score-based recommendation.
    This ensures compliance requirements are prioritized over scoring.
    """
    # Eligibility gates override score
    if eligibility == "fail":
        return "Do not pursue (eligibility)"
    if eligibility == "unclear":
        return "Review (eligibility unclear)"

    # Score-based recommendations
    if weighted_score >= 4.0:
        return "Strong pursue"
    elif weighted_score >= 3.0:
        return "Review"
    else:
        return "Do not pursue"


def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_rfp_screener.py <rfp_file.txt>")
        sys.exit(1)

    # Load RFP
    with open(sys.argv[1], 'r') as f:
        rfp_text = f.read()

    print("Analyzing RFP...\n")

    # Step 1: LLM parses RFP (with fallback)
    try:
        llm_result = parse_rfp(rfp_text)
    except Exception as e:
        print(f"⚠️  Claude API unavailable, using mock response for demo: {e}\n")
        llm_result = load_mock_response()

    # Step 2: Apply rules-based scoring
    weighted_score = calculate_score(llm_result)

    # Step 3: Generate recommendation
    recommendation = get_recommendation(weighted_score, llm_result["eligibility"])

    # Output results
    output = {
        "rfp_title": llm_result["rfp_title"],
        "organization": llm_result["issuing_organization"],
        "eligibility": llm_result["eligibility"],
        "eligibility_reasoning": llm_result.get("eligibility_reasoning", ""),
        "weighted_score": weighted_score,
        "recommendation": recommendation,
        "breakdown": {
            category: {
                "score": llm_result["scores"][category]["score"],
                "weight": WEIGHTS[category],
                "weighted": round(llm_result["scores"][category]["score"] * WEIGHTS[category], 2),
                "evidence": llm_result["scores"][category].get("evidence", ""),
                "reasoning": llm_result["scores"][category].get("reasoning", ""),
                "confidence": llm_result["scores"][category].get("confidence", "")
            }
            for category in WEIGHTS.keys()
        },
        "signals": llm_result["extracted_signals"]
    }

    print(json.dumps(output, indent=2))
    print(f"\n{'='*60}")
    print(f"RECOMMENDATION: {recommendation}")
    print(f"WEIGHTED SCORE: {weighted_score}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
