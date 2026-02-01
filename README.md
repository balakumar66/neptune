# Neptune 🌊

A web-based tool to extract section titles and content from websites, with AI-powered categorization and smart filtering.

## Architecture

```mermaid
flowchart LR
    subgraph Input
        URL[/"URL(s)"/]
    end

    subgraph Scraper["🔍 Scraper"]
        FETCH[Fetch HTML]
        PARSE[Parse Headings<br/>h1-h6]
        EXTRACT[Extract Content<br/>under each heading]
    end

    subgraph AI["🤖 OpenAI Categorizer"]
        PROMPT["Send to GPT-4o-mini:<br/><i>'Categorize this section...'</i>"]
        CATEGORY["Returns category:<br/>Products, About, FAQ, etc."]
    end

    subgraph Filter["🧹 Cleaner"]
        REMOVE["Remove boilerplate:<br/>• Related Products<br/>• Footer/Nav<br/>• Copyright"]
        MINWORDS[Filter by word count]
    end

    subgraph Output
        CSV[/"CSV / Excel"/]
    end

    URL --> FETCH --> PARSE --> EXTRACT
    EXTRACT --> PROMPT --> CATEGORY
    CATEGORY --> REMOVE --> MINWORDS --> CSV

    style Input fill:#e1f5fe
    style Output fill:#e8f5e9
    style AI fill:#fff3e0
```

### Data Flow Example

```mermaid
flowchart TB
    subgraph "1️⃣ Scraper Output"
        S1["<b>Section 1</b><br/>Title: 'CPTC 110-1350W'<br/>Content: 'Professional tile cutter...'"]
        S2["<b>Section 2</b><br/>Title: 'Key Specifications'<br/>Content: 'Power: 1350W, RPM: 12000...'"]
        S3["<b>Section 3</b><br/>Title: 'Related Products'<br/>Content: 'CB1 Blower, CPAG 22...'"]
        S4["<b>Section 4</b><br/>Title: 'Copyright'<br/>Content: '© 2026 All Rights Reserved'"]
    end

    subgraph "2️⃣ After AI Categorization"
        C1["✅ Products/Services"]
        C2["✅ Products/Services"]
        C3["⚠️ Navigation/Menu"]
        C4["⚠️ Legal/Terms"]
    end

    subgraph "3️⃣ After Filtering"
        F1["✅ CPTC 110-1350W<br/><i>Products/Services</i>"]
        F2["✅ Key Specifications<br/><i>Products/Services</i>"]
        F3["❌ Filtered out"]
        F4["❌ Filtered out"]
    end

    S1 --> C1 --> F1
    S2 --> C2 --> F2
    S3 --> C3 --> F3
    S4 --> C4 --> F4

    style F1 fill:#c8e6c9
    style F2 fill:#c8e6c9
    style F3 fill:#ffcdd2
    style F4 fill:#ffcdd2
```

## Features

- **Web Interface** - Easy-to-use Streamlit UI for scraping websites
- **Section Extraction** - Extract all headings (h1-h6) and their content from webpages
- **AI Categorization** - Automatically categorize sections using OpenAI (Products, About, Contact, etc.)
- **Smart Filtering** - Remove boilerplate content like "Related Products", footers, navigation
- **Customizable Filters** - Edit YAML config to add/remove filter rules
- **Multiple Export Formats** - Download results as CSV or formatted Excel
- **Grid Layout Support** - Handles modern websites with content in separate columns

## Quick Start

### Option 1: Deploy to Railway (Recommended)

1. Fork this repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select the `deploy/railway` branch
4. Add environment variable: `OPENAI_API_KEY`
5. Generate a domain and you're live!

### Option 2: Run Locally

```bash
# Clone and setup
git clone https://github.com/balakumar66/neptune.git
cd neptune
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the app
streamlit run src/app.py
```

## Usage

### Web Interface

1. Open the app in your browser (default: http://localhost:8501)
2. Enter URLs (one per line)
3. Click "Start Extraction"
4. Download results as CSV or Excel

### Command Line (Advanced)

```bash
python src/main.py --input data/urls.csv --output data/output.csv --categorize
```

## Configuration

### Filter Customization

Edit `config/filters.yaml` to customize what content gets filtered:

```yaml
# Minimum words required for a section
min_word_count: 5

# Section titles to exclude (case-insensitive)
excluded_section_titles:
  - "related products"
  - "you may also like"
  - "footer"
  # Add your own...

# Keywords that indicate boilerplate
boilerplate_keywords:
  - "copyright"
  - "privacy policy"
  # Add your own...
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI categorization |

## Output Format

The exported CSV/Excel contains:

| Column | Description |
|--------|-------------|
| `row_no` | Row number for reference |
| `url` | Source URL |
| `page_title` | Page title from `<title>` tag |
| `description` | Page meta description |
| `section_title` | Heading text |
| `section_level` | Heading level (h1-h6) |
| `content` | Text content under that section |
| `ai_category` | AI-assigned category |

## Project Structure

```
neptune/
├── config/
│   └── filters.yaml      # Customizable filter rules
├── src/
│   ├── app.py            # Streamlit web interface
│   ├── scraper.py        # Web scraping logic
│   ├── categorizer.py    # AI categorization
│   ├── cleaner.py        # Data filtering
│   └── main.py           # CLI interface
├── Procfile              # Railway deployment
├── railway.json          # Railway config
└── requirements.txt
```

## Deployment

### Railway

The `deploy/railway` branch is configured for Railway deployment:

- Auto-deploys on push
- Uses Nixpacks builder
- Health checks enabled

### Streamlit Community Cloud

Also compatible with Streamlit Cloud - just point to `src/app.py`.

## License

MIT
