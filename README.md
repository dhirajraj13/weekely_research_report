# Weekly Research Report Generator

An AI-powered automation script that aggregates RSS feeds from top chemistry journals and uses the Gemini API to filter and summarize publications matching specific research interests (e.g., Non-Adiabatic Molecular Dynamics, Excited-State Methods, and AI in materials science).

## Features

- **Broad Coverage:** Fetches recent articles from arXiv, Nature, Science, ACS journals, RSC, Wiley, and more via RSS and CrossRef.
- **Smart Filtering:** Uses Gemini 2.5 Flash to ruthlessly filter out noise and only keep papers relevant to specialized target domains.
- **Markdown Summaries:** Automatically generates clean, highly readable Markdown reports outlining the paper's main results, computational methodology, and scientific importance.
- **Deduplication:** Prevents the same article from showing up multiple times.

## Prerequisites

- Python 3.8+
- A Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dhirajraj13/weekely_research_report.git
   cd weekely_research_report
   ```

2. Install the required dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. Set your Gemini API key as an environment variable:
   ```bash
   export GEMINI_API_KEY='your-api-key-here'
   ```

## Usage

Simply run the script:
```bash
python daily_report.py
```

The script will fetch the last 7 days of publications, filter them, and output a markdown file named `Report_YYYY-MM-DD.md` in the same directory.

## Customization Tips
To make this tool work for your specific research, you should modify two key areas in daily_report.py:

Journal Sources: Navigate to the section labeled # 2. Define Your Journal Sources (RSS Feeds). Update the dictionary with the RSS links for the specific journals you follow (e.g., JCTC, JCP, or specific arXiv categories).

Research Focus: Modify the section labeled # 4. The Highly Specific Filtering Prompt. Change the research keywords and interests to match your domain (e.g., if you are moving from Excited-State Methods to Surface Chemistry).

## Future Scope & Roadmap

- **v1.1.0 (Upcoming):** Automate the execution using GitHub Actions to run daily at 8:00 AM and commit the markdown report automatically.
- **v1.2.0:** Move the target topics and journal lists to an external `config.yaml` file so users don't have to edit the Python script directly.
- **v1.3.0:** Add an option to dispatch the generated markdown report directly via email (SMTP).
- **v2.0.0:** Implement a local Vector DB to store historical reports and allow RAG (Retrieval-Augmented Generation) queries against past literature.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT
