# Simple RFP Screener - POC

Proof of concept: LLM extraction → Rules-based scoring → Automated recommendation

## What It Does

1. **LLM parses RFP** - Claude extracts structured signals and scores 6 criteria
2. **Rules-based scoring** - Applies weighted rubric to calculate priority score
3. **Recommendation** - Outputs "Strong pursue" / "Review" / "Do not pursue"

## Setup

```bash
# Install dependencies
pip install anthropic python-dotenv

# Add API key to .env file
echo 'ANTHROPIC_API_KEY="your-key"' > .env
```

## Usage

```bash
python simple_rfp_screener.py sample_rfps/sample_rfp_1_strong_fit.txt
```

## How It Works

### Scoring Criteria (Weighted)

- **Service fit** (30%) - Does RFP match what we offer?
- **Win likelihood** (20%) - Do we have competitive advantage?
- **Deadline feasibility** (15%) - Can we submit quality proposal in time?
- **Strategic fit** (15%) - Right buyer/sector/geography?
- **Revenue value** (10%) - Financially meaningful?
- **Proposal effort** (10%) - Low effort relative to value? (inverse score)

### Decision Logic

```
Eligibility = fail → "Do not pursue"
Eligibility = unclear → "Review"
Score ≥ 4.0 → "Strong pursue"
Score 3.0-3.9 → "Review"
Score < 3.0 → "Do not pursue"
```

## Output Example

```json
{
  "rfp_title": "Digital Transformation Consulting",
  "weighted_score": 4.35,
  "recommendation": "Strong pursue",
  "breakdown": {
    "service_fit": {
      "score": 5,
      "weight": 0.30,
      "weighted": 1.5,
      "reasoning": "Perfect match for our digital transformation services"
    },
    ...
  }
}
```

## Files

- `simple_rfp_screener.py` - Main script (~150 lines)
- `sample_rfps/` - Test RFPs
- `.env` - API key (create this)

That's it!
