import argparse
import html
import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from elicit_client import ConfigurationError, ElicitApiError, ElicitClient, Paper


@dataclass(frozen=True)
class Topic:
    slug: str
    pebble_label: str
    category: str
    search_query: str
    action_steps: tuple[str, ...]
    safety_boundary: str
    guidance_sources: tuple[str, ...]


TOPICS = {
    topic.slug: topic
    for topic in (
        Topic(
            "sensory-grounding",
            "FEET • SOUND • NOW",
            "grounding",
            "sensory grounding present moment stress anxiety systematic review",
            (
                "Feel where your feet or body meet a stable surface.",
                "Name one thing you can see, one you can hear, and one you can feel.",
                "Pause and notice whether your attention has shifted; stop if this feels worse.",
            ),
            "This is an optional grounding prompt, not medical treatment for derealization or dissociation.",
            (
                "https://news.va.gov/104529/live-whole-health-125-grounding-exercise-and-connecting-with-our-senses/",
                "https://www.nhs.uk/mental-health/conditions/dissociative-disorders/",
            ),
        ),
        Topic(
            "gentle-breathing",
            "AIR • EASY • SLOW",
            "stress",
            "slow paced breathing stress anxiety systematic review meta analysis",
            (
                "Sit, stand, or lie somewhere supported.",
                "Let the breath move into your belly only as deeply as is comfortable—never force it.",
                "Breathe gently in through the nose and out through the mouth; count evenly if helpful.",
            ),
            "A short Reel can introduce the practice, but it is not an instant reset or a complete breathing session.",
            ("https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/",),
        ),
        Topic(
            "mindful-noticing",
            "NOTICE • RETURN • NOW",
            "mindfulness",
            "brief mindfulness present moment stress wellbeing systematic review",
            (
                "Choose one present sensation, such as a sound or the feeling of your hands.",
                "Notice it without deciding whether it is good or bad.",
                "When attention wanders, gently return once—no score and no failure.",
            ),
            "Mindful noticing is a general wellness practice, not a substitute for care.",
            ("https://news.va.gov/104529/live-whole-health-125-grounding-exercise-and-connecting-with-our-senses/",),
        ),
        Topic(
            "muscle-release",
            "HANDS • RELEASE • REST",
            "relaxation",
            "progressive muscle relaxation stress anxiety systematic review randomized trial",
            (
                "Pick one comfortable muscle group, such as your hands.",
                "Gently tense without straining, then release.",
                "Notice the contrast; skip injured or painful areas and stop if uncomfortable.",
            ),
            "Avoid painful areas or forceful tension; this is a brief introduction, not individualized treatment.",
            ("https://www.va.gov/WHOLEHEALTHLIBRARY/tools/progressive-muscle-relaxation.asp",),
        ),
        Topic(
            "nature-microbreak",
            "LOOK • COLOR • TEXTURE",
            "behavior",
            "brief nature exposure microbreak stress wellbeing systematic review",
            (
                "Step outside or look toward a natural view if one is available.",
                "Notice one color, one texture, and one sound.",
                "Treat any change as information, not a required outcome.",
            ),
            "This is a low-pressure wellness experiment; evidence and context still require full-text review.",
            (),
        ),
        Topic(
            "social-microconnection",
            "HELLO • LISTEN • REPLY",
            "behavior",
            "brief positive social interaction wellbeing loneliness longitudinal systematic review",
            (
                "Choose one low-pressure connection: a greeting, short message, or sincere reply.",
                "Keep the invitation easy to decline.",
                "Notice how the interaction felt without treating it as a performance score.",
            ),
            "Social connection is context-dependent; respect safety, privacy, culture, and personal boundaries.",
            ("https://www.hhs.gov/surgeongeneral/priorities/connection/index.html",),
        ),
        Topic(
            "awe-noticing",
            "WIDE • DETAIL • WONDER",
            "emerging",
            "awe intervention mental health wellbeing randomized trial systematic review",
            (
                "Notice something that feels vast, intricate, or surprising.",
                "Describe one concrete detail rather than forcing a feeling.",
                "Let the moment be neutral if awe does not appear.",
            ),
            "Treat awe as an emerging research lead, not a guaranteed mood intervention.",
            (),
        ),
        Topic(
            "psychological-flexibility",
            "NOTICE • CHOOSE • MOVE",
            "emerging",
            "psychological flexibility daily behavior wellbeing longitudinal meta analysis",
            (
                "Name the thought or feeling that is present.",
                "Name one value that matters in this moment.",
                "Choose one tiny action that can coexist with the feeling.",
            ),
            "This simplified prompt is educational and requires expert review before clinical use.",
            (),
        ),
        Topic(
            "music-check-in",
            "PLAY • NOTICE • CHOOSE",
            "behavior",
            "music listening stress regulation wellbeing systematic review",
            (
                "Choose one familiar track at a comfortable volume.",
                "Notice whether your energy shifts up, down, or not at all.",
                "Change or stop the music if it feels uncomfortable.",
            ),
            "Music responses vary; do not promise relaxation or use unsafe listening levels.",
            (),
        ),
        Topic(
            "sleep-hygiene",
            "TIME • LIGHT • CAFFEINE • ROOM",
            "sleep",
            "sleep hygiene consistent wake time caffeine screen light bedroom systematic review adults",
            (
                "Keep your wake-up time as consistent as you reasonably can.",
                "Make the hour before bed dimmer and quieter when possible.",
                "Choose one small change tonight instead of trying to fix everything at once.",
            ),
            "Sleep habits can support sleep, but persistent sleep problems or major daytime impairment deserve professional assessment.",
            (
                "https://www.cdc.gov/nchs/products/databriefs/db559.htm",
                "https://www.nhlbi.nih.gov/health/sleep-deprivation/healthy-sleep-habits",
                "https://www.nhs.uk/every-mind-matters/mental-wellbeing-tips/how-to-fall-asleep-faster-and-sleep-better/",
            ),
        ),
        Topic(
            "implementation-intentions",
            "IF • THEN • EASY",
            "psychology-tip",
            "implementation intentions habit behavior change mental health wellbeing meta analysis",
            (
                "Choose one situation you regularly encounter.",
                "Pair it with one tiny action: ‘If X happens, then I will do Y.’",
                "Make Y easy enough to try once, then revise rather than judging yourself.",
            ),
            "This is a behavior-planning prompt, not a guarantee that a habit or symptom will change.",
            (),
        ),
    )
}

DEFAULT_TOPIC_SLUGS = (
    "sensory-grounding",
    "gentle-breathing",
    "mindful-noticing",
    "muscle-release",
    "nature-microbreak",
    "awe-noticing",
)
MAX_LIVE_REQUESTS = 12


def select_topic_slugs(
    use_all: bool,
    requested: list[str] | None,
    *,
    request_budget: int = MAX_LIVE_REQUESTS,
) -> tuple[str, ...]:
    selected = tuple(TOPICS) if use_all else tuple(dict.fromkeys(requested or DEFAULT_TOPIC_SLUGS))
    if len(selected) > request_budget:
        raise ValueError(f"topic selection exceeds the {request_budget}-request budget")
    return selected


def build_evidence_card(topic: Topic, papers: tuple[Paper, ...]) -> dict:
    return {
        "topic": topic.slug,
        "brandIdentity": "Plain-Spoken Pebble",
        "pebbleLabel": topic.pebble_label,
        "category": topic.category,
        "actionSteps": list(topic.action_steps),
        "safetyBoundary": topic.safety_boundary,
        "guidanceSources": list(topic.guidance_sources),
        "researchQuery": topic.search_query,
        "evidenceLeads": [_paper_record(paper) for paper in papers],
        "publicationStatus": "human_review_required",
        "reviewChecklist": [
            "Read the full paper, not only the abstract.",
            "Check population, comparator, outcomes, harms, uncertainty, and follow-up.",
            "Separate association from causation and confirm the study is not retracted.",
            "Have a qualified reviewer approve any clinical or condition-specific wording.",
        ],
    }


def _paper_record(paper: Paper) -> dict:
    record = asdict(paper)
    record["authors"] = list(paper.authors)
    record["urls"] = list(paper.urls)
    return record


def render_markdown(cards: list[dict]) -> str:
    lines = [
        "# Plain-Spoken Pebble Research Cards",
        "",
        "> Human review required. Elicit finds evidence leads; it does not establish clinical quality or turn abstracts into medical advice.",
        "",
    ]
    for card in cards:
        lines.extend((f"## {card['pebbleLabel']}", "", f"**Topic:** `{card['topic']}`", "", "### Easy steps"))
        lines.extend(f"{index}. {_clean_text(step)}" for index, step in enumerate(card["actionSteps"], start=1))
        lines.extend(("", f"**Safety boundary:** {_clean_text(card['safetyBoundary'])}", "", "### Evidence leads"))
        if not card["evidenceLeads"]:
            lines.append("- No live papers attached yet; run the keyed Elicit search.")
        for paper in card["evidenceLeads"]:
            title = _clean_text(paper["title"])
            year = paper["year"] or "year unknown"
            url = next(iter(paper["urls"]), None)
            if url:
                lines.append(f"- [{title}]({url}) ({year})")
            else:
                lines.append(f"- {title} ({year})")
        lines.extend(("", "**Status:** Human review required before publishing.", ""))
    return "\n".join(lines)


def write_outputs(cards: list[dict], output_directory: Path) -> tuple[Path, Path]:
    cards = [_dedupe_card_evidence(card) for card in cards]
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "candidate-evidence-cards.json"
    markdown_path = output_directory / "candidate-evidence-cards.md"
    for path in (json_path, markdown_path):
        if path.exists() and not path.is_file():
            raise OSError(f"output path is not a regular file: {path}")

    temporary_paths: list[Path] = []
    try:
        temporary_json = _write_secure_temp(
            output_directory,
            json.dumps(cards, indent=2, ensure_ascii=False) + "\n",
        )
        temporary_paths.append(temporary_json)
        temporary_markdown = _write_secure_temp(output_directory, render_markdown(cards) + "\n")
        temporary_paths.append(temporary_markdown)
        temporary_json.replace(json_path)
        temporary_markdown.replace(markdown_path)
    finally:
        for path in temporary_paths:
            path.unlink(missing_ok=True)
    return json_path, markdown_path


def _dedupe_card_evidence(card: dict) -> dict:
    seen: set[str] = set()
    unique_leads = []
    for lead in card.get("evidenceLeads", []):
        key = str(lead.get("doi") or lead.get("elicit_id") or lead.get("title", "")).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        unique_leads.append(lead)
    return {**card, "evidenceLeads": unique_leads}


def _write_secure_temp(directory: Path, content: str) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=directory,
        prefix=".candidate-evidence-",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_file.write(content)
        return Path(temporary_file.name)


def _clean_text(value: object) -> str:
    text = html.escape(" ".join(str(value).split())[:500], quote=False)
    return text.replace("[", "\\[").replace("]", "\\]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build evidence-linked Plain-Spoken Pebble content cards")
    parser.add_argument("--topic", action="append", choices=sorted(TOPICS), help="Repeat to select topics")
    parser.add_argument("--all", action="store_true", help="Search every curated topic")
    parser.add_argument("--max-results", type=int, default=8, help="Papers per topic, capped at 50")
    parser.add_argument("--min-year", type=int, default=2018)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Make live Elicit requests")
    mode.add_argument("--dry-run", action="store_true", help="Explicit alias for the default offline mode")
    parser.add_argument(
        "--confirm-quota",
        action="store_true",
        help="Confirm that live requests may consume Elicit plan quota",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "research" / "generated",
    )
    args = parser.parse_args()
    cards = []
    try:
        slugs = select_topic_slugs(args.all, args.topic)
        if args.live and not args.confirm_quota:
            raise ConfigurationError("--live requires --confirm-quota before using Elicit plan quota")
        client = ElicitClient.from_environment() if args.live else None
        if client is not None:
            print(
                f"Confirmed live Elicit usage: {len(slugs)} request(s), up to {args.max_results} papers each",
                file=sys.stderr,
            )
        for slug in slugs:
            topic = TOPICS[slug]
            papers = () if client is None else client.search_papers(
                topic.search_query,
                max_results=args.max_results,
                min_year=args.min_year,
            )
            cards.append(build_evidence_card(topic, papers))
        json_path, markdown_path = write_outputs(cards, args.output_dir)
    except (ConfigurationError, ElicitApiError, ValueError, OSError) as error:
        print(f"Research build failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    print(json_path)
    print(markdown_path)


if __name__ == "__main__":
    main()
