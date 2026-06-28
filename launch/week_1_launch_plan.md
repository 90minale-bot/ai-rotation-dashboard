# Week 1 Launch Plan

## Product Name

Rotation Clock Weekly

## Positioning

A weekly, signal-backed market note for tracking AI/growth leadership, tactical value rotation, and when not to chase late rotation moves.

## Free Offer

Join the free weekly note for:

- the current 20D tactical rotation read
- the 20D signal-quality check
- the 60D rotation-extension or AI-reassertion warning
- a plain-English bottom line
- the market news that explains what changed

## Target Reader

Self-directed investors, market watchers, advisors, and AI/growth investors who want a disciplined rotation framework without receiving personalized investment advice.

## Launch Steps

1. Create a free publication on Substack or beehiiv.
2. Use the landing-page copy from `launch/landing_page_copy.md`.
3. Use the first issue template from `launch/weekly_note_template.md`.
4. Copy the publication signup URL.
5. In Streamlit Cloud, add a secret:

```toml
NEWSLETTER_SIGNUP_URL = "https://your-signup-url-here"
```

6. Redeploy or refresh the Streamlit app.
7. Publish one free weekly note for four to six weeks before launching a paid tier.

## First Paid Offer

After the free launch period:

- Free: dashboard snapshot and short interpretation
- Paid: full weekly note, signal history, model tables, and watchlist

Suggested launch price:

```text
$15/month
$149/year
```

## Compliance Notes

Use educational language:

- "The model indicates..."
- "Historically, similar setups..."
- "This is not individualized investment advice."

Avoid:

- "Buy this now"
- "Sell this now"
- guaranteed performance language
- personalized portfolio recommendations
