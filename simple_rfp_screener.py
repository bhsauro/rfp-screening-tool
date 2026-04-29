#!/usr/bin/env python3
"""
Simple RFP Screener - POC
Demonstrates: LLM extraction → Rules-based scoring → Recommendation
"""

import json
import sys
import os
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

# Mock response for demo/testing when API unavailable
MOCK_RESPONSE = {
    "rfp_title": "Digital Transformation Consulting Services",
    "issuing_organization": "City of Portland Public Works Department",
    "eligibility": "pass",
    "eligibility_reasoning": "All requirements met: 5+ years experience, municipal projects, certifications, insurance, Oregon registration",
    "scores": {
        "service_fit": {
            "score": 5,
            "evidence": "RFP requests digital transformation, asset management, and portal development - all core services",
            "reasoning": "Perfect alignment with our digital transformation consulting expertise",
            "confidence": "high"
        },
        "strategic_fit": {
            "score": 4,
            "evidence": "Public sector client in target geography (West Coast), infrastructure focus aligns with strategy",
            "reasoning": "Strong strategic fit - municipal infrastructure is a key vertical",
            "confidence": "high"
        },
        "win_likelihood": {
            "score": 4,
            "evidence": "We have 3 similar municipal projects completed, strong references available",
            "reasoning": "Good competitive position with relevant experience",
            "confidence": "medium"
        },
        "deadline_feasibility": {
            "score": 4,
            "evidence": "6 weeks until deadline, standard proposal requirements",
            "reasoning": "Sufficient time to prepare quality proposal",
            "confidence": "high"
        },
        "proposal_effort": {
            "score": 3,
            "evidence": "Standard RFP format, no unusual requirements, can leverage past proposals",
            "reasoning": "Moderate effort - some customization needed but manageable",
            "confidence": "medium"
        },
        "revenue_value": {
            "score": 4,
            "evidence": "$450K-$650K budget range",
            "reasoning": "Solid revenue opportunity in target range",
            "confidence": "high"
        }
    },
    "extracted_signals": {
        "deadline": "June 1, 2026",
        "budget": "$450,000 - $650,000",
        "required_services": ["Digital transformation assessment", "Asset management systems", "Citizen portals", "Change management", "Training"]
    }
}

# Prompt for Claude
PROMPT = """Analyze this RFP and return ONLY valid JSON (no markdown, no code blocks).

Score each category 1-5 where:
- 1 = very poor, 5 = excellent
- For "proposal_effort": 5 = low effort, 1 = high effort (inverse)

For each score, provide:
- evidence: Specific facts from the RFP that support this score
- reasoning: Why those facts lead to this score
- confidence: low | medium | high (how certain are you of this assessment)

Evaluation guidance:

Use the following criteria when scoring:

- service_fit: How well the RFP requirements match typical workflow automation, data integration, and proposal support capabilities
- strategic_fit: Alignment with target sectors, clients, or types of work (e.g., operational efficiency, process improvement)
- win_likelihood: Evidence of relevant experience, clear differentiation, or existing relationships
- deadline_feasibility: Whether the timeline allows for a strong proposal given typical effort required
- proposal_effort: Estimated level of effort required to complete the proposal (5 = minimal effort, 1 = very high effort)
- revenue_value: Whether the opportunity appears financially meaningful based on scope or implied budget

If information is missing or unclear, make a reasonable estimate and lower confidence.

Return this exact structure:
{
  "rfp_title": "...",
  "issuing_organization": "...",
  "eligibility": "pass | fail | unclear",
  "eligibility_reasoning": "...",
  "scores": {
    "service_fit": {
      "score": 1-5,
      "evidence": "...",
      "reasoning": "...",
      "confidence": "low | medium | high"
    },
    "strategic_fit": {
      "score": 1-5,
      "evidence": "...",
      "reasoning": "...",
      "confidence": "low | medium | high"
    },
    "win_likelihood": {
      "score": 1-5,
      "evidence": "...",
      "reasoning": "...",
      "confidence": "low | medium | high"
    },
    "deadline_feasibility": {
      "score": 1-5,
      "evidence": "...",
      "reasoning": "...",
      "confidence": "low | medium | high"
    },
    "proposal_effort": {
      "score": 1-5,
      "evidence": "...",
      "reasoning": "...",
      "confidence": "low | medium | high"
    },
    "revenue_value": {
      "score": 1-5,
      "evidence": "...",
      "reasoning": "...",
      "confidence": "low | medium | high"
    }
  },
  "extracted_signals": {
    "deadline": "...",
    "budget": "...",
    "required_services": []
  }
}

RFP to analyze:
"""


def parse_rfp(rfp_text):
    """Use Claude to parse RFP and extract structured data."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",  # Update this to working model
        max_tokens=3000,
        temperature=0,
        messages=[{"role": "user", "content": PROMPT + rfp_text}]
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
    """Apply rules-based scoring using weights."""

    # Eligibility gate
    if llm_result["eligibility"] == "fail":
        return None
    if llm_result["eligibility"] == "unclear":
        return None

    # Calculate weighted score with validation
    total = 0
    for category, weight in WEIGHTS.items():
        score = llm_result["scores"][category]["score"]
        validated_score = validate_score(score, category)
        total += validated_score * weight

    return round(total, 2)


def get_recommendation(weighted_score, eligibility):
    """Determine recommendation based on score and eligibility."""

    if eligibility == "fail":
        return "Do not pursue"
    if eligibility == "unclear":
        return "Review"

    if weighted_score is None:
        return "Review"

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
        llm_result = MOCK_RESPONSE

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
