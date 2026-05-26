import sqlite3
import re
import json
import time
from pathlib import Path
from pydantic import BaseModel
from prompt_model import prompt_model

class SkillGapResult(BaseModel):
	gaps: list[str]

def fetch_db_skills(db_url: str) -> set:
	"""Fetch and normalize all unique skills from the jobs database."""
	db_path = Path(db_url)
	if not db_path.exists():
		return set()

	try:
		conn = sqlite3.connect(db_path)
		cursor = conn.cursor()
		cursor.execute("SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL")
		rows = cursor.fetchall()
		conn.close()

		all_skills = set()
		for row in rows:
			if not row[0]:
				continue
			# Skills are comma-separated based on tag_data.py
			skills = [s.strip().lower() for s in row[0].split(",")]
			for skill in skills:
				if skill:
					all_skills.add(skill)

		return all_skills
	except Exception as e:
		# Handle database errors gracefully
		print(f"Error: {e}")
		return set()

def extract_resume_skills_with_llm(resume_text: str, model_name: str = "gemini-2.5-flash-lite") -> set:
	"""
	Extracts skills from the resume using an LLM to ensure certifications/soft skills are ignored.
	Structured to return deterministic JSON format.
	"""
	# Defensive programming: simple jailbreak prevention
	safe_resume = resume_text.replace("ignore previous instructions", "").replace("system prompt", "")

	prompt = f"""
You are an expert technical recruiter analyzing a resume.
Extract ALL technical hard skills, programming languages, databases, cloud providers, and frameworks.

CRITICAL INSTRUCTIONS:
1. EXCLUDE soft skills (e.g., leadership, cooking, management, English).
2. EXCLUDE certifications (e.g., CISCO CCNA, AWS Certified).
3. Return strictly a JSON array of strings in lowercase.
4. Do not include markdown formatting or conversational text.

Resume Text:
{safe_resume}
"""

	max_retries = 3
	retry_delay = 1

	for attempt in range(max_retries):
		try:
			res = prompt_model(model_name, prompt)

			# Clean possible markdown from the LLM output
			clean_res = res.replace("```json", "").replace("```", "").strip()
			extracted_skills = json.loads(clean_res)

			if isinstance(extracted_skills, list):
				return set([str(skill).strip().lower() for skill in extracted_skills])
		except Exception as e:
			print(f"Attempt {attempt} failed: {e}")
			print(f"Retrying in {retry_delay}s...")
			time.sleep(retry_delay)
			retry_delay *= 2  # Exponential backoff

	return set()

def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:
	"""Main function to identify skill gaps deterministically."""
	try:
		# 1. Load the resume text
		file_path = Path(input_file_path)
		if not file_path.exists():
			return SkillGapResult(gaps=[])

		with open(file_path, "r", encoding="utf-8") as f:
			resume_text = f.read()

		# 2. Get unique skills from the database
		db_skills = fetch_db_skills(db_url)
		if not db_skills:
			return SkillGapResult(gaps=[])

		# 3. Extract skills present in the resume
		# Option A: Strict Regex matching (highly deterministic but might miss aliases)
		resume_text_lower = resume_text.lower()
		resume_skills_regex = set()
		for skill in db_skills:
			# Word boundary regex to ensure exact matching, avoiding substring false positives
			pattern = r'\b' + re.escape(skill) + r'\b'
			if re.search(pattern, resume_text_lower):
				resume_skills_regex.add(skill)

		# Option B: LLM extraction matching
		resume_skills_llm = extract_resume_skills_with_llm(resume_text)

		# Combine both methods for best coverage
		found_skills = resume_skills_regex.union(resume_skills_llm)

		# 4. Calculate the skill gaps
		gaps = db_skills.difference(found_skills)

		# Sort and return as lowercased list
		sorted_gaps = sorted(list(gaps))

		return SkillGapResult(gaps=sorted_gaps)

	except Exception as e:
		# Fulfilling the requirement to handle all errors gracefully (no crashes)
		print(f"Error: {e}")
		return SkillGapResult(gaps=[])

if __name__ == "__main__":
	result = find_skill_gaps("data/resources/resume_d3.txt", "data/resources/jobs_d1.db")
	print(f"gaps={result.gaps}")
