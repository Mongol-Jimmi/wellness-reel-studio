# Generated research candidates

- `candidate-evidence-cards.json`: machine-readable action drafts and evidence leads.
- `candidate-evidence-cards.md`: editor-facing Plain-Spoken Pebble research candidates.

Offline generation is the default and costs USD $0:

```bash
python3 src/research_pipeline.py
```

A live run requires both the private environment key and explicit quota confirmation:

```bash
python3 src/research_pipeline.py --live --confirm-quota --max-results 8
```

Every result requires full-text human review. These candidate artifacts are not publication-ready and must not be treated as medical advice.
