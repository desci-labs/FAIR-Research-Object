#!/usr/bin/env python3
"""
OpenAI-powered Metadata Generator for dPID Research Objects

This script fetches dPID content and uses OpenAI's API to generate
proper FAIR-compliant metadata including:
- Title optimization
- Description/abstract
- Keywords
- Subject classification
- Data type identification
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import defaultdict

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


@dataclass
class FileInfo:
    """Information about a single file in the dPID."""
    name: str
    path: str
    size: int
    extension: str
    cid: Optional[str] = None


@dataclass 
class DPIDContent:
    """All content information for a dPID."""
    dpid: int
    title: str
    url: str
    license: Optional[str] = None
    authors: List[Dict[str, str]] = field(default_factory=list)
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    components: List[Dict[str, Any]] = field(default_factory=list)
    files: List[FileInfo] = field(default_factory=list)
    extensions_summary: Dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    total_size: int = 0


@dataclass
class GeneratedMetadata:
    """AI-generated metadata for a dPID."""
    dpid: int
    original_title: str
    suggested_title: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    subjects: List[str] = field(default_factory=list)
    data_types: List[str] = field(default_factory=list)
    methodology: Optional[str] = None
    potential_uses: Optional[str] = None
    raw_response: Optional[str] = None
    model_used: str = ""
    generated_at: str = ""


def extract_files_from_tree(entry: dict, path_prefix: str = "") -> List[FileInfo]:
    """Extract file information from the file tree."""
    files = []
    
    name = entry.get('name', '')
    current_path = f"{path_prefix}/{name}" if path_prefix else name
    
    if entry.get('type') == 'file':
        # Extract extension
        if '.' in name:
            ext = '.' + name.rsplit('.', 1)[1].lower()
        else:
            ext = '(no extension)'
        
        files.append(FileInfo(
            name=name,
            path=current_path,
            size=entry.get('size', 0),
            extension=ext,
            cid=entry.get('cid')
        ))
    
    # Process children
    for child in entry.get('children', []):
        files.extend(extract_files_from_tree(child, current_path))
    
    return files


def fetch_dpid_jsonld(dpid: int, base_url: str = "https://beta.dpid.org") -> Optional[Dict]:
    """Fetch JSON-LD metadata for a dPID."""
    try:
        url = f"{base_url}/{dpid}?format=jsonld"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching JSON-LD for dPID {dpid}: {e}")
        return None


def fetch_dpid_tree(dpid: int, base_url: str = "https://beta.dpid.org") -> Optional[Dict]:
    """Fetch file tree for a dPID."""
    try:
        url = f"{base_url}/api/v2/data/dpid/{dpid}?depth=full"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching file tree for dPID {dpid}: {e}")
        return None


def parse_dpid_content(dpid: int, jsonld: Dict, tree: Dict) -> DPIDContent:
    """Parse dPID content from JSON-LD and file tree."""
    content = DPIDContent(dpid=dpid, title="", url=f"https://beta.dpid.org/{dpid}")
    
    # Parse JSON-LD graph
    graph = jsonld.get('@graph', [])
    
    for item in graph:
        item_id = item.get('@id', '')
        item_type = item.get('@type', '')
        
        # Main research object (root)
        if item_id == './':
            content.title = item.get('name', f'dPID {dpid}')
            content.license = item.get('license')
            content.url = item.get('url', content.url)
            
            # Extract creators/authors
            creators = item.get('creator', [])
            if not isinstance(creators, list):
                creators = [creators]
            for creator in creators:
                if isinstance(creator, dict):
                    content.authors.append({
                        'id': creator.get('@id', ''),
                        'type': 'reference'
                    })
        
        # Person entries
        elif item_type == 'Person':
            person_id = item.get('@id', '')
            name = item.get('name', '')
            # Update author entry with name
            for author in content.authors:
                if author.get('id') == person_id:
                    author['name'] = name
                    author['type'] = 'Person'
        
        # Component entries (datasets, code, papers)
        elif item_type in ['Dataset', 'SoftwareSourceCode', 'CreativeWork', 'WebSite']:
            component = {
                'id': item.get('@id', ''),
                'type': item_type,
                'name': item.get('name', ''),
                'description': item.get('description', ''),
                'keywords': item.get('keywords', ''),
                'encoding_format': item.get('encodingFormat', ''),
                'license': item.get('license', '')
            }
            if component['name'] or component['description']:
                content.components.append(component)
                
                # Collect keywords from components
                if component['keywords']:
                    kws = component['keywords']
                    if isinstance(kws, str):
                        kws = [k.strip() for k in kws.split(',')]
                    content.keywords.extend(kws)
    
    # Deduplicate keywords
    content.keywords = list(set(content.keywords))
    
    # Parse file tree
    tree_data = tree.get('tree', tree)
    files = extract_files_from_tree(tree_data)
    content.files = files
    content.total_files = len(files)
    content.total_size = sum(f.size for f in files)
    
    # Summarize extensions
    ext_counts = defaultdict(int)
    for f in files:
        ext_counts[f.extension] += 1
    content.extensions_summary = dict(ext_counts)
    
    return content


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def build_prompt(content: DPIDContent) -> str:
    """Build the prompt for OpenAI to generate metadata."""
    
    # Format authors
    author_names = []
    for author in content.authors:
        if author.get('name'):
            name = author['name']
            author_id = author.get('id', '')
            if 'orcid.org' in author_id:
                name += f" (ORCID: {author_id})"
            author_names.append(name)
    
    authors_str = ", ".join(author_names[:10])  # Limit to first 10 authors
    if len(author_names) > 10:
        authors_str += f" and {len(author_names) - 10} others"
    
    # Format file extensions summary
    ext_summary = "\n".join([
        f"  - {ext}: {count} files" 
        for ext, count in sorted(content.extensions_summary.items(), key=lambda x: -x[1])[:15]
    ])
    
    # Format components
    components_str = ""
    for i, comp in enumerate(content.components[:5], 1):  # Limit to first 5
        comp_desc = f"  {i}. {comp['name']}"
        if comp['type']:
            comp_desc += f" (type: {comp['type']})"
        if comp['description']:
            desc_preview = comp['description'][:200]
            if len(comp['description']) > 200:
                desc_preview += "..."
            comp_desc += f"\n     Description: {desc_preview}"
        if comp['keywords']:
            comp_desc += f"\n     Keywords: {comp['keywords']}"
        components_str += comp_desc + "\n"
    
    # Sample file names (first 30, focusing on unique patterns)
    sample_files = []
    seen_patterns = set()
    for f in content.files[:100]:
        # Create a pattern by removing numbers
        pattern = ''.join(c if not c.isdigit() else '#' for c in f.name)
        if pattern not in seen_patterns:
            seen_patterns.add(pattern)
            sample_files.append(f"{f.name} ({format_file_size(f.size)})")
            if len(sample_files) >= 30:
                break
    
    sample_files_str = "\n".join([f"  - {f}" for f in sample_files])
    
    prompt = f"""You are a research metadata specialist. Analyze the following research object and generate comprehensive FAIR-compliant metadata.

## Research Object Information

**dPID:** {content.dpid}
**URL:** {content.url}
**Current Title:** {content.title}
**License:** {content.license or 'Not specified'}
**Authors:** {authors_str or 'Not specified'}

**Existing Keywords:** {', '.join(content.keywords) if content.keywords else 'None provided'}

## File Contents Summary

**Total Files:** {content.total_files}
**Total Size:** {format_file_size(content.total_size)}

**File Type Distribution:**
{ext_summary}

## Components/Datasets:
{components_str if components_str else '  No named components found'}

## Sample File Names:
{sample_files_str}

---

Based on the above information, generate comprehensive metadata for this research object. Consider:
1. The file types present (e.g., .fits files suggest astronomy, .ipynb suggest computational analysis)
2. The file naming patterns (e.g., star names, coordinates, experiment IDs)
3. The component descriptions and keywords already provided
4. The overall structure and purpose of the research

Respond in the following JSON format:
{{
  "suggested_title": "An improved, descriptive title if the current one could be better, or null if the current title is good",
  "abstract": "A 100-200 word abstract describing what this research object contains, its purpose, and potential significance",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6", "keyword7", "keyword8"],
  "subjects": ["Primary research field", "Secondary field if applicable"],
  "data_types": ["Type of data contained, e.g., 'Astronomical observations', 'Simulation results', 'Code repository'"],
  "methodology": "Brief description of methods used based on file contents (e.g., 'ALMA telescope observations processed with CASA pipeline')",
  "potential_uses": "How this data could be reused by other researchers"
}}

Ensure all fields are populated based on the evidence available. If uncertain about something, make reasonable inferences from the file names and types."""

    return prompt


def generate_metadata_with_openai(
    content: DPIDContent, 
    api_key: str,
    model: str = "gpt-5"
) -> GeneratedMetadata:
    """Use OpenAI to generate metadata for a dPID."""
    
    client = OpenAI(api_key=api_key)
    
    prompt = build_prompt(content)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a research metadata specialist who generates FAIR-compliant metadata for research objects. Always respond with valid JSON."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=1,
            response_format={"type": "json_object"}
        )
        
        raw_response = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from response")
        
        return GeneratedMetadata(
            dpid=content.dpid,
            original_title=content.title,
            suggested_title=parsed.get('suggested_title'),
            abstract=parsed.get('abstract'),
            keywords=parsed.get('keywords', []),
            subjects=parsed.get('subjects', []),
            data_types=parsed.get('data_types', []),
            methodology=parsed.get('methodology'),
            potential_uses=parsed.get('potential_uses'),
            raw_response=raw_response,
            model_used=model,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise


def save_results(
    content: DPIDContent, 
    metadata: GeneratedMetadata, 
    output_dir: Path
):
    """Save the results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the raw content info
    content_file = output_dir / f"dpid_{content.dpid}_content.json"
    content_data = asdict(content)
    # Convert FileInfo objects to dicts
    content_data['files'] = [asdict(f) for f in content.files[:100]]  # Limit stored files
    with open(content_file, 'w') as f:
        json.dump(content_data, f, indent=2)
    
    # Save the generated metadata
    metadata_file = output_dir / f"dpid_{content.dpid}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(asdict(metadata), f, indent=2)
    
    # Save a human-readable report
    report_file = output_dir / f"dpid_{content.dpid}_report.md"
    report = generate_report(content, metadata)
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nResults saved to:")
    print(f"  - Content: {content_file}")
    print(f"  - Metadata: {metadata_file}")
    print(f"  - Report: {report_file}")


def generate_rocrate_example(content: DPIDContent, metadata: GeneratedMetadata) -> str:
    """Generate an example RO-Crate JSON snippet."""
    example = {
        "name": metadata.suggested_title or content.title,
        "description": (metadata.abstract or '')[:100] + "...",
        "keywords": metadata.keywords,
        "about": [{"@type": "DefinedTerm", "name": s} for s in metadata.subjects]
    }
    return json.dumps(example, indent=2)


def generate_report(content: DPIDContent, metadata: GeneratedMetadata) -> str:
    """Generate a human-readable markdown report."""
    
    # Format authors
    author_names = [a.get('name', a.get('id', 'Unknown')) for a in content.authors[:10]]
    
    report = f"""# AI-Generated Metadata Report for dPID {content.dpid}

**Generated:** {metadata.generated_at}  
**Model:** {metadata.model_used}  
**URL:** {content.url}

---

## Original Information

| Field | Value |
|-------|-------|
| **Title** | {content.title} |
| **Authors** | {', '.join(author_names) if author_names else 'Not specified'} |
| **License** | {content.license or 'Not specified'} |
| **Total Files** | {content.total_files} |
| **Total Size** | {format_file_size(content.total_size)} |

### File Type Distribution

| Extension | Count |
|-----------|-------|
"""
    for ext, count in sorted(content.extensions_summary.items(), key=lambda x: -x[1])[:10]:
        report += f"| {ext} | {count} |\n"

    report += f"""
### Existing Keywords
{', '.join(content.keywords) if content.keywords else 'None provided'}

---

## AI-Generated Metadata

### Suggested Title
{metadata.suggested_title if metadata.suggested_title else '_Current title is appropriate_'}

### Abstract
{metadata.abstract or 'Not generated'}

### Keywords
{', '.join(metadata.keywords) if metadata.keywords else 'None generated'}

### Research Subjects
{', '.join(metadata.subjects) if metadata.subjects else 'Not identified'}

### Data Types
{', '.join(metadata.data_types) if metadata.data_types else 'Not identified'}

### Methodology
{metadata.methodology or 'Not identified'}

### Potential Reuse
{metadata.potential_uses or 'Not identified'}

---

## How to Use This Metadata

This metadata can be incorporated into the dPID's RO-Crate by updating the following fields:

```json
{generate_rocrate_example(content, metadata)}
```

---

*Generated by OpenAI Metadata Generator for DeSci dPIDs*
"""
    return report


def main():
    parser = argparse.ArgumentParser(
        description='Generate FAIR-compliant metadata for dPIDs using OpenAI'
    )
    parser.add_argument(
        'dpid',
        type=int,
        help='dPID number to analyze'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=os.environ.get('OPENAI_API_KEY'),
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-5',
        choices=['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        help='OpenAI model to use (default: gpt-5)'
    )
    parser.add_argument(
        '--base-url',
        type=str,
        default='https://beta.dpid.org',
        help='Base URL for dPID resolver (default: https://beta.dpid.org)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./results',
        help='Output directory for results (default: ./results)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress information'
    )
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY or use --api-key")
        sys.exit(1)
    
    print(f"=" * 60)
    print(f"OpenAI Metadata Generator for dPID {args.dpid}")
    print(f"=" * 60)
    
    # Fetch dPID data
    print(f"\n[1/4] Fetching JSON-LD metadata...")
    jsonld = fetch_dpid_jsonld(args.dpid, args.base_url)
    if not jsonld:
        print("Failed to fetch JSON-LD. Exiting.")
        sys.exit(1)
    print("  ✓ JSON-LD fetched successfully")
    
    print(f"\n[2/4] Fetching file tree...")
    tree = fetch_dpid_tree(args.dpid, args.base_url)
    if not tree:
        print("Failed to fetch file tree. Exiting.")
        sys.exit(1)
    print("  ✓ File tree fetched successfully")
    
    # Parse content
    print(f"\n[3/4] Parsing content...")
    content = parse_dpid_content(args.dpid, jsonld, tree)
    print(f"  ✓ Found {content.total_files} files ({format_file_size(content.total_size)})")
    print(f"  ✓ Title: {content.title}")
    print(f"  ✓ Authors: {len(content.authors)}")
    print(f"  ✓ Components: {len(content.components)}")
    
    if args.verbose:
        print(f"\n  File extensions:")
        for ext, count in sorted(content.extensions_summary.items(), key=lambda x: -x[1])[:10]:
            print(f"    {ext}: {count}")
    
    # Generate metadata with OpenAI
    print(f"\n[4/4] Generating metadata with OpenAI ({args.model})...")
    try:
        metadata = generate_metadata_with_openai(content, args.api_key, args.model)
        print("  ✓ Metadata generated successfully")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        sys.exit(1)
    
    # Display results
    print(f"\n" + "=" * 60)
    print("GENERATED METADATA")
    print("=" * 60)
    
    if metadata.suggested_title:
        print(f"\n📝 Suggested Title:")
        print(f"   {metadata.suggested_title}")
    
    print(f"\n📄 Abstract:")
    print(f"   {metadata.abstract}")
    
    print(f"\n🏷️  Keywords:")
    print(f"   {', '.join(metadata.keywords)}")
    
    print(f"\n📚 Subjects:")
    print(f"   {', '.join(metadata.subjects)}")
    
    print(f"\n📊 Data Types:")
    print(f"   {', '.join(metadata.data_types)}")
    
    if metadata.methodology:
        print(f"\n🔬 Methodology:")
        print(f"   {metadata.methodology}")
    
    if metadata.potential_uses:
        print(f"\n🔄 Potential Reuse:")
        print(f"   {metadata.potential_uses}")
    
    # Save results
    output_dir = Path(args.output_dir)
    save_results(content, metadata, output_dir)
    
    print(f"\n" + "=" * 60)
    print("Done!")


if __name__ == '__main__':
    main()

