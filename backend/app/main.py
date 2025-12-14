from fastapi import FastAPI, UploadFile, File, Body, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
from typing import Optional
import json

import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .parser import parse_resume, extract_skills
from .skills import SKILLS, SYNONYMS, ROLE_KEYWORDS
from .database import get_db, init_db
from .models import User, Analysis
from .auth import (
    hash_password, verify_password, create_access_token, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv
import os
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Small, fast embedding model - loaded lazily to prevent startup delay
_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading SentenceTransformer model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("Model loaded!")
    return _model

app = FastAPI(title="Resume SaaS Backend")
os.makedirs("avatars", exist_ok=True)
app.mount("/avatars", StaticFiles(directory="avatars"), name="avatars")

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- REQUEST/RESPONSE MODELS ----

class UserRegister(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# ---- HELPER FUNCTIONS ----

# Helper function _extract_skills_from_text removed; imported from .parser


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

# ---- AUTH ENDPOINTS ----
# ---- AUTH ENDPOINTS ----

@app.post("/auth/register", response_model=TokenResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""

    # check if email exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pwd = hash_password(user.password)

    new_user = User(
        email=user.email,
        username=user.username,
        password=hashed_pwd,  # updated field name
        name=None,
        avatar_url=None,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login with email + password"""

    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password):  # updated field name
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me")
def get_profile(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Return logged-in user's profile"""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    current_user = get_current_user(token, db)

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "username": current_user.username,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at,
    }

class ProfileUpdate(BaseModel):
    name: Optional[str]
    email: Optional[str]
    username: Optional[str]

@app.put("/auth/update-profile")
def update_profile(data: ProfileUpdate, 
                   authorization: Optional[str] = Header(None), 
                   db: Session = Depends(get_db)):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    user = get_current_user(token, db)

    # Update fields only if provided
    if data.name is not None:
        user.name = data.name

    if data.email is not None:
        # Check if email belongs to someone else
        if db.query(User).filter(User.email == data.email, User.id != user.id).first():
            raise HTTPException(status_code=400, detail="Email already taken")
        user.email = data.email

    if data.username is not None:
        if db.query(User).filter(User.username == data.username, User.id != user.id).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = data.username

    db.commit()
    db.refresh(user)

    return {"message": "Profile updated successfully"}

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

@app.put("/auth/change-password")
def change_password(data: PasswordChange,
                    authorization: Optional[str] = Header(None), 
                    db: Session = Depends(get_db)):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    user = get_current_user(token, db)

    # Verify old password
    if not verify_password(data.old_password, user.password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    # Set new password
    user.password = hash_password(data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}

@app.post("/auth/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")
    user = get_current_user(token, db)

    # Store locally under /avatars/
    folder = "avatars"
    os.makedirs(folder, exist_ok=True)

    filename = f"user_{user.id}_{file.filename}"
    filepath = os.path.join(folder, filename)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    # Save URL path (frontend will load it)
    user.avatar_url = f"http://127.0.0.1:8000/avatars/{filename}"
    db.commit()

    return {"avatar_url": user.avatar_url}


# ---- PUBLIC ENDPOINTS ----

@app.get("/")
def home():
    return {"status": "Backend running", "message": "Resume SaaS API is live 🚀"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a PDF resume"""
    try:
        content = await file.read()
        parsed = parse_resume(content)
        return {"filename": file.filename, "parsed": parsed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {str(e)}")


def compute_score(resume_text: str, jd_text: str, resume_skills_input: list[str] | None = None) -> dict:
    """Compute match score between resume and JD"""
    resume_text = (resume_text or "").lower()
    jd_text = (jd_text or "").lower()
    resume_skills_input = resume_skills_input or []

    if not resume_text or not jd_text:
        return {"error": "Resume or JD missing"}

    resume_skills: set[str] = set(s.lower() for s in resume_skills_input)
    if not resume_skills:
        resume_skills = set(extract_skills(resume_text))

    jd_skills = set(extract_skills(jd_text))

    matched_jd_skills = sorted(s for s in jd_skills if s in resume_skills)
    missing_skills = sorted(s for s in jd_skills if s not in resume_skills)
    resume_extra_skills = sorted(s for s in resume_skills if s not in jd_skills)

    # SCORING LOGIC
    # 1. Skill Match (Primary Factor)
    if jd_skills:
        coverage = len(matched_jd_skills) / len(jd_skills)
    else:
        coverage = 0.0

    skill_score = coverage * 75.0  # Max 75 points from skills

    # 2. Semantic Similarity (Secondary Factor)
    try:
        embed_model = get_model()
        emb_resume = embed_model.encode([resume_text])
        emb_jd = embed_model.encode([jd_text])
        similarity = float(cosine_similarity(emb_resume, emb_jd)[0][0])
        # Clamp between 0 and 1
        similarity = max(0.0, min(1.0, similarity))
    except Exception:
        similarity = 0.0

    # If JD is extremely short and has no detected skills, return 0
    if len(jd_text) < 10 and not jd_skills:
        return {
            "final_score": 0.0,
            "skill_score": 0.0,
            "jd_similarity_score": 0.0,
            "similarity_raw": 0.0,
            "matched_jd_skills": [],
            "missing_skills": [],
            "resume_extra_skills": [],
            "role": "Unknown",
        }

    # If JD has no skills, rely more on semantic but penalize valid "tech" comparison
    if not jd_skills:
        # If no skills detected in JD, and semantic similarity is low, return 0.
        # This prevents "hi there" from getting any score.
        if similarity < 0.5:
            jd_score = 0.0
        else:
            jd_score = similarity * 50.0 
    else:
        jd_score = similarity * 25.0

    final_score = round(skill_score + jd_score, 2)
    
    # Cap at 100
    final_score = min(100.0, final_score)

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
    """Score resume against job description"""
    return compute_score(data.get("resume") or "", data.get("jd") or "", data.get("skills") or [])


import uuid

# Simple in-memory cache for reports (cleared on restart)
REPORT_CACHE = {}

def _generate_pdf_buffer(result):
    """Internal helper to generate PDF buffer from result dict"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Helper to strict sanitize text
    def safe_text(text):
        if not text: return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    # --- Header ---
    c.setFillColorRGB(0.02, 0.05, 0.1) 
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 50, "Resume Match Report")
    
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawString(width - 220, height - 50, "Generated by Resume Analysis AI")

    # --- Score Section ---
    y = height - 120
    
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, safe_text(f"Total Match Score: {result['final_score']}%"))
    
    # Breakdown
    y -= 30
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(40, y, safe_text(f"Skill Match: {result['skill_score']}% (max 75%)"))
    c.drawString(300, y, safe_text(f"JD Similarity: {result['jd_similarity_score']}% (max 25%)"))
    y -= 20
    c.drawString(40, y, safe_text(f"Detected Role: {result['role']}"))
    
    y -= 40
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(40, y, width - 40, y)
    y -= 30

    # --- Content Function ---
    def draw_section(title, items, color_hex):
        nonlocal y
        if y < 100: 
            c.showPage()
            y = height - 50
        
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(40, y, safe_text(title))
        y -= 20
        
        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        
        if not items:
            c.drawString(60, y, "- None detected")
            y -= 16
        else:
            for item in items:
                if y < 50:
                    c.showPage()
                    y = height - 50
                c.drawString(60, y, safe_text(f"• {item}"))
                y -= 16
        y -= 20

    draw_section("✅ JD Skills You Have", result["matched_jd_skills"], "#00AA00")
    draw_section("⚠️ Missing Skills", result["missing_skills"], "#AA0000")
    draw_section("💎 Bonus Skills (Not in JD)", result["resume_extra_skills"], "#0000AA")

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width / 2, 30, "Automated Report - Not a guarantee of hiring")

    c.save()
    buffer.seek(0)
    return buffer

def _generate_fallback_pdf(result, error_msg=""):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, "Resume Match Report (Fallback)")
    c.drawString(100, 730, "Original generation failed.")
    c.drawString(100, 710, f"Score: {result.get('final_score', 'N/A')}")
    c.save()
    buffer.seek(0)
    return buffer

@app.post("/score-report")
async def score_report(data: dict = Body(...)):
    """Legacy endpoint (kept for safety, but we move to two-step)"""
    try:
        result = compute_score(data.get("resume") or "", data.get("jd") or "", data.get("skills") or [])
        buffer = _generate_pdf_buffer(result)
        return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=resume_match_report.pdf"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/init-score-download")
async def init_score_download(data: dict = Body(...)):
    """Step 1: Generate PDF and return ID"""
    try:
        result = compute_score(data.get("resume") or "", data.get("jd") or "", data.get("skills") or [])
        try:
            buffer = _generate_pdf_buffer(result)
        except Exception as e:
            # Fallback
            import traceback
            traceback.print_exc()
            buffer = _generate_fallback_pdf(result, str(e))
        
        report_id = str(uuid.uuid4())
        REPORT_CACHE[report_id] = buffer
        # Return URL ending in .pdf so browser sees it as file
        return {"download_url": f"/download-report/{report_id}/resume_match_report.pdf"}
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/download-report/{report_id}/{filename}")
async def download_report_endpoint(report_id: str, filename: str):
    """Step 2: Serve the PDF. Filename param is ignored logic-wise but helps browser."""
    if report_id not in REPORT_CACHE:
        raise HTTPException(status_code=404, detail="Report expired or not found")
    
    buffer = REPORT_CACHE[report_id]
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# 🧠 AI Resume Rewrite
@app.post("/rewrite")
async def rewrite_resume(data: dict = Body(...)):
    """AI-powered resume rewrite suggestions using Groq"""
    if not client:
        return {"error": "Groq API key missing (.env not configured)"}

    resume_text = data.get("resume") or ""
    jd_text = data.get("jd") or ""

    if not resume_text or not jd_text:
        return {"error": "Resume or JD missing"}

    prompt = f"""
Analyze the resume against the JD. Provide 3 specific improvements in JSON format.
Rules:
- JSON only. No markdown. No conversational text.
- Keys: "improved_summary", "skills_to_add" (list), "bullet_suggestions" (list).

Resume:
{resume_text[:2000]}

JD:
{jd_text[:2000]}
"""

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful expert career coach. You always output valid JSON object."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            reply = response.choices[0].message.content.strip()
            
            # Parsing
            start = reply.find("{")
            end = reply.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(reply[start:end])
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            continue

    return {"error": "AI busy. Please try again."}

# ---- PROTECTED ENDPOINTS ----

@app.post("/analyze")
async def analyze_resume(
    data: dict = Body(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Analyze resume and save to database (requires auth)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    try:
        current_user = get_current_user(token, db)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    resume_text = data.get("resume", "")
    jd_text = data.get("jd", "")
    scores = compute_score(resume_text, jd_text)
    
    if "error" in scores:
        raise HTTPException(status_code=400, detail=scores["error"])
    
    analysis = Analysis(
        user_id=current_user.id,
        resume_name=data.get("resume_name", "resume.pdf"),
        job_title=scores.get("role", "Unknown"),
        job_description=jd_text,
        match_score=scores["final_score"],
        skill_score=scores["skill_score"],
        semantic_score=scores["jd_similarity_score"],
        missing_skills=json.dumps(scores.get("missing_skills", [])),
        bonus_skills=json.dumps(scores.get("resume_extra_skills", []))
    )
    db.add(analysis)
    db.commit()
    
    return scores


@app.get("/analyses")
def get_user_analyses(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get all analyses for current user (requires auth)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    try:
        current_user = get_current_user(token, db)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).all()
    return [{"id": a.id, "resume_name": a.resume_name, "job_title": a.job_title, "match_score": a.match_score} for a in analyses]


@app.get("/analyses/{analysis_id}")
def get_analysis_detail(
    analysis_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get detailed analysis (requires auth)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization.replace("Bearer ", "")
    try:
        current_user = get_current_user(token, db)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "id": analysis.id,
        "resume_name": analysis.resume_name,
        "job_title": analysis.job_title,
        "job_description": analysis.job_description,
        "match_score": analysis.match_score,
        "skill_score": analysis.skill_score,
        "semantic_score": analysis.semantic_score,
        "missing_skills": json.loads(analysis.missing_skills),
        "bonus_skills": json.loads(analysis.bonus_skills),
        "created_at": analysis.created_at
    }


# ---- RENDER DEPLOYMENT: Bind to PORT environment variable ----
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
