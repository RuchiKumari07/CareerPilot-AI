import json
import time
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)


# =========================================================
# COMMON GEMINI FUNCTION
# =========================================================

def generate_ai_response(prompt):

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )

            return response.text

        except Exception as e:

            print(f"Gemini Error - Attempt {attempt + 1}:", e)

            if attempt < 2:
                time.sleep(3)

    return None


# =========================================================
# TEST AI
# =========================================================

def test_ai():

    response = generate_ai_response("Say Hello")

    if response is None:
        return "AI service unavailable."

    return response


# =========================================================
# RESUME SUMMARY
# =========================================================

def generate_resume_summary(resume_text):

    prompt = f"""
You are an ATS Resume Analyzer.

Analyze this resume.

Resume:
{resume_text}

Return ONLY in this format:

1. Candidate Profile
2. Strengths
3. Weaknesses
4. Career Recommendation

Rules:

Use ONLY resume information.

Never invent skills.

Never invent dates.

Do not incorrectly mark previous years as future.

Keep maximum 180 words.
"""

    response_text = generate_ai_response(prompt)

    if response_text is None:
        return "AI Summary is temporarily unavailable."

    return response_text


# =========================================================
# INTERVIEW QUESTIONS
# =========================================================

def generate_interview_questions(parsed):

    prompt = f"""
You are an experienced technical interviewer.

Based on the following resume generate:

1. Five Technical Interview Questions
2. Three Project Based Questions
3. Two HR Interview Questions

Candidate Name:
{parsed["name"]}

Skills:
{", ".join(parsed["skills"])}

Education:
{parsed["education"]}

Experience:
{parsed["experience"]}

Projects:
{parsed["projects"]}

Return ONLY valid JSON.

{{
  "technical": [],
  "project": [],
  "hr": []
}}

Do not return markdown.
"""

    response_text = generate_ai_response(prompt)

    if response_text is None:

        return {
            "technical": [],
            "project": [],
            "hr": []
        }

    try:

        text = response_text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception as e:

        print("Interview JSON Error:", e)

        return {
            "technical": [],
            "project": [],
            "hr": []
        }


# =========================================================
# ATS ANALYSIS
# =========================================================

def generate_ats_analysis(parsed):

    prompt = f"""
You are an ATS Resume Analyzer.

Analyze the following resume.

Name:
{parsed['name']}

Skills:
{", ".join(parsed['skills'])}

Education:
{parsed['education']}

Experience:
{parsed['experience']}

Projects:
{parsed['projects']}

Return ONLY:

ATS Score Improvement
Missing Skills
Resume Improvements
Interview Chances

Do not invent information.

Maximum 150 words.
"""

    response_text = generate_ai_response(prompt)

    if response_text is None:
        return "ATS Analysis unavailable."

    return response_text


# =========================================================
# JOB DESCRIPTION MATCH
# =========================================================

def match_job_description(resume_text, job_description):

    prompt = f"""
You are an ATS recruiter.

Compare the Resume with the Job Description.

Resume:
{resume_text}

Job Description:
{job_description}

Return ONLY valid JSON.

{{
  "match_percentage": 0,
  "matched_skills": [],
  "missing_skills": [],
  "suggestions": []
}}
"""

    response_text = generate_ai_response(prompt)

    if response_text is None:

        return """
{
  "match_percentage": 0,
  "matched_skills": [],
  "missing_skills": [],
  "suggestions": [
    "AI service temporarily unavailable"
  ]
}
"""

    return response_text


# =========================================================
# COVER LETTER
# =========================================================

def generate_cover_letter(resume_text, job_description):

    prompt = f"""
You are a professional HR recruiter.

Using the resume and job description below, write a professional cover letter.

Resume:
{resume_text}

Job Description:
{job_description}

Rules:

- Use ONLY resume information.
- Do not invent experience.
- Keep it professional.
- Around 250-350 words.
- Include:
    - Greeting
    - Introduction
    - Skills & Experience
    - Why suitable
    - Closing

Return plain text only.
"""

    response_text = generate_ai_response(prompt)

    if response_text is None:
        return "Cover Letter generation is temporarily unavailable."

    return response_text


# =========================================================
# ATS IMPROVEMENT
# =========================================================

def generate_ats_improvement(resume_text):

    prompt = f"""
You are a professional ATS Resume Expert.

Analyze the following resume.

Resume:
{resume_text}

Give ONLY these sections:

1. ATS Score Improvement
2. Missing Keywords
3. Resume Improvements
4. Technical Skill Improvements
5. Career Advice

Maximum 250 words.

Return plain text only.
"""

    response_text = generate_ai_response(prompt)

    if response_text is None:
        return "ATS Improvement is temporarily unavailable."

    return response_text