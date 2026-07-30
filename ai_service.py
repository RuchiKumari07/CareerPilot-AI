import  json
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")


client = genai.Client(api_key=API_KEY)


# -----------------------------
# Test AI
# -----------------------------
def test_ai():
    try:
        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents="Say Hello"
        )
        return response.text

    except Exception as e:
        print("Gemini Error:", e)
        return "AI service unavailable."


# -----------------------------
# Resume Summary
# -----------------------------
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

    try:
        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt
        )

        return response.text

    except Exception as e:
        print("Gemini Error:", e)
        return "AI Summary is temporarily unavailable."
    

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

    try:

        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt
        )

        text = response.text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception as e:

        print("Gemini Error:", e)

        return {
            "technical": [],
            "project": [],
            "hr": []
        }
# -----------------------------
# ATS Analysis
# -----------------------------
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

    try:
        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt
        )

        return response.text

    except Exception as e:
        print("Gemini Error:", e)
        return "ATS Analysis unavailable."


# -----------------------------
# Job Description Match
# -----------------------------
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

    try:
        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt
        )

        return response.text

    except Exception as e:
        print("Gemini Error:", e)

        return """
{
  "match_percentage": 0,
  "matched_skills": [],
  "missing_skills": [],
  "suggestions": [
    "AI service unavailable"
  ]
}

"""
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

    try:

        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt
        )

        return response.text

    except Exception as e:

        print("Gemini Error:", e)

        return "Cover Letter generation failed."
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

    try:

        response = client.models.generate_content(
            model="models/gemini-flash-latest",
            contents=prompt
        )

        return response.text

    except Exception as e:

        print("Gemini Error:", e)

        return "ATS Improvement is currently unavailable."
