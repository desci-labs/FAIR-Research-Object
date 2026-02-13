# OpenAI Metadata Generator for dPID Research Objects

This demo uses OpenAI's API to automatically generate FAIR-compliant metadata for dPIDs (decentralized Persistent Identifiers) on the DeSci network.

## What It Does

Given a dPID number, the script:

1. **Fetches** the dPID's JSON-LD metadata and complete file tree
2. **Analyzes** the content structure, file types, and existing metadata
3. **Generates** comprehensive metadata using OpenAI including:
   - Improved title suggestions
   - Abstract/description
   - Keywords
   - Subject classifications
   - Data type identification
   - Methodology inference
   - Potential reuse descriptions

## Installation

```bash
cd openai_metadata_demo
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Generate metadata for a dPID
python generate_metadata.py 46
```

### Options

```bash
python generate_metadata.py <dpid> [options]

Arguments:
  dpid                  dPID number to analyze

Options:
  --api-key KEY         OpenAI API key (or use OPENAI_API_KEY env var)
  --model MODEL         Model to use: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo
                        (default: gpt-4o-mini)
  --base-url URL        dPID resolver URL (default: https://beta.dpid.org)
  --output-dir DIR      Output directory (default: ./results)
  --verbose             Print detailed progress
```

### Examples

```bash
# Use a specific model
python generate_metadata.py 46 --model gpt-4o

# Use dev environment
python generate_metadata.py 46 --base-url https://dev.dpid.org

# Verbose output
python generate_metadata.py 46 --verbose

# Specify output directory
python generate_metadata.py 46 --output-dir ./my_results
```

## Output Files

For each dPID, three files are generated in the output directory:

1. **`dpid_<N>_content.json`** - Raw content analysis including:
   - Title, authors, license
   - File list with sizes and extensions
   - Extension distribution summary
   - Component descriptions

2. **`dpid_<N>_metadata.json`** - AI-generated metadata:
   - Suggested title
   - Abstract
   - Keywords
   - Subjects
   - Data types
   - Methodology
   - Potential uses
   - Raw API response

3. **`dpid_<N>_report.md`** - Human-readable markdown report

## Example Output

```
============================================================
OpenAI Metadata Generator for dPID 46
============================================================

[1/4] Fetching JSON-LD metadata...
  ✓ JSON-LD fetched successfully

[2/4] Fetching file tree...
  ✓ File tree fetched successfully

[3/4] Parsing content...
  ✓ Found 786 files (263.8 MB)
  ✓ Title: Exploring Lupus Clouds
  ✓ Authors: 17
  ✓ Components: 4

[4/4] Generating metadata with OpenAI (gpt-4o-mini)...
  ✓ Metadata generated successfully

============================================================
GENERATED METADATA
============================================================

📄 Abstract:
   This research object contains ALMA telescope observations and analysis 
   of protoplanetary disks in the Lupus star-forming region...

🏷️  Keywords:
   ALMA, protoplanetary disks, Lupus, star formation, astronomy, dust, gas...

📚 Subjects:
   Astrophysics, Planetary Science

📊 Data Types:
   Astronomical observations, Reduced data products, Analysis code
```

## How It Works

### Information Extracted

The script extracts comprehensive information from each dPID:

| Source | Information |
|--------|-------------|
| JSON-LD | Title, authors, license, component descriptions, keywords |
| File Tree | All filenames, sizes, extensions, directory structure |
| Inference | File type patterns, naming conventions, content types |

### Prompt Engineering

The OpenAI prompt is carefully constructed to include:
- All available metadata
- File extension distribution (e.g., 536 .fits files → astronomy)
- Sample file names (reveals naming patterns like star coordinates)
- Component descriptions
- Existing keywords

### Model Selection

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| gpt-4o-mini | Fast | Good | $ |
| gpt-4o | Medium | Excellent | $$$ |
| gpt-4-turbo | Medium | Excellent | $$$ |
| gpt-3.5-turbo | Fast | Acceptable | $ |

## Integration with RO-Crate

The generated metadata can be incorporated into the dPID's RO-Crate:

```json
{
  "@context": "https://w3id.org/ro/crate/1.1/context",
  "@id": "./",
  "@type": "Dataset",
  "name": "<suggested_title>",
  "description": "<abstract>",
  "keywords": "<keywords>",
  "about": [
    {"@type": "DefinedTerm", "name": "<subject>"}
  ]
}
```

## Cost Estimation

Using gpt-4o-mini (recommended):
- Typical dPID: ~2000 input tokens, ~500 output tokens
- Cost per dPID: ~$0.001 (less than a tenth of a cent)
- 1000 dPIDs: ~$1.00

## Future Improvements

- [ ] Batch processing multiple dPIDs
- [ ] PDF/image content analysis for richer descriptions
- [ ] Automatic RO-Crate update functionality
- [ ] Fine-tuned model for scientific metadata
- [ ] Integration with DeSci Nodes for direct updates

## License

MIT License - See parent project for details.

