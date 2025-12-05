from fastapi import FastAPI, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .parser import parse_resume
from .skills import SKILLS, SYNONYMS, ROLE_KEYWORDS

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv
import os
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Small, fast embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

app = FastAPI(title="Resume SaaS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_skills_from_text(text: str) -> set[str]:
    text_low = text.lower()
    found: set[str] = set()
    for skill in SKILLS:
        if skill.lower() in text_low:
            found.add(skill)
    for syn, real in SYNONYMS.items():
        if syn in text_low:
            found.add(real)
    return found


def _detect_role(jd_text: str) -> str:
    jd_low = jd_text.lower()
    best_role = "General Software Engineer"
    best_hits = 0
    for role, keywords in ROLE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in jd_low)
        if hits > best_hits:
            best_hits = hits
            best_role = role
    return best_role


@app.get("/")
def home():
    return {"status": "Backend running", "message": "Resume SaaS API is live 🚀"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()
    parsed = parse_resume(content)
    return {"filename": file.filename, "parsed": parsed}


def compute_score(resume_text: str, jd_text: str, resume_skills_input: list[str] | None = None) -> dict:
    resume_text = (resume_text or "").lower()
    jd_text = (jd_text or "").lower()
    resume_skills_input = resume_skills_input or []

    if not resume_text or not jd_text:
        return {"error": "Resume or JD missing"}

    resume_skills: set[str] = set(s.lower() for s in resume_skills_input)
    if not resume_skills:
        resume_skills = _extract_skills_from_text(resume_text)

    jd_skills = _extract_skills_from_text(jd_text)

    matched_jd_skills = sorted(s for s in jd_skills if s in resume_skills)
    missing_skills = sorted(s for s in jd_skills if s not in resume_skills)
    resume_extra_skills = sorted(s for s in resume_skills if s not in jd_skills)

    if jd_skills:
        coverage = len(matched_jd_skills) / len(jd_skills)
    else:
        coverage = 0.0

    skill_score = min((coverage * 60.0) + (min(len(resume_skills) / len(SKILLS), 1.0) * 10.0), 70.0)

    try:
        emb_resume = model.encode([resume_text])
        emb_jd = model.encode([jd_text])
        similarity = max(0.0, min(1.0, float(cosine_similarity(emb_resume, emb_jd)[0][0])))
    except Exception:
        similarity = 0.0

    jd_score = similarity * 30.0
    final_score = round(skill_score + jd_score, 2)
    detected_role = _detect_role(jd_text)

    return {
        "final_score": float(final_score),
        "skill_score": float(round(skill_score, 2)),
        "jd_similarity_score": float(round(jd_score, 2)),
        "similarity_raw": float(round(similarity, 4)),
        "matched_jd_skills": matched_jd_skills,
        "missing_skills": missing_skills,
        "resume_extra_skills": resume_extra_skills,
        "role": detected_role,
    }


@app.post("/score")
async def score_resume(data: dict = Body(...)):
    return compute_score(data.get("resume") or "", data.get("jd") or "", data.get("skills") or [])


@app.post("/score-report")
async def score_report(data: dict = Body(...)):
    result = compute_score(data.get("resume") or "", data.get("jd") or "", data.get("skills") or [])
    if result.get("error"):
        return result

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def line(text, size=12, gap=16, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(40, y, text)
        y -= gap

    line("Resume Match Engine – ATS Report", 16, 26, bold=True)
    line(f"Overall Match Score: {result['final_score']}%", 13, 20)
    line(f"Skill Match: {result['skill_score']}% (max 70%)", 11)
    line(f"JD Similarity: {result['jd_similarity_score']}% (max 30%)", 11)
    line(f"Detected Role: {result['role']}", 11)
    y -= 16

    line("JD Skills You Already Have:", 13, 20, bold=True)
    for s in result["matched_jd_skills"] or ["None"]:
        line(f"- {s}", 11)

    y -= 10
    line("Important Missing Skills:", 13, 20, bold=True)
    for s in result["missing_skills"] or ["None"]:
        line(f"- {s}", 11)

    y -= 10
    line("Bonus Skills In Your Resume:", 13, 20, bold=True)
    for s in result["resume_extra_skills"] or ["None"]:
        line(f"- {s}", 11)

    c.showPage()
    c.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resume_match_report.pdf"},
    )


# 🧠 NEW FEATURE — AI Resume Rewrite
@app.post("/rewrite")
async def rewrite_resume(data: dict = Body(...)):
    if not client:
        return {"error": "Groq API key missing (.env not configured)"}

    resume_text = data.get("resume") or ""
    jd_text = data.get("jd") or ""

    if not resume_text or not jd_text:
        return {"error": "Resume or JD missing"}

    prompt = f"""
Rewrite the resume to match the job. Output JSON:

Resume:
{resume_text}

JD:
{jd_text}

JSON Output:
{{
  "improved_summary": "...",
  "skills_to_add": ["..."],
  "bullet_suggestions": ["..."]
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        reply = response.choices[0].message.content.strip()
        
        # Try to parse JSON safely
        import json
        try:
            return json.loads(reply)
        except:
            # LLM may return extra text around JSON → try cleaning
            start = reply.find("{")
            end = reply.rfind("}") + 1
            if start != -1 and end != -1:
                try:
                    return json.loads(reply[start:end])
                except:
                    pass
            # Give raw output if still not JSON
            return {"raw_output": reply, "error": "JSON parse failed"}


    except Exception as e:
        return {"error": str(e)}

