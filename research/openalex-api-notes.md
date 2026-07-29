# Research: Current OpenAlex API notes (evidence discovery)

**Primary-source basis (checked 2026-02-27):** OpenAlex developer documentation, including the official API reference and guides. Exact URLs are listed below. This note intentionally does not rely on third-party tutorials.

## Summary
OpenAlex is a scholarly-metadata discovery API. Current documentation describes a free API key, a $1/day free budget, metered endpoint classes, and a 100 requests/second ceiling; `mailto` is no longer the current “polite pool” mechanism. For a small pipeline, use narrow, reproducible `/works` searches plus filters, cursor pagination, field selection, DOI/OA/retraction capture, and conservative retries. OpenAlex discovers papers and metadata; it does **not** establish clinical quality, and an abstract must never be converted directly into medical advice.

## Findings

1. **Authentication, allowance, and pricing.** The current authentication page says data and snapshots remain free, while the API is freemium. A free account supplies an API key (create account and retrieve it at `https://openalex.org/settings/api`); the key is passed as `api_key`. The documented free key budget is **$1/day** (reset midnight UTC). Without a key the documented trial allowance is **$0.10/day**, but use a key for the intended pipeline and for current at-scale access; do not depend on the old `mailto` polite pool. [Authentication & pricing](https://developers.openalex.org/api-reference/authentication) [Deprecations (historical polite pool)](https://developers.openalex.org/guides/deprecations)

2. **Endpoint costs and free daily equivalents.** Documented cost per 1,000 calls: singleton lookup **free**; list+filter **$0.10**; keyword search **$1**; semantic search **$1**; content download **$10**. The free-key examples quantify approximately 10,000 list/filter calls/day, 1,000 search calls/day, and 100 content downloads/day (singleton lookups unlimited). A `/works?search=...` request is a search-class call, whereas a filter-only `/works` request is list+filter. `meta.cost_usd` and `meta.count` allow estimating pagination cost before traversing a result set. [Authentication & pricing](https://developers.openalex.org/api-reference/authentication)

3. **Rate limits and status endpoint.** The docs state that exceeding the daily budget or making more than **100 requests/second** produces `429 Too Many Requests`. Responses expose `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Credits-Used`, and `X-RateLimit-Reset` (seconds until reset). `GET https://api.openalex.org/rate-limit?api_key=...` reports budget, usage, remaining amount, reset time, endpoint costs, and credits. A small client should throttle well below 100 RPS, inspect headers, persist usage/logs, and stop rather than accidentally spending beyond the daily budget (unless paid/prepaid use is explicitly intended). [Authentication & pricing](https://developers.openalex.org/api-reference/authentication) [Check rate-limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status)

4. **`/works` search.** `GET https://api.openalex.org/works` with `search` searches work `title`, `abstract`, and `fulltext`; stemming and stop-word removal apply. Uppercase `AND`, `OR`, `NOT`, quoted phrases, proximity (`"..."~N`), exact/unstemmed `search.exact`, wildcards, and limited fuzzy syntax are documented. Search results default to relevance ordering and include `relevance_score`; relevance combines text similarity and citation count, so it is a discovery ranking—not evidence quality. Long Boolean URLs are limited to about 4 KB; split large OR vocabularies and union IDs client-side. [Searching](https://developers.openalex.org/guides/searching)

5. **Filters, sorting, and field selection.** Use comma-separated filters for AND, `|` for OR, `!` for NOT, and numeric inequalities such as `cited_by_count:>100`; works filters include `publication_year`, `type`, `open_access.is_oa`, `has_abstract`, DOI, and many more. Use `sort=publication_date:desc`, `sort=cited_by_count:desc`, or (only with search) `sort=relevance_score:desc`; multiple sort keys are comma-separated. `select=id,doi,display_name,...` restricts response fields, but selection is **root-level only** (e.g. `select=open_access.is_oa` is invalid; select `open_access`). [Filtering](https://developers.openalex.org/guides/filtering) [Sorting](https://developers.openalex.org/guides/sort) [Selecting fields](https://developers.openalex.org/guides/selecting-fields)

6. **Paging limits.** `per_page` defaults to 25 and accepts 1–100. Basic paging uses `page` (documented range 1–500), and the basic paging limit is 10,000 results. For larger sets, start with `cursor=*`, then send the returned `meta.next_cursor` until it is `null` and results are empty. Use `per_page=100` to reduce calls. [Page through results](https://developers.openalex.org/guides/page-through-results) [Authentication & pricing (limits)](https://developers.openalex.org/api-reference/authentication)

7. **Response metadata.** List responses have `meta` plus `results` (and sometimes `group_by`). Relevant `meta` fields are `count`, `db_response_time_ms`, `page`, `per_page`, `next_cursor`, `groups_count`, and `cost_usd`. Store query parameters and the metadata with each run so discovery is reproducible and cost/pagination can be audited. [List works / response schema](https://developers.openalex.org/api-reference/works/list-works) [API introduction / response format](https://developers.openalex.org/api-reference/introduction)

8. **Abstract reconstruction.** Work records expose `abstract_inverted_index`, a mapping from token to a list of integer positions (rather than plaintext). Reconstruct by placing each token at every listed position and joining tokens by ascending position; absent indexes mean no abstract was supplied. This restores tokenized text for triage, not a guaranteed publisher-faithful abstract (spacing, punctuation, and tokenization are not recoverable perfectly). Official schema: [Get a single work](https://developers.openalex.org/api-reference/works/get-a-single-work); official docs repository example/schema: [work-object README](https://github.com/ourresearch/openalex-docs/blob/main/api-entities/works/work-object/README.md).

```python
def reconstruct_abstract(index):
    if not index:
        return None
    by_position = {}
    for token, positions in index.items():
        for position in positions:
            by_position[position] = token
    return " ".join(by_position[p] for p in sorted(by_position))
```

9. **DOI and open-access fields.** Capture `id`, `doi`, `ids.doi`, `display_name`, publication date/year, type, `is_retracted`, `abstract_inverted_index`, `open_access`, `best_oa_location`, `primary_location`, and `locations`. `open_access` includes `is_oa`, `oa_url`, and `any_repository_has_fulltext`; location objects include `is_oa`, landing/PDF URLs, license fields, and publication/accepted indicators. OA is an access/availability signal, **not** peer-review or clinical-quality evidence. [Work schema](https://developers.openalex.org/api-reference/works/get-a-single-work)

10. **Errors and handling.** Official error guidance maps 400 to invalid query/filter, 301 to merged entity (follow redirect), 403 to rate-limit forbidden, 404 to missing entity, 429 to daily limit exceeded, and 500 to server error. Set a 30-second timeout, log status/body/request parameters, inspect rate headers, and exponential-backoff transient 429/5xx responses (e.g. 1, 2, 4, 8 seconds with jitter and a cap). Do not blindly retry 400/404; treat 403 as a stop-and-diagnose condition. [Error handling](https://developers.openalex.org/api-reference/errors)

## Minimal keyed Python request

Never put a literal secret in source, logs, or this document. OpenAlex documents the query-parameter form; `requests` URL-encodes it. For production, redact the key from logged URLs.

```python
import os
import requests

api_key = os.environ["OPENALEX_API_KEY"]
params = {
    "api_key": api_key,
    "search": '"stress management" AND wellbeing',
    "filter": "type:article,publication_year:2020-2026,has_abstract:true",
    "sort": "relevance_score:desc",
    "select": "id,doi,display_name,publication_date,is_retracted,open_access,best_oa_location,abstract_inverted_index",
    "per_page": 25,
    "cursor": "*",
}
r = requests.get("https://api.openalex.org/works", params=params, timeout=30)
r.raise_for_status()
payload = r.json()
print(payload["meta"]["count"], payload["meta"]["next_cursor"])
```

## Conservative methodology for mental-wellness evidence discovery

* Define a scope that is non-diagnostic and general (e.g. stress, sleep, physical activity, social connection, mindfulness, journaling, relaxation, and help-seeking), and pre-register inclusion/exclusion terms, date range, languages, and population.
* Run several short, conceptually distinct searches rather than one broad query: (a) behavior/intervention + wellbeing/stress, (b) systematic review/meta-analysis terms, (c) randomized/controlled/effectiveness terms, and (d) emerging developments with a recent-year filter. Keep a query ledger, date, filters, cursor, selected fields, and returned count.
* Prefer high-recall discovery first; deduplicate by normalized DOI, then OpenAlex ID. Retain DOI and OA URLs for human verification. Exclude or flag `is_retracted`; do not infer study validity from citations, relevance score, OA status, or OpenAlex topic labels.
* Triage title/abstract only into evidence categories (review/meta-analysis, randomized trial, longitudinal/observational, qualitative, protocol, commentary). Require human review of full text and methods before claims. Record sample, comparator, outcome, effect/uncertainty, follow-up, harms, limitations, conflicts, and whether the population matches.
* Treat “novel” as recently indexed/published and potentially promising—not effective. Verify novelty, publication status, retractions, and independent replication in the paper and authoritative sources. Separate association from causation.
* Present results as evidence leads and uncertainty, with neutral, low-risk language. Do not diagnose, prescribe, promise outcomes, or turn an abstract into medical advice; advise professional/emergency support where appropriate. OpenAlex discovers papers but does not establish clinical quality or safety.

## Sources

- Kept: [Authentication & pricing](https://developers.openalex.org/api-reference/authentication) — current key, allowance, endpoint costs, limits, headers.
- Kept: [List works](https://developers.openalex.org/api-reference/works/list-works) — `/works` schema and list response.
- Kept: [Searching](https://developers.openalex.org/guides/searching) — searchable fields and query syntax.
- Kept: [Filtering](https://developers.openalex.org/guides/filtering) — filter logic and works fields.
- Kept: [Sorting](https://developers.openalex.org/guides/sort) — sortable fields/directions.
- Kept: [Selecting fields](https://developers.openalex.org/guides/selecting-fields) — root-level `select` behavior.
- Kept: [Page through results](https://developers.openalex.org/guides/page-through-results) — page/cursor constraints.
- Kept: [Get a single work](https://developers.openalex.org/api-reference/works/get-a-single-work) — DOI, OA, abstract-index schema.
- Kept: [Errors](https://developers.openalex.org/api-reference/errors) — status codes and retry guidance.
- Kept: [Rate-limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status) — usage endpoint schema.
- Kept: [Official docs repository work object](https://github.com/ourresearch/openalex-docs/blob/main/api-entities/works/work-object/README.md) — primary repository schema context.

## Gaps

The official schema describes the inverted index but does not provide a canonical punctuation/whitespace reconstruction helper; the function above is positional token reconstruction and should be treated as approximate text. Exact clinical-quality appraisal, full-text access, and medical guidance are outside OpenAlex and require human expert review and appropriate clinical/public-health sources.

## Supervisor coordination
No blocking decision was needed.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Primary-source OpenAlex findings, exact URLs, methodology, and keyed Python request written to the authoritative artifact path."
    }
  ],
  "changedFiles": [
    "/home/willem/wellness-brand-lab/.pi-subagents/artifacts/outputs/cc270ffa-bbce-4b8e-a53e-4025411eba24/research.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [],
  "validationOutput": [
    "Artifact contains authentication/pricing, endpoint costs, limits, works behavior, metadata, abstract reconstruction, DOI/OA fields, errors, methodology, and environment-key example."
  ],
  "residualRisks": [
    "OpenAlex docs do not define a canonical punctuation-preserving abstract reconstruction helper.",
    "API policy and pricing can change; recheck official docs before deployment."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added the requested primary-source OpenAlex API research brief as the sole artifact.",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Runtime instruction required the artifact path above; no other project files were edited."
}
```