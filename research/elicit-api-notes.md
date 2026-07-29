# Elicit API Integration Notes

Primary source: [Elicit API Reference](https://docs.elicit.com/), OpenAPI 3.1.0 / API version 2.0.0, checked for this implementation.

## Current contract

- Base URL: `https://elicit.com/api/v2`
- Paper search: `POST /search/papers`
- Authentication: `Authorization: Bearer <key>`
- Local environment variable used here: `ELICIT_API_KEY`
- API access requires an eligible paid plan (the current docs say Pro or above).
- Global limit: 100 requests per minute per IP. Exceeding it returns 429 and blocks the IP for five minutes.
- Result cap depends on plan; this project intentionally caps requests at 50 papers and defaults to 8.
- Filters used: minimum year, study-type tags, and `retracted: exclude_retracted`.
- Elicit returns paper metadata including title, authors, year, abstract, DOI, PMID, venue, citation count, and URLs.

## Implementation boundary

`src/elicit_client.py` performs paper discovery. `src/research_pipeline.py` combines those evidence leads with separately curated, low-risk action steps for the Plain-Spoken Pebble identity.

The software deliberately does **not**:

- infer clinical quality from Elicit ranking, citations, venue, or abstracts;
- claim a search result proves an intervention works;
- turn paper abstracts directly into medical advice;
- publish cards automatically;
- log or persist the API key.

Every generated card remains `human_review_required`. Full text, study population, comparator, outcomes, harms, uncertainty, retraction status, and applicability must be reviewed before publication.

## Safe local setup

```bash
read -rsp "Elicit API key: " ELICIT_API_KEY
printf '\n'
export ELICIT_API_KEY
python3 src/research_pipeline.py --live --confirm-quota --max-results 8
```

Do not paste the key into chat, source files, command arguments, screenshots, or committed `.env` files.

## Cost gate

Offline generation is the default, uses no API calls, and costs USD $0. A live run requires both `--live` and `--confirm-quota`; the default topic set then performs six paper-search requests. Topics are deduplicated and a twelve-request ceiling is enforced. The exact monetary impact depends on the user’s Elicit plan and must be checked in Elicit account settings before a live run.

## Sources

- API reference and schemas: https://docs.elicit.com/
- API keys/account settings: https://elicit.com/settings
- API terms: https://elicit.com/operations/api-terms
- Official examples: https://github.com/elicit/api-examples
