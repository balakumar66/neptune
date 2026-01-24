# Neptune - Website Content Extractor

A Python tool to extract section titles and content from websites, with AI-powered categorization.

## Features

- Read URLs from CSV file
- Extract section headings (h1-h6) and their content from each webpage
- AI-powered categorization to normalize sections into common themes
- Export results to CSV or Excel

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key (optional, for AI categorization)
```

## Usage

### Basic Usage (Console)

```bash
python src/main.py --input data/urls.csv --output data/output.csv
```

### With AI Categorization

```bash
python src/main.py --input data/urls.csv --output data/output.csv --categorize
```

### Input CSV Format

Your input CSV should have a column named `url`:

```csv
url
https://example.com
https://another-site.com/page
```

## Output

The output CSV/Excel will contain:
- `url`: Source URL
- `section_title`: The heading text
- `section_level`: Heading level (h1-h6)
- `content`: Text content under that section
- `category` (if AI categorization enabled): Normalized category name
