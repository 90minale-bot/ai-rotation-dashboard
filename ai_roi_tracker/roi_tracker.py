from keyword_lists import POSITIVE_AI_TERMS, NEUTRAL_AI_TERMS, NEGATIVE_AI_ROI_TERMS


def scan_terms(text_lower, term_dict):
    hits = []
    score = 0

    for term, weight in term_dict.items():
        if term in text_lower:
            hits.append({"term": term, "weight": weight})
            score += weight

    return hits, score


def analyze_text(text):
    text_lower = text.lower()

    positive_hits, positive_score = scan_terms(text_lower, POSITIVE_AI_TERMS)
    neutral_hits, neutral_score = scan_terms(text_lower, NEUTRAL_AI_TERMS)
    negative_hits, negative_score = scan_terms(text_lower, NEGATIVE_AI_ROI_TERMS)

    roi_risk_score = negative_score - positive_score

    phase_scores = {
        "BUILDOUT / EXPANSION": positive_score,
        "OPTIMIZATION / ROI SCRUTINY": neutral_score,
        "SLOWDOWN / ROI DISAPPOINTMENT": negative_score,
    }

    dominant_phase = max(phase_scores, key=phase_scores.get)

    if negative_score >= 8 and negative_score > positive_score:
        signal = "HIGH AI ROI RISK"
        interpretation = (
            "AI commentary shows strong signs of ROI concern, slowing capex, "
            "capacity digestion, or weakening demand."
        )
    elif negative_score >= 4 and negative_score > positive_score:
        signal = "MODERATE AI ROI RISK"
        interpretation = (
            "There are meaningful warning signs around AI ROI, spending discipline, "
            "or demand moderation."
        )
    elif positive_score >= 6 and positive_score > negative_score:
        signal = "AI SPEND MOMENTUM POSITIVE"
        interpretation = (
            "AI demand and investment language remains constructive, with limited "
            "evidence of ROI pushback."
        )
    elif neutral_score >= 4 and neutral_score >= positive_score and neutral_score >= negative_score:
        signal = "AI OPTIMIZATION PHASE"
        interpretation = (
            "Language suggests the market may be shifting from raw AI buildout toward "
            "ROI measurement, utilization, efficiency, and production deployment."
        )
    else:
        signal = "NEUTRAL / MIXED"
        interpretation = (
            "AI commentary is balanced or not strong enough to confirm a clear phase."
        )

    return {
        "signal": signal,
        "interpretation": interpretation,
        "roi_risk_score": roi_risk_score,
        "dominant_phase": dominant_phase,
        "phase_scores": phase_scores,
        "positive_score": positive_score,
        "neutral_score": neutral_score,
        "negative_score": negative_score,
        "positive_hits": positive_hits,
        "neutral_hits": neutral_hits,
        "negative_hits": negative_hits,
    }


def main():
    print("Paste AI commentary / earnings text below.")
    print("Press Enter twice when finished.\n")

    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)

    text = "\n".join(lines)
    result = analyze_text(text)

    print("\n=== AI ROI Tracker Result ===")
    print(f"Signal: {result['signal']}")
    print(f"Dominant Phase: {result['dominant_phase']}")
    print(f"Interpretation: {result['interpretation']}")
    print(f"ROI Risk Score: {result['roi_risk_score']}")
    print(f"Buildout Score: {result['positive_score']}")
    print(f"Optimization Score: {result['neutral_score']}")
    print(f"Slowdown Score: {result['negative_score']}")
    print(f"Positive Hits: {result['positive_hits']}")
    print(f"Neutral Hits: {result['neutral_hits']}")
    print(f"Negative Hits: {result['negative_hits']}")


if __name__ == "__main__":
    main()