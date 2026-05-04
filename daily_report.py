import os
import re
import sys
import warnings
from email.utils import parsedate_to_datetime
from html import unescape
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent
REQUIREMENTS_PATH = SCRIPT_DIR / "requirements.txt"


def exit_missing_dependency(package_name):
    print(
        f"Missing dependency: {package_name}\n"
        "Install the required packages in your active environment with:\n"
        f"  python3 -m pip install -r {REQUIREMENTS_PATH}"
    )
    sys.exit(1)


try:
    import feedparser
    import requests
except ModuleNotFoundError as exc:
    exit_missing_dependency(exc.name)

# 1. Configure the AI Brain
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print(
        "Missing GEMINI_API_KEY environment variable.\n"
        "Set it before running, for example:\n"
        "  export GEMINI_API_KEY='your-api-key'"
    )
    sys.exit(1)

try:
    from google import genai
except (ImportError, ModuleNotFoundError):
    exit_missing_dependency("google-genai")

# Using Flash because it is fast, cost-effective, and handles large text contexts well.
client = genai.Client(api_key=api_key)
model_name = "gemini-2.5-flash"

# 2. Define Your Journal Sources (RSS Feeds)
# Note: Journal RSS URLs can occasionally change, but these represent the standard structure.
rss_urls = {
    "arXiv (Chem-Ph)": "http://export.arxiv.org/rss/physics.chem-ph",
    "Nature": "https://www.nature.com/nature.rss",
    "Science": "https://www.science.org/rss/news_and_notes.xml", # Broad feed; AI will filter
    "JCTC (ACS)": "https://feeds.feedburner.com/acs/jctcce",
    "JPC A (ACS)": "https://feeds.feedburner.com/acs/jpcafh",
    "JPC Lett (ACS)": "https://feeds.feedburner.com/acs/jpclcd",
    "JACS (ACS)": "https://feeds.feedburner.com/acs/jacsat",
    "JPC B (ACS)": "https://feeds.feedburner.com/acs/jpcbfk",
    "JPC C (ACS)": "https://feeds.feedburner.com/acs/jpccck",
    "Biochemistry (ACS)": "https://feeds.feedburner.com/acs/bichaw",
    "PNAS": "https://www.pnas.org/action/showFeed?jc=pnas&type=etoc&feed=rss",
    "Nature Communications": "https://www.nature.com/ncomms.rss",
    "Joule (Cell Press)": "https://www.cell.com/joule/current.rss",
    "Soft Matter (RSC)": "http://feeds.rsc.org/rss/sm",
    "Molecular Physics (T&F)": "https://www.tandfonline.com/action/showFeed?jc=tmph20&type=etoc&feed=rss",
    "Adv. Optical Materials": "https://onlinelibrary.wiley.com/action/showFeed?jc=21951071&type=etoc&feed=rss",
}

crossref_journals = {
    "JCP (AIP)": "1089-7690",
    "Annual Review of Phys Chem": "1545-1593",
}
# Set the date range for filtering papers. Default is the most recent 7 days.
daily_abstracts = ""
today = datetime.today().strftime('%Y-%m-%d')
today_date = datetime.today().date()
lookback_days = 7
cutoff_date = today_date - timedelta(days=lookback_days - 1)
max_entries_per_source = 500


def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return " ".join(text.split())


def parse_rss_entry_date(entry):
    if entry.get("published_parsed"):
        t = entry.published_parsed
        return datetime(t.tm_year, t.tm_mon, t.tm_mday).date()
    if entry.get("updated_parsed"):
        t = entry.updated_parsed
        return datetime(t.tm_year, t.tm_mon, t.tm_mday).date()

    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).date()
        except Exception:
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
            except Exception:
                continue
    return None


def parse_crossref_item_date(item):
    for key in ("published-online", "issued", "published-print", "created"):
        date_parts = item.get(key, {}).get("date-parts", [])
        if not date_parts or not date_parts[0]:
            continue
        parts = date_parts[0]
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        try:
            return datetime(year, month, day).date()
        except ValueError:
            continue
    return None


def parse_feed_date(feed):
    feed_updated = getattr(feed, "feed", {}).get("updated")
    if not feed_updated:
        return None
    try:
        return parsedate_to_datetime(feed_updated).date()
    except Exception:
        return None


def append_abstract(source_name, title, summary, link, pub_date=None):
    date_text = pub_date.isoformat() if pub_date else "Unknown"
    return (
        f"Source: {source_name}\n"
        f"Published: {date_text}\n"
        f"Title: {title}\n"
        f"Abstract: {summary}\n"
        f"Link: {link}\n\n"
    )

# 3. Fetch the Data
seen_items = set()
for source_name, url in rss_urls.items():
    try:
        feed = feedparser.parse(url)
        feed_date = parse_feed_date(feed)
        # Scan deeper into each source so same-week papers are not missed.
        for entry in feed.entries[:max_entries_per_source]:
            entry_date = parse_rss_entry_date(entry)
            if entry_date:
                if entry_date < cutoff_date:
                    continue
            elif not feed_date or feed_date < cutoff_date:
                continue
            title = entry.get("title", "Untitled")
            summary = entry.get("summary", "No abstract available.")
            link = entry.get("link", url)
            dedupe_key = (source_name, link, title.strip().lower())
            if dedupe_key in seen_items:
                continue
            seen_items.add(dedupe_key)
            daily_abstracts += append_abstract(source_name, title, summary, link, entry_date)
    except Exception:
        continue

for source_name, issn in crossref_journals.items():
    try:
        crossref_url = (
            f"https://api.crossref.org/journals/{issn}/works"
            f"?filter=from-pub-date:{cutoff_date}"
            f"&sort=published&order=desc&rows={max_entries_per_source}"
        )
        response = requests.get(
            crossref_url,
            headers={"User-Agent": "daily-report/1.0 (mailto:research@example.com)"},
            timeout=20,
        )
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
        for item in items:
            item_date = parse_crossref_item_date(item)
            if not item_date or item_date < cutoff_date:
                continue
            title = clean_text(item.get("title", ["Untitled"])[0])
            summary = clean_text(item.get("abstract", "No abstract available."))
            link = item.get("URL") or item.get("resource", {}).get("primary", {}).get("URL") or crossref_url
            dedupe_key = (source_name, link, title.strip().lower())
            if dedupe_key in seen_items:
                continue
            seen_items.add(dedupe_key)
            daily_abstracts += append_abstract(source_name, title, summary, link, item_date)
    except Exception:
        continue

if not daily_abstracts.strip():
    print(
        f"No entries found in the last {lookback_days} days "
        f"({cutoff_date} to {today_date}). Check feeds or widen the window."
    )
    sys.exit(1)

# 4. The Highly Specific Filtering Prompt
prompt = f"""
You are a senior theoretical/computational chemistry researcher specializing in nonadiabatic dynamics, excited-state methods, decoherence theory, and AI-assisted quantum chemistry literature analysis. Your task is to review the following list of recent journal publications and filter them strictly based on the user's research interests.

TARGET TOPICS-:
A) Primary PRIORITY:
- Non-Adiabatic Molecular Dynamics (NAMD) [topics can be : Decoherence-Corrected Dynamics, Ab Initio Multiple Spawning (AIMS), etc]
- Conical intersections
- Ehrenfest dynamics
- Decoherence-corrected Ehrenfest dynamics -: TAB-DMS (to-a-block dense-manifold-of-states)
- Decoherence concepts in quantum systems
- Attosecond physics and electron dynamics
- Real-Time TD-DFT

B)SECONDARY PRIORITY:
- Quantum dots
- Nanoscale Excited State Dynamics [on topics: Hot-Carrier Cooling, Solar Energy Conversion, Metal Clusters]
- Full Configuration Interaction (FCI)
- GPU-Accelerated Quantum Chemistry
- Machine Learning (ML) and AI applications applied specifically to the above theoretical chemistry fields.


INSTRUCTIONS:
1. Read all provided abstracts.
2. Keep ONLY papers whose `Published` date falls in the last {lookback_days} days ({cutoff_date} to {today_date}).
3. If `Published` is `Unknown`, include it when the abstract indicates it belongs to TARGET TOPICS.
4. Discard ANY paper that does not explicitly deal with the TARGET TOPICS. Be ruthless. 
5. Ignore general biology, astronomy, or unrelated except from theoretical, computational, or AI/ML for materials science.
6. For the papers that DO match, create a cleanly formatted Markdown report.
7. If NO papers match today, simply output: "No relevant papers published today in the target domains."

FORMAT FOR EACH MATCHING PAPER:
## [Title of the Paper]

- **Journal/Source:** [Source]
- **Publication Date:** [Date]
- **Key keywords:** [e.g., NAMD, ML, Conical Intersection]
- **Main results:** [Pointwise summary of the paper's central findings and results.(at least 5-6 points)]
- **Computational methodology and framework:** [Explicitly mention:
- Electronic structure level
- Dynamics scheme
- Number of states
- Basis set (if available)
- Software
- ML architecture (if used)]
- **Why it is interesting or important:** [Very brief pointwise explanation of the scientific significance, especially for the target topics.]
- **Link:** [URL]
-State whether this paper is:
    - Incremental
    - Moderate advance
    - Significant methodological advance
    - Landmark / must follow
---

ABSTRACTS TO REVIEW:
{daily_abstracts}
"""

# 5. Process with AI and Generate Report
try:
    response = client.models.generate_content(model=model_name, contents=prompt)
    daily_report = response.text
except Exception as exc:
    print(f"Gemini analysis failed: {exc}")
    sys.exit(1)

# 6. Save or Display the Report
filename = f"Report_{today}.md"
output_path = SCRIPT_DIR / filename
with open(output_path, "w") as file:
    file.write(daily_report)
