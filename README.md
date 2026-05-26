# Week 2: AI Pipeline & Skill Gap Analysis

## Project Overview

This project implements an AI-driven data processing pipeline to analyze job market requirements and identify skill gaps for job seekers. It uses Large Language Models (LLMs) to extract concrete technical skills from job descriptions, construct a normalized skill database, and then compare those requirements against a candidate's given resume to highlight missing technical skills.

## Setup Instructions

### Prerequisites
- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)
- Optional: [Ollama](https://ollama.com/) (if utilizing local models like `llama3.1` or `phi3`)(not recommended)
- A valid Google Gemini API key (for cloud models)

### Installation
1. Navigate to the project root directory.
2. Initialize and sync the project dependencies:
   ```bash
   uv sync
   ```

### Configuration
Create a `.env` file in the root directory to store your API credentials securely:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

The project offers three main scripts for different steps of the pipeline.

supported gemini models:

gemini-2.5-flash

gemini-2.5-flash-lite

gemini-3-flash-preview

**1. General LLM Testing**

Test plain prompts with configured models:
```bash
uv run main.py <model> <prompt>
# Example
uv run main.py "gemini-2.5-flash-lite" "What is Python?"
```

**2. Data Tagging**

to change ai model, change "MODEL_NAME" inside the top of the file

Extract technical skills from job descriptions and populate the SQLite database:
```bash
uv run tag_data.py <db_path>
```
*Expected Output*: Standard output showing parsed jobs (e.g., `Analyzed Job 1234: python, sql, aws`)

**3. Skill Gap Identification**

to change ai model, change "MODEL_NAME" inside the top of the file

Analyze a resume and compare it against the tagged database to find missing skills:
```bash
uv run find_skill_gaps.py <resume_path> <db_path>
```
*Expected Output*: Prints the difference of resume skills and job listing skills, showing missing resume skills

(e.g., `gaps=['aws', 'docker', ...]`).

---

## API / Function Reference

### `prompt_model.py`
- **`prompt_model(model: str, prompt: str) -> str`**
  - **Purpose**: A universal router for LLM prompts, delegating calls to local Ollama instances or Google Gemini API.
  - **Inputs**: `model` (target model name) and `prompt` (the query).
  - **Outputs**: Returns the generated text response or an error string safely without crashing.

### `tag_data.py`
- **`tag_data(db_url: str)`**
  - **Purpose**: Reads uncategorized job postings from the database in batches, queries the LLM to extract technical skills, validates the output, and updates the database.
  - **Inputs**: Path to the local SQLite database.
  - **Outputs**: Updates the database, also outputs the update changes.

### `find_skill_gaps.py`
- **`find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`**
  - **Purpose**: Compares extracted skills from the resume against the universe of technical skills from the database to identify skill gaps.
  - **Inputs**: Path to the resume text file, Path to the SQLite database.
  - **Outputs**: Outputs the skill gaps between the resume and database, the skill gap is a sorted list of missing technical skills.

---

## Data / Assumptions

### Data Sources
- **Database**: a SQLite database containing job details. The tool expects columns like `source_id`, `job_title`, `description`, and `tech_stack`.
- **Resume**: Plain unstructured resume text data typically contains technical skills extracted from resumes.

### Assumptions
- The database skills are correctly delimited by commas.
- The resume does not contain heavy malicious attempts beyond simple prompt injection ("ignore previous instructions").
- Extracted skills are normalized to lowercase.
- Soft skills and certifications in resume are actively excluded from analysis.

Data from inputs are parsed for error checks then processed for their use case

Ai models are used to process the data and the responses are validated

finally data from the response is processed for their intended uses

---

## Testing
- Local Ai models was tested and determined to be too slow and too inconsistent even with small amount of data to process and strict hand holding context
- Database of small amount and large amount of job listings with diverse job descriptions, including non descriptive or missing details were used to tests for errors or failures
- Online Ai models used were tested for instability by increasing the amount of data to process per request
- Formats are enforced and checked for Input data and Output data to pick up errors during processing procedure

**Highlights**
- **Extraction Validation**: `tag_data.py` relies on `parse_and_validate_response()` which asserts batch size consistency, source ID matches, and non-empty responses. Incorrect formats enforce exponential backoff retries instead of crashing.
- **Determinism Check**: `find_skill_gaps.py` forces deterministic outcomes by cross-referencing an LLM JSON extraction with strict Regex word boundaries (`\b`) against the database's known skills array.
- **Resiliency**: Defensive try-catch blocks wrap database access, prompt execution, and file I/O to ensure graceful degradation.

---

## Limitations

- **LLM Errors**: Local LLMs are heavily limited by hardware performance, resulting in inconsistent reponses and not following instructions.
- **LLM Rate Limiting**: Online LLMs are Rate Limited daily, resulting in requests being bundled in batches to the rate of request.
- **Extraction Blindspots**: Regex boundary constraints heavily rely on the LLM spelling the output correctly. Small aliasing anomalies (e.g. `node.js` vs `nodejs`) might count as missing skills even if present.
- **Prompt Injection**: Basic injection sanitization is present via `.replace()`, but dedicated adversarial resume documents could hypothetically corrupt the LLM extraction logic.

---

## Architecture Reflection

### Design Choices
- **Decoupled Inference Layer**: `prompt_model.py` keeps API details completely decoupled from the logic layers (`tag_data` and `find_gap`), allowing models to be hot-swapped for benchmarking.
- **Hybrid Matching Model**: Relying on the LLM entirely for exact keyword mapping sometimes generated hallucinations. Utilizing the LLM for abstraction and complementing it with strict Regex ensures maximum determinism.

### Trade-offs
- **Speed vs Accuracy**: Batching prompts in chunks of 50 enhances speed but increases the risk that an LLM formats a single result improperly, which triggers a retry of the whole batch.
- **Cost vs Determinism**: Calling the LLM for resume extraction incurs API usage, whereas a pure regex method is computationally free but misses nuanced contexts (like skipping a skill if it's listed under "Certifications").

### Improvements
- Build robust caching for LLM requests (e.g., storing a hash of the prompt and the response) so iterative testing doesn't rack up API charges.
- Implement more robust alias mapping (e.g., treating "React", "ReactJS", and "React.js" as the same entity) in the final gap calculation.
