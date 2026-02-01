#!/usr/bin/env python3
"""
Neptune - Web UI for Website Content Extractor

Streamlit-based web interface for scraping and categorizing website content.
"""

import streamlit as st
import pandas as pd
import re
import time
from urllib.parse import urlparse
from io import BytesIO
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import WebScraper, Section
from categorizer import AICategorizer
from cleaner import filter_dataframe, get_filter_summary


# Custom CSS for professional styling
CUSTOM_CSS = """
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Centered header */
    .header-container {
        text-align: center;
        padding: 1rem 0;
    }
    .header-container h1 {
        margin-bottom: 0.25rem;
    }
    .header-container p {
        color: #666;
        font-size: 1.1rem;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #1e3a5f;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #6c757d;
        padding: 1rem;
        font-size: 0.85rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hide deploy button */
    .stDeployButton {display: none;}
    [data-testid="stToolbar"] {display: none;}
</style>
"""

# JavaScript to scroll to results
SCROLL_TO_RESULTS = """
<script>
    window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
</script>
"""


def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    url = url.strip()
    if not url:
        return False
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False
        if '.' not in result.netloc:
            return False
        domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?'
            r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*'
            r'\.[a-zA-Z]{2,}$'
        )
        domain = result.netloc.split(':')[0]
        if not domain_pattern.match(domain):
            return False
        return True
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize URL by adding scheme if missing."""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def sections_to_dataframe(sections: list) -> pd.DataFrame:
    """Convert Section objects to DataFrame."""
    data = []
    for section in sections:
        data.append({
            'url': section.url,
            'page_title': getattr(section, 'page_title', '') or '',
            'description': getattr(section, 'meta_description', '') or '',
            'canonical_url': getattr(section, 'canonical_url', '') or '',
            'section_title': section.section_title,
            'section_level': section.section_level,
            'content': section.content,
            'ai_category': section.category or ''
        })
    return pd.DataFrame(data)


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        'results_df': None,
        'original_count': 0,
        'urls_processed': 0,
        'enable_filtering': True,
        'extraction_complete': False,
        'url_input': ''
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_results():
    """Clear all results from session state."""
    st.session_state.results_df = None
    st.session_state.original_count = 0
    st.session_state.urls_processed = 0
    st.session_state.extraction_complete = False


def main():
    st.set_page_config(
        page_title="Neptune - Website Content Extractor",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Header (centered)
    st.markdown(
        """
        <div class='header-container'>
            <h1>🌊 Neptune</h1>
            <p>Extract and categorize website content with AI</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Clear button (right-aligned)
    if st.session_state.results_df is not None:
        col1, col2, col3 = st.columns([5, 1, 5])
        with col2:
            if st.button("🗑️ Clear", help="Clear results and start over", use_container_width=True):
                clear_results()
                st.rerun()
    
    st.divider()
    
    # URL input section
    st.markdown("#### 📝 Enter URLs")
    url_input = st.text_area(
        "URLs to scrape",
        value=st.session_state.url_input,
        height=150,
        placeholder="https://example.com\nhttps://another-site.com/page",
        help="Enter one URL per line",
        label_visibility="collapsed"
    )
    st.session_state.url_input = url_input
    
    # Filtering is always enabled
    enable_filtering = True
    
    # Parse and validate URLs
    urls_raw = [line.strip() for line in url_input.strip().split('\n') if line.strip()]
    valid_urls = []
    invalid_urls = []
    
    for url in urls_raw:
        if is_valid_url(url):
            valid_urls.append(normalize_url(url))
        else:
            invalid_urls.append(url)
    
    # URL validation feedback (compact)
    if urls_raw:
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if valid_urls:
                st.success(f"✓ {len(valid_urls)} valid")
        with col2:
            if invalid_urls:
                st.error(f"✗ {len(invalid_urls)} invalid")
        with col3:
            if invalid_urls:
                with st.expander("Show invalid URLs"):
                    for url in invalid_urls:
                        st.code(url, language=None)
    
    # Submit button
    st.markdown("")  # Spacing
    col_btn, col_space = st.columns([1, 3])
    with col_btn:
        submit_clicked = st.button(
            "🚀 Extract Content",
            type="primary",
            disabled=len(valid_urls) == 0,
            use_container_width=True
        )
    
    # Processing
    if submit_clicked and valid_urls:
        # Clear previous results
        clear_results()
        
        # Initialize components
        scraper = WebScraper(timeout=30, delay=1.0)
        categorizer = AICategorizer()
        all_sections = []
        
        # Progress container
        st.markdown("---")
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Phase 1: Scraping
            status_text.info("🔍 **Phase 1/3:** Extracting content from websites...")
            
            for i, url in enumerate(valid_urls):
                progress = (i + 1) / len(valid_urls) * 0.5
                progress_bar.progress(progress)
                
                try:
                    sections = scraper.scrape_url(url)
                    all_sections.extend(sections)
                except Exception as e:
                    st.warning(f"Failed: {url[:50]}...")
                
                if i < len(valid_urls) - 1:
                    time.sleep(1.0)
            
            # Phase 2: Categorization
            status_text.info("🤖 **Phase 2/3:** AI Categorization...")
            progress_bar.progress(0.7)
            
            if all_sections and categorizer:
                all_sections = categorizer.categorize_sections(all_sections)
            
            # Phase 3: Convert and filter
            progress_bar.progress(0.85)
            df = sections_to_dataframe(all_sections)
            original_count = len(df)
            
            if enable_filtering and len(df) > 0:
                status_text.info("🧹 **Phase 3/3:** Cleaning data...")
                df = filter_dataframe(df)
            
            progress_bar.progress(1.0)
            status_text.success("✅ **Extraction complete!**")
            
            # Store results
            st.session_state.results_df = df
            st.session_state.original_count = original_count
            st.session_state.urls_processed = len(valid_urls)
            st.session_state.extraction_complete = True
            
            # Auto-scroll to results
            st.markdown(SCROLL_TO_RESULTS, unsafe_allow_html=True)
    
    # Results display (persisted via session state)
    if st.session_state.results_df is not None:
        df = st.session_state.results_df
        
        if len(df) > 0:
            st.markdown("---")
            st.markdown("### 📊 Results")
            
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("URLs", st.session_state.urls_processed)
            with col2:
                st.metric("Sections Found", st.session_state.original_count)
            with col3:
                st.metric("After Filtering", len(df))
            with col4:
                reduction = round((1 - len(df) / st.session_state.original_count) * 100) if st.session_state.original_count > 0 else 0
                st.metric("Noise Reduced", f"{reduction}%")
            
            # Data preview
            st.markdown("#### 📄 Data Preview")
            
            st.dataframe(
                df,
                use_container_width=True,
                height=400,
                column_config={
                    "url": st.column_config.TextColumn("URL", width="medium"),
                    "page_title": st.column_config.TextColumn("Page Title", width="medium"),
                    "description": st.column_config.TextColumn("Description", width="medium"),
                    "canonical_url": st.column_config.TextColumn("Canonical URL", width="small"),
                    "section_title": st.column_config.TextColumn("Section Title", width="medium"),
                    "section_level": st.column_config.TextColumn("Level", width="small"),
                    "content": st.column_config.TextColumn("Content", width="large"),
                    "ai_category": st.column_config.TextColumn("Category", width="small"),
                }
            )
            
            # Download section
            st.markdown("#### 💾 Download")
            
            # Prepare export data
            export_df = df.copy()
            export_df.insert(0, 'row_no', range(1, len(export_df) + 1))
            if 'content' in export_df.columns:
                export_df['content'] = export_df['content'].apply(
                    lambda x: str(x).replace('\n', ' ').strip() if pd.notna(x) else ''
                )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                csv_data = export_df.to_csv(index=False)
                st.download_button(
                    label="📥 CSV",
                    data=csv_data,
                    file_name="neptune_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='Sections')
                    workbook = writer.book
                    worksheet = writer.sheets['Sections']
                    
                    from openpyxl.styles import PatternFill, Font
                    
                    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                    header_font = Font(bold=True, color='FFFFFF')
                    
                    for cell in worksheet[1]:
                        cell.fill = header_fill
                        cell.font = header_font
                    
                    worksheet.freeze_panes = 'A2'
                    worksheet.auto_filter.ref = worksheet.dimensions
                
                st.download_button(
                    label="📥 Excel",
                    data=excel_buffer.getvalue(),
                    file_name="neptune_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        elif st.session_state.extraction_complete:
            st.warning("No content was extracted from the provided URLs.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div class='footer'>
            Neptune • Website Content Extractor
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
