#!/usr/bin/env python3
"""
Streamlit GUI for OpenAI Metadata Generator

Run with: streamlit run app.py
"""

import os
import json
import streamlit as st
from pathlib import Path

from generate_metadata import (
    fetch_dpid_jsonld,
    fetch_dpid_tree,
    parse_dpid_content,
    generate_metadata_with_openai,
    format_file_size,
    DPIDContent,
    GeneratedMetadata
)

# Page config
st.set_page_config(
    page_title="dPID Metadata Generator",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: #e94560;
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        color: #a0a0a0;
        margin-top: 0.5rem;
    }
    
    /* Card styling */
    .metadata-card {
        background: #1a1a2e;
        border: 1px solid #2a2a4e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .metadata-card h3 {
        color: #e94560;
        margin-top: 0;
        font-size: 1.1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .metadata-card p {
        color: #d0d0d0;
        line-height: 1.6;
    }
    
    /* Keyword tags */
    .keyword-tag {
        display: inline-block;
        background: #0f3460;
        color: #e94560;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        margin: 0.2rem;
        font-size: 0.85rem;
        border: 1px solid #e94560;
    }
    
    /* Stats boxes */
    .stat-box {
        background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #2a2a4e;
    }
    .stat-box .number {
        font-size: 2rem;
        font-weight: bold;
        color: #e94560;
    }
    .stat-box .label {
        color: #a0a0a0;
        font-size: 0.9rem;
    }
    
    /* Extension table */
    .ext-table {
        width: 100%;
        border-collapse: collapse;
    }
    .ext-table td {
        padding: 0.5rem;
        border-bottom: 1px solid #2a2a4e;
    }
    .ext-table .ext-name {
        color: #e94560;
        font-family: monospace;
    }
    .ext-table .ext-count {
        color: #a0a0a0;
        text-align: right;
    }
    
    /* Progress styling */
    .stProgress > div > div > div > div {
        background-color: #e94560;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>🔬 dPID Metadata Generator</h1>
        <p>Generate FAIR-compliant metadata for DeSci research objects using AI</p>
    </div>
    """, unsafe_allow_html=True)


def render_stats(content: DPIDContent):
    """Render statistics about the dPID."""
    cols = st.columns(4)
    
    with cols[0]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="number">{content.total_files}</div>
            <div class="label">Total Files</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="number">{format_file_size(content.total_size)}</div>
            <div class="label">Total Size</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="number">{len(content.authors)}</div>
            <div class="label">Authors</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"""
        <div class="stat-box">
            <div class="number">{len(content.extensions_summary)}</div>
            <div class="label">File Types</div>
        </div>
        """, unsafe_allow_html=True)


def render_keywords(keywords: list):
    """Render keywords as tags."""
    tags_html = "".join([f'<span class="keyword-tag">{kw}</span>' for kw in keywords])
    st.markdown(tags_html, unsafe_allow_html=True)


def render_metadata_card(icon: str, title: str, content: str):
    """Render a metadata card."""
    st.markdown(f"""
    <div class="metadata-card">
        <h3>{icon} {title}</h3>
        <p>{content}</p>
    </div>
    """, unsafe_allow_html=True)


def render_extension_chart(extensions: dict):
    """Render file extension distribution."""
    import pandas as pd
    
    # Sort and limit to top 10
    sorted_exts = sorted(extensions.items(), key=lambda x: -x[1])[:10]
    
    if sorted_exts:
        df = pd.DataFrame(sorted_exts, columns=['Extension', 'Count'])
        st.bar_chart(df.set_index('Extension'))


def main():
    render_header()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.environ.get('OPENAI_API_KEY', ''),
            help="Your OpenAI API key"
        )
        
        model = st.selectbox(
            "Model",
            ["gpt-5", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            index=0,
            help="OpenAI model to use"
        )
        
        base_url = st.text_input(
            "Resolver URL",
            value="https://beta.dpid.org",
            help="dPID resolver base URL"
        )
        
        st.markdown("---")
        st.markdown("""
        ### 📖 About
        
        This tool uses OpenAI to analyze dPID research objects 
        and generate comprehensive FAIR-compliant metadata.
        
        **Features:**
        - Automatic abstract generation
        - Keyword extraction
        - Subject classification
        - Methodology inference
        """)
    
    # Main input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        dpid = st.number_input(
            "Enter dPID Number",
            min_value=1,
            max_value=10000,
            value=46,
            step=1,
            help="The dPID number to analyze"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("🚀 Generate Metadata", type="primary", use_container_width=True)
    
    # Generate metadata
    if generate_btn:
        if not api_key:
            st.error("⚠️ Please enter your OpenAI API key in the sidebar")
            return
        
        # Progress container
        progress_container = st.empty()
        status_container = st.empty()
        
        try:
            # Step 1: Fetch JSON-LD
            with progress_container:
                st.progress(0.25, text="Fetching JSON-LD metadata...")
            
            jsonld = fetch_dpid_jsonld(dpid, base_url)
            if not jsonld:
                st.error("❌ Failed to fetch JSON-LD metadata")
                return
            
            # Step 2: Fetch file tree
            with progress_container:
                st.progress(0.50, text="Fetching file tree...")
            
            tree = fetch_dpid_tree(dpid, base_url)
            if not tree:
                st.error("❌ Failed to fetch file tree")
                return
            
            # Step 3: Parse content
            with progress_container:
                st.progress(0.75, text="Analyzing content...")
            
            content = parse_dpid_content(dpid, jsonld, tree)
            
            # Step 4: Generate with OpenAI
            with progress_container:
                st.progress(0.90, text=f"Generating metadata with {model}...")
            
            metadata = generate_metadata_with_openai(content, api_key, model)
            
            # Clear progress
            progress_container.empty()
            status_container.empty()
            
            # Store in session state
            st.session_state['content'] = content
            st.session_state['metadata'] = metadata
            
            st.success("✅ Metadata generated successfully!")
            
        except Exception as e:
            progress_container.empty()
            st.error(f"❌ Error: {str(e)}")
            return
    
    # Display results if available
    if 'metadata' in st.session_state and 'content' in st.session_state:
        content = st.session_state['content']
        metadata = st.session_state['metadata']
        
        st.markdown("---")
        
        # Original info section
        st.markdown("## 📋 Original Information")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Title:** {content.title}")
            st.markdown(f"**URL:** [{content.url}]({content.url})")
            st.markdown(f"**License:** {content.license or 'Not specified'}")
            
            # Authors
            author_names = [a.get('name', a.get('id', 'Unknown')) for a in content.authors[:10]]
            if author_names:
                st.markdown(f"**Authors:** {', '.join(author_names)}")
        
        with col2:
            render_stats(content)
        
        # File type distribution
        st.markdown("### 📁 File Type Distribution")
        render_extension_chart(content.extensions_summary)
        
        st.markdown("---")
        
        # Generated metadata section
        st.markdown("## 🤖 AI-Generated Metadata")
        
        # Suggested title
        if metadata.suggested_title:
            render_metadata_card("📝", "Suggested Title", metadata.suggested_title)
        
        # Abstract
        if metadata.abstract:
            render_metadata_card("📄", "Abstract", metadata.abstract)
        
        # Two column layout for keywords and subjects
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏷️ Keywords")
            if metadata.keywords:
                render_keywords(metadata.keywords)
            else:
                st.markdown("*No keywords generated*")
        
        with col2:
            st.markdown("### 📚 Subjects")
            if metadata.subjects:
                render_keywords(metadata.subjects)
            else:
                st.markdown("*No subjects identified*")
        
        # Data types and methodology
        col1, col2 = st.columns(2)
        
        with col1:
            if metadata.data_types:
                render_metadata_card("📊", "Data Types", ", ".join(metadata.data_types))
        
        with col2:
            if metadata.methodology:
                render_metadata_card("🔬", "Methodology", metadata.methodology)
        
        # Potential reuse
        if metadata.potential_uses:
            render_metadata_card("🔄", "Potential Reuse", metadata.potential_uses)
        
        st.markdown("---")
        
        # JSON output
        st.markdown("## 📦 RO-Crate Integration")
        
        rocrate_example = {
            "@context": "https://w3id.org/ro/crate/1.1/context",
            "@id": "./",
            "@type": "Dataset",
            "name": metadata.suggested_title or content.title,
            "description": metadata.abstract,
            "keywords": metadata.keywords,
            "about": [{"@type": "DefinedTerm", "name": s} for s in metadata.subjects]
        }
        
        st.json(rocrate_example)
        
        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            metadata_json = json.dumps({
                "dpid": metadata.dpid,
                "original_title": metadata.original_title,
                "suggested_title": metadata.suggested_title,
                "abstract": metadata.abstract,
                "keywords": metadata.keywords,
                "subjects": metadata.subjects,
                "data_types": metadata.data_types,
                "methodology": metadata.methodology,
                "potential_uses": metadata.potential_uses,
                "model_used": metadata.model_used,
                "generated_at": metadata.generated_at
            }, indent=2)
            
            st.download_button(
                "📥 Download Metadata JSON",
                metadata_json,
                file_name=f"dpid_{content.dpid}_metadata.json",
                mime="application/json"
            )
        
        with col2:
            st.download_button(
                "📥 Download RO-Crate Snippet",
                json.dumps(rocrate_example, indent=2),
                file_name=f"dpid_{content.dpid}_rocrate.json",
                mime="application/json"
            )


if __name__ == "__main__":
    main()

