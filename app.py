from ai_service import test_ai, generate_resume_summary, generate_ats_analysis, match_job_description, generate_interview_questions, generate_ats_improvement, generate_cover_letter
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_mail import Mail, Message
import random
from datetime import datetime, timedelta
import pdfplumber
import docx
import re
import os
import tempfile
import spacy
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_file,  redirect
import json
import fitz
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

mail = Mail(app)

app.secret_key = os.getenv("SECRET_KEY")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_PERMANENT"] = True

CORS(
    app,
    supports_credentials=True,
    origins=["https://careerpilot-ai-1-wdck.onrender.com"]
)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        autocommit=True
    )

db = get_db_connection()
cursor = db.cursor(dictionary=True)
otp_storage = {}
@app.route("/test-ai")
def test_ai_route():

    return {
        "response": test_ai()
    }
@app.route("/test-db")
def test_db():

    cursor.execute("SELECT * FROM users")

    data = cursor.fetchall()

    return jsonify(data)
@app.route("/register", methods=["POST"])
def register():

    data = request.json

    name = data["name"]
    email = data["email"]
    password = data["password"]

    hashed_password = generate_password_hash(password)

    try:

        query = """
        INSERT INTO users(name,email,password)
        VALUES(%s,%s,%s)
        """

        cursor.execute(
            query,
            (name,email,hashed_password)
        )

        db.commit()

        return jsonify({
            "success":True,
            "message":"User registered successfully"
        })


    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "success":False,
            "error":str(e)
        })
@app.route("/login", methods=["GET"])
def login_page():
    return send_file("login.html")
@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data["email"].strip()
    password = data["password"]

    query = "SELECT * FROM users WHERE email=%s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404

    if not check_password_hash(user["password"], password):
        return jsonify({
            "success": False,
            "message": "Wrong password"
        }), 401

    session.clear()
    session.permanent = True

    session["user"] = user["name"]
    session["email"] = user["email"]
    

    print("LOGIN SESSION:", dict(session))

    return jsonify({
        "success": True,
        "message": "Login successful",
        "name": user["name"],
        "email": user["email"]
    })

@app.route("/dashboard", methods=["GET"])
def dashboard():

    if "email" not in session:
        return redirect("/login")

    return send_file("dashboard.html")
@app.route("/send-otp", methods=["POST"])
def send_otp():

    data = request.get_json()

    email = data["email"].strip()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    if not user:

        return jsonify({
            "success": False,
            "message": "Email not registered."
        })

    otp = str(random.randint(100000,999999))

    otp_storage[email] = {
        "otp": otp,
        "expiry": datetime.now() + timedelta(minutes=5),
        "verified": False
    }

    msg = Message(

        subject="CareerPilot AI - Password Reset OTP",

        sender=app.config["MAIL_USERNAME"],

        recipients=[email]

    )

    msg.body = f"""

Hello {user["name"]},

Your OTP for password reset is:

{otp}

This OTP is valid for 5 minutes.

Do not share this OTP with anyone.

CareerPilot AI
"""

    mail.send(msg)

    return jsonify({

        "success": True,

        "message": "OTP sent successfully."

    })
@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    data = request.get_json()

    email = data["email"].strip()
    otp = data["otp"].strip()

    if email not in otp_storage:

        return jsonify({
            "success": False,
            "message": "OTP not found. Please request a new OTP."
        })

    saved = otp_storage[email]

    if datetime.now() > saved["expiry"]:

        del otp_storage[email]

        return jsonify({
            "success": False,
            "message": "OTP has expired."
        })

    if otp != saved["otp"]:

        return jsonify({
            "success": False,
            "message": "Invalid OTP."
        })
    otp_storage[email]["verified"] = True

    return jsonify({
        "success": True,
        "message": "OTP Verified Successfully."
    })
@app.route("/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json()

    email = data["email"].strip()
    password = data["password"]

    if email not in otp_storage:

        return jsonify({
            "success": False,
            "message": "Please verify OTP first."
        })

    hashed_password = generate_password_hash(password)

    cursor.execute(
        "UPDATE users SET password=%s WHERE email=%s",
        (hashed_password, email)
    )

    db.commit()

    del otp_storage[email]

    return jsonify({
        "success": True,
        "message": "Password Reset Successfully."
    })

# Load SpaCy NER Model
nlp = spacy.load("en_core_web_sm")


# ---------------------------------------------------
# Text Extraction
# ---------------------------------------------------


def extract_text_from_pdf(path):

    text = ""

    with pdfplumber.open(path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2
            )

            if page_text:
                page_text = re.sub(r"\n+", "\n", page_text)
                text += page_text + "\n"

    return text
def extract_text_from_docx(path):
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs])

def get_section(text, start_keywords, end_keywords):

    lines = text.split("\n")

    collecting = False
    result = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        # Start section
        if not collecting:
            for keyword in start_keywords:
                if lower.startswith(keyword.lower()):
                    collecting = True
                    break
            continue

        # End section
        stop = False
        for keyword in end_keywords:
            if lower.startswith(keyword.lower()):
                stop = True
                break

        if stop:
            break

        result.append(line)

    return "\n".join(result)

# ---------------------------------------------------
# NER Based Extraction
# ---------------------------------------------------

def extract_name(text):

    # Resume ki pehli 5 lines check karo
    lines = text.split("\n")[:5]

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Email wali line skip
        if "@" in line:
            continue

        # Phone number hata do
        line = re.sub(r"\+?\d[\d\s\-()]{8,}", "", line)

        # Extra spaces hata do
        line = line.strip()

        # Agar line me sirf alphabets aur spaces hain
        if re.fullmatch(r"[A-Za-z ]{3,40}", line):
            return line.title()

    # SpaCy fallback
    doc = nlp(text)

    for ent in doc.ents:

        if ent.label_ == "PERSON":

            name = re.sub(r"\+?\d[\d\s\-()]{8,}", "", ent.text)

            return name.strip().title()

    return "Not Found"

def extract_entities(text):
    doc = nlp(text)

    entities = {
        "PERSON": [],
        "ORG": [],
        "GPE": []
    }

    for ent in doc.ents:
        if ent.label_ in entities:
            if ent.text not in entities[ent.label_]:
                entities[ent.label_].append(ent.text)

    return entities

# ---------------------------------------------------
# Regex Extraction
# ---------------------------------------------------

def extract_email(text):
    match = re.search(
        r"[\w.\-+]+@[\w\-]+\.[a-zA-Z]{2,}",
        text
    )
    return match.group() if match else "Not Found"

def extract_phone(text):
    match = re.search(
        r"(\+?\d[\d\s\-().]{8,14}\d)",
        text
    )
    return match.group().strip() if match else "Not Found"

def extract_linkedin(text):
    match = re.search(
        r"(linkedin\.com/in/[\w\-]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return "https://" + match.group()

    return "Not Found"

def extract_github(text):
    match = re.search(
        r"(github\.com/[\w\-]+)",
        text,
        re.IGNORECASE
    )

    if match:
        return "https://" + match.group()

    return "Not Found"

# ---------------------------------------------------
# Skills Extraction
# ---------------------------------------------------

def extract_skills(text):

    SKILL_KEYWORDS = [
        "Python", "Java", "JavaScript", "TypeScript",
        "C", "C++", "C#", "HTML", "CSS",
        "React", "Angular", "Vue",
        "Node.js", "Express.js",
        "Django", "Flask", "Spring",
        "FastAPI", "MySQL", "PostgreSQL",
        "MongoDB", "Firebase",
        "Redis", "Docker", "Kubernetes",
        "AWS", "Azure", "GCP",
        "Git", "GitHub",
        "REST API", "GraphQL",
        "Linux", "SQL", "NoSQL",
        "Machine Learning",
        "Deep Learning",
        "TensorFlow", "PyTorch",
        "Pandas", "NumPy",
        "Scikit-learn", "NLP",
        "Bootstrap", "Tailwind",
        "Figma", "Postman",
        "Selenium", "Flutter",
        "Dart", "Kotlin", "Swift"
    ]

    found = []

    text_lower = text.lower()

    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            if skill not in found:
                found.append(skill)

    return found if found else ["Not Found"]

# ---------------------------------------------------
# Education Extraction
# ---------------------------------------------------

def extract_education(text):

    section = get_section(
        text,
        ["Education"],
        [
            "Technical Skills",
            "Skills",
            "Projects",
            "Experience",
            "Internship",
            "Certifications",
            "Languages"
        ]
    )

    if not section:
        return []

    lines = [line.strip() for line in section.split("\n") if line.strip()]

    education = []
    current = ""

    for line in lines:

        if (
            "University" in line
            or "School" in line
            or "College" in line
        ):

            if current:
                education.append(current.strip())

            current = line

        else:
            current += " " + line

    if current:
        education.append(current.strip())

    return education
   

# ---------------------------------------------------
# Experience Extraction
# ---------------------------------------------------

def extract_experience(text):

    section = get_section(
        text,
        ["Experience", "Work Experience", "Internship"],
        [
            "Projects",
            "Education",
            "Technical Skills",
            "Skills",
            "Certifications",
            "Languages",
            "Achievements"
        ]
    )

    if not section:
        return []

    lines = [line.strip().replace("•", "") for line in section.split("\n") if line.strip()]

    jobs = []
    current = None

    for line in lines:

        # Experience title
        if ("Intern" in line or
            "Developer" in line or
            "Engineer" in line or
            "Analyst" in line or
            "Executive" in line):

            if current:
                jobs.append(current)

            current = {
                "title": line,
                "description": []
            }

        elif current:
            current["description"].append(line)

    if current:
        jobs.append(current)

    return jobs
def extract_projects(text):

    section = get_section(
        text,
        ["Projects", "Project"],
        []
    )

    if not section:
        return []

    lines = [line.strip() for line in section.split("\n") if line.strip()]

    projects = []
    current = None

    i = 0

    while i < len(lines):

        line = lines[i]
        lower = line.lower()

        # Stop when next section starts
        if lower in [
            "internship",
            "experience",
            "work experience",
            "education",
            "technical skills",
            "skills",
            "achievements",
            "certifications",
            "languages"
        ]:
            break

        # Project Title
        if "|" in line:

            title = line

            # If next line is only a year (2026 etc.)
            if i + 1 < len(lines):
                nxt = lines[i + 1]

                if re.fullmatch(r"\d{4}", nxt):
                    title += " " + nxt
                    i += 1

            current = {
                "title": title,
                "tech": "",
                "description": []
            }

            projects.append(current)

        elif current:

            # First comma line = tech stack
            if current["tech"] == "" and "," in line:
                current["tech"] = line

            else:
                current["description"].append(line)

        i += 1

    return projects
# ---------------------------------------------------
# Resume Score
# ---------------------------------------------------

def calculate_score(data):

    score = 0

    if data["name"] != "Not Found":
        score += 20

    if data["email"] != "Not Found":
        score += 15

    if data["phone"] != "Not Found":
        score += 15

    score += min(len(data["skills"]),20)

    if len(data["education"])>0:
        score += 10

    if len(data["projects"])>0:
        score += 10

    if len(data["experience"])>0:
        score += 10

    return min(score,95)
def generate_ats_analysis(data):

    suggestions = []

    strengths = []

    # Name
    if data["name"] == "Not Found":
        suggestions.append("Add your full name.")
    else:
        strengths.append("Name Found")

    # Email
    if data["email"] == "Not Found":
        suggestions.append("Add a professional email.")
    else:
        strengths.append("Professional Email")

    # Phone
    if data["phone"] == "Not Found":
        suggestions.append("Add phone number.")
    else:
        strengths.append("Phone Number")

    # LinkedIn
    if data["linkedin"] == "Not Found":
        suggestions.append("Add LinkedIn profile.")
    else:
        strengths.append("LinkedIn Profile")

    # GitHub
    if data["github"] == "Not Found":
        suggestions.append("Add GitHub profile.")
    else:
        strengths.append("GitHub Profile")

    # Skills
    if len(data["skills"]) < 8:
        suggestions.append("Add more technical skills.")
    else:
        strengths.append("Strong Technical Skills")

    # Projects
    if len(data["projects"]) == 0:
        suggestions.append("Add at least one project.")
    else:
        strengths.append("Projects Included")

    # Experience
    if len(data["experience"]) == 0:
        suggestions.append("Add internship or work experience.")
    if len(data["skills"]) < 10:
        suggestions.append("Add more technical skills related to your target role.")

    if len(data["projects"]) < 2:
        suggestions.append("Include at least two strong projects.")

    if len(data["experience"]) == 0:
        suggestions.append("Add internship or practical experience.")
    else:
        strengths.append("Experience Present")

    return {
        "strengths": strengths,
        "suggestions": suggestions
    }

# ---------------------------------------------------
# Routes
# ---------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return send_file("register.html")

@app.route("/parse", methods=["POST"])
def parse_resume():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if "resume" not in request.files:
        return jsonify({
            "error": "No file uploaded"
        }), 400

    file = request.files["resume"]

    if file.filename == "":
        return jsonify({
            "error": "Empty filename"
        }), 400

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in [".pdf", ".docx"]:
        return jsonify({
            "error": "Only PDF and DOCX supported"
        }), 400

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=ext
    ) as tmp:

        file.save(tmp.name)
        temp_path = tmp.name

    try:

        if ext == ".pdf":
            text = extract_text_from_pdf(temp_path)
        else:
            text = extract_text_from_docx(temp_path)
        ai_summary = generate_resume_summary(text)

        parsed = {
            "name": extract_name(text),
            "email": extract_email(text),
            "phone": extract_phone(text),
            "linkedin": extract_linkedin(text),
            "github": extract_github(text),
            "skills": extract_skills(text),
            "education": extract_education(text),
            "experience": extract_experience(text),
            
            "projects": extract_projects(text),
            "entities": extract_entities(text),
            
            "raw_text": text[:2000],
            "ai_summary": ai_summary
        }
        print("========== PARSED DATA ==========")
        print("Name:", parsed["name"])
        print("Education:", parsed["education"])
        print("Experience:", parsed["experience"])
        print("Projects:", parsed["projects"])
        print("=================================")
        print(parsed["projects"])
        print(parsed["experience"])
        print("SESSION:", session)
        print("SESSION EMAIL:", session.get("email"))

        parsed["score"] = calculate_score(parsed)
        parsed["ats"] = generate_ats_analysis(parsed)
        parsed["interview_questions"] = generate_interview_questions(parsed)

        user_email = session.get("email")

        if user_email:

            cursor.execute(
               "SELECT id FROM users WHERE email=%s",(user_email,)
               
            )
            user = cursor.fetchone()
            print("USER:", user)

            


            if user:

                query = """
                INSERT INTO resumes
                (
                    user_id,
                    file_name,
                    name,
                    email,
                    phone,
                    skills,
                    education,
                    experience,
                    score,
                    projects,
                    ai_summary,
                    ats,
                    linkedin,
                    github,
                    interview_questions,
                    raw_text
                )

                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """
                print(dict(session))
                print("PARSED DATA:", parsed)


                cursor.execute(
                    query,
                   (
        user["id"],
        file.filename,
        parsed["name"],
        parsed["email"],
        parsed["phone"],
        ",".join(parsed["skills"]),
        json.dumps(parsed["education"]),
        json.dumps(parsed["experience"]),
        parsed["score"],
        json.dumps(parsed["projects"]),
        parsed["ai_summary"],
        json.dumps(parsed["ats"]),
        parsed["linkedin"],
        parsed["github"],
        json.dumps(parsed["interview_questions"]),
        parsed["raw_text"]
                )
                )

                db.commit()
                print("Resume Saved Successfully")

        return jsonify({
            "success": True,
            "data": parsed
        })

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({
           "success": False,
           "error": str(e)
        }), 500

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ---------------------------------------------------
# Run
# ---------------------------------------------------
@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    })
@app.route("/resume-history", methods=["GET"])
def resume_history():
    print("HISTORY SESSION:", dict(session))

    user_email = session.get("email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please login first"
        }), 401

    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (user_email,)
    )

    user = cursor.fetchone()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404

    cursor.execute("""
        SELECT
            id,
            file_name,
            name,
            score,
            uploaded_at
        FROM resumes
        WHERE user_id=%s
        ORDER BY uploaded_at DESC
    """, (user["id"],))

    resumes = cursor.fetchall()

    return jsonify({
        "success": True,
        "resumes": resumes
    })
@app.route("/latest-interview", methods=["GET"])
def latest_interview():

    user_email = session.get("email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please login first"
        }), 401

    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (user_email,)
    )

    user = cursor.fetchone()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404

    cursor.execute("""
        SELECT
            name,
            interview_questions
        FROM resumes
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user["id"],))

    resume = cursor.fetchone()

    if not resume:
        return jsonify({
            "success": False,
            "message": "No Resume Found"
        })

    interview_questions = {
        "technical": [],
        "project": [],
        "hr": []
    }

    if resume["interview_questions"]:

        try:
            interview_questions = json.loads(
                resume["interview_questions"]
            )
        except Exception as e:
            print("Interview JSON Error:", e)

    return jsonify({
        "success": True,
        "name": resume["name"],
        "interview_questions": interview_questions
    })
@app.route("/ats-improvement")
def ats_improvement():

    user_email = session.get("email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please Login"
        }), 401

    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (user_email,)
    )

    user = cursor.fetchone()

    cursor.execute("""
        SELECT raw_text,name
        FROM resumes
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user["id"],))

    resume = cursor.fetchone()

    if not resume:
        return jsonify({
            "success": False,
            "message": "No Resume Found"
        })

    improvement = generate_ats_improvement(
        resume["raw_text"]
    )

    return jsonify({

        "success": True,

        "name": resume["name"],

        "improvement": improvement

    })
@app.route("/delete-resume/<int:resume_id>", methods=["DELETE"])
def delete_resume(resume_id):

    user_email = session.get("email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please login first"
        }), 401

    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (user_email,)
    )

    user = cursor.fetchone()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404

    cursor.execute(
        """
        DELETE FROM resumes
        WHERE id=%s AND user_id=%s
        """,
        (resume_id, user["id"])
    )

    db.commit()

    return jsonify({
        "success": True,
        "message": "Resume deleted successfully"
    })
@app.route("/resume/<int:resume_id>", methods=["GET"])
def get_resume(resume_id):

    user_email = session.get("email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please login first"
        }), 401

    cursor.execute(
        """
        SELECT
            resumes.*
        FROM resumes
        JOIN users
        ON resumes.user_id = users.id
        WHERE resumes.id=%s
        AND users.email=%s
        """,
        (resume_id, user_email)
    )

    resume = cursor.fetchone()

    if not resume:
        return jsonify({
            "success": False,
            "message": "Resume not found"
        }), 404

    return jsonify({
        "success": True,
        "resume": resume
    })
@app.route("/job-match", methods=["POST"])
def job_match():

    user_email = session.get("email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please login first"
        }), 401

    data = request.get_json()

    job_description = data.get("job_description", "").strip()

    if not job_description:
        return jsonify({
            "success": False,
            "message": "Job Description is required"
        }), 400

    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (user_email,)
    )

    user = cursor.fetchone()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404

    cursor.execute("""
        SELECT raw_text
        FROM resumes
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user["id"],))

    resume = cursor.fetchone()

    if not resume:
        return jsonify({
            "success": False,
            "message": "No Resume Found"
        })

    result = match_job_description(
        resume["raw_text"],
        job_description
    )

    return jsonify({
        "success": True,
        "result": result
    })
@app.route("/cover-letter", methods=["POST"])
def cover_letter():

    user_email = session.get("email")

    if not user_email:
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = request.get_json()

    job_description = data.get("job_description", "").strip()

    if job_description == "":
        return jsonify({
            "success": False,
            "message": "Job Description is required."
        })

    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (user_email,)
    )

    user = cursor.fetchone()

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found."
        })

    cursor.execute("""
        SELECT
            name,
            raw_text
        FROM resumes
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (user["id"],))

    resume = cursor.fetchone()

    if not resume:
        return jsonify({
            "success": False,
            "message": "No Resume Found."
        })

    letter = generate_cover_letter(
        resume["raw_text"],
        job_description
    )

    return jsonify({

        "success": True,

        "name": resume["name"],

        "cover_letter": letter

    })
if __name__ == "__main__":
    app.run(debug=True, port=5000)