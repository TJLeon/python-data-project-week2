import sqlite3
from pathlib import Path
from prompt_model import prompt_model
import json
import re

BATCH_SIZE = 50
DB_PATH = "data/resources/jobs_d1.db"

def parse_and_validate_response(response: str, batch: list[tuple], attempt: int = 1):
	"""
	Parses model response and validates it.
	Returns matches list if valid, False if needs retry.
	"""
	# Parse response: extract all "Analyzed Job" lines
	pattern = r"Analyzed Job (\d+): (.+)"
	matches = re.findall(pattern, response)

	# Check 1: Batch size mismatch
	if len(matches) != len(batch):
		print(f"Attempt {attempt} failed: Mismatch between batch size and response")
		return False

	# Extract source_ids from batch for validation
	batch_source_ids = {str(row[0]) for row in batch}

	# Check 2 & 3: Validate each result
	for source_id, tech_stack in matches:
		# Check 2: Valid source_id
		if source_id not in batch_source_ids:
			print(f"Attempt {attempt} failed: Invalid source_id in response")
			return False

		# Check 3: Non-empty tech_stack
		if not tech_stack.strip():
			print(f"Attempt {attempt} failed: Empty tech_stack in response")
			return False

	return matches  # Return the parsed matches

def tag_data(db_url: str):
	db_path = Path(db_url)
	if not db_path.exists():
		print("Error: invalid database path")
		return

	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()

	cursor.execute("SELECT COUNT(*) FROM jobs WHERE tech_stack IS NULL")
	table_size = cursor.fetchone()[0]
	total = 0

	while total < table_size:
		cursor.execute("""
			SELECT source_id, job_title, description
			FROM jobs WHERE tech_stack IS NULL
			LIMIT ?
		""", (BATCH_SIZE,))
		rows = cursor.fetchall()

		if not rows:
			break

		formatted_jobs = json.dumps([
			{
				"source_id": row[0],
				"job_title": row[1],
				"description": row[2]
			}
			for row in rows
		], indent=4, ensure_ascii=False).encode("ascii", "ignore").decode("ascii")

		prompt = f"""You are a technical data extractor. Your task is to extract concrete technical hard skills from job title and descriptions.

CRITICAL INSTRUCTIONS:
1. ONLY extract: Programming Languages (e.g., Python, SQL), Frameworks/Libraries (e.g., Spring Boot, PyTorch), Cloud/DBs (e.g., AWS, Oracle), Tools (e.g., Docker, Excel, Tableau), and specific technical methods (e.g., A/B testing, feature engineering, CI/CD, labeling).
2. DO NOT extract: Soft skills, degrees/fields of study (Computer Science, Mathematics, Statistics), generic job duties (data cleaning, integration, optimization, decision-making, analytics), architectural concepts (data warehouse, microservices, data lake), or broad buzzwords (AI, ML, Deep Learning).
3. Split grouped phrases into individual skills, but keep canonical names together (e.g., "Spring Framework/Spring Boot").
4. You must respond ONLY with the exact format specified below. No conversational text or markdown blocks.

INPUT DATA EXAMPLE:
[
    {{
        "source_id": "111111",
        "job_title": "Data Analyst",
        "description": "Bachelors in Computer Science. Must have Python, Spring Framework/Spring Boot, Excel, and A/B testing. Responsible for product optimization, data-driven decision making, feature engineering, and labeling. Experience with AI and ML pipelines."
    }}
]
OUTPUT DATA EXAMPLE:
Analyzed Job 111111: Python, Spring Framework/Spring Boot, Excel, A/B testing, feature engineering, labeling

OUTPUT FORMAT:
Analyzed Job <source_id>: <comma-separated list>

INPUT JSON:
{formatted_jobs}
"""

		max_retries = 5
		for attempt in range(1, max_retries + 1):
			res = prompt_model("gemini-2.5-flash-lite", prompt)

			parsed_matches = parse_and_validate_response(res, rows, attempt)

			if parsed_matches:  # If validation passed, we get the matches
				for source_id, tech_stack in parsed_matches:
					# Update database with parsed results
					cursor.execute("""
					UPDATE jobs
					SET tech_stack = ?
					WHERE source_id = ?
				""", (tech_stack, source_id))
					print(f"Analyzed Job {source_id}: {tech_stack}")
				conn.commit()  # Commit changes to database
				total += BATCH_SIZE
				break
			else:
				#print(f"Attempt {attempt}:")
				#print(res)
				pass

	conn.close()

if __name__ == "__main__":
	tag_data(DB_PATH)
