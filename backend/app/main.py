from fastapi import FastAPI, UploadFile, File, Body, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta, datetime
from typing import Optional
import json

import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

from .parser import parse_resume, extract_skills
from .skills import SKILLS, SYNONYMS, ROLE_KEYWORDS
from .database import get_db, init_db
from .models import User, Analysis
from .auth import (
    hash_password, verify_password, create_access_token, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

from dotenv import load_dotenv
import os
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Lazy load Groq client to prevent startup errors
_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None and GROQ_API_KEY:
        try:
            print("Initializing Groq client...")
            _groq_client = Groq(api_key=GROQ_API_KEY)
            print("Groq client initialized!")
        except Exception as e:
            print(f"Failed to initialize Groq client: {e}")
            return None
    return _groq_client

# Small, fast TF-IDF similarity instead of heavy SentenceTransformer
_vectorizer = None

def get_similarity(text1, text2):
    """Memory-efficient TF-IDF based similarity"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([text1, text2])
        return float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
    except Exception as e:
        print(f"Similarity error: {e}")
        return 0.0

app = FastAPI(title="Resume SaaS Backend")
os.makedirs("avatars", exist_ok=True)
app.mount("/avatars", StaticFiles(directory="avatars"), name="avatars")

# Initialize database on startup (not at import time)
@app.on_event("startup")
async def startup_event():
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialized!")

# Configure CORS - Nuclear option for production
# Set allow_credentials=False when using "*" to avoid browser blocks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
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
    jd_len = len(jd_low)
    
    # If JD is too short, don't guess a specific role
    if jd_len < 40:
        return "Generic / Undefined Role"
        
    best_role = "General Software Engineer"
    best_hits = 0
    for role, keywords in ROLE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in jd_low)
        if hits > best_hits:
            best_hits = hits
            best_role = role
            
    # If no specific keywords matched despite reasonable length, call it general
    if best_hits == 0:
        return "Software Professional" if jd_len < 300 else "General Software Engineer"
        
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
    print(f"DEBUG: Login attempt for email: {user.email}")
    try:
        db_user = db.query(User).filter(User.email == user.email).first()
        if not db_user:
            print(f"DEBUG: User not found: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        print(f"DEBUG: User found, verifying password...")
        if not verify_password(user.password, db_user.password):
            print(f"DEBUG: Password verification failed for: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        print(f"DEBUG: Password verified, creating token...")
        access_token = create_access_token(
            data={"sub": db_user.email},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        print(f"DEBUG: Token created successfully for: {user.email}")

        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"CRITICAL LOGIN ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
    db: Session = Depends(get_db),
    request: Request = None 
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

    # Use BACKEND_URL from env if set, otherwise fallback to request base
    backend_url = os.getenv("BACKEND_URL")
    if backend_url:
        base_url = backend_url.rstrip("/")
    else:
        # Better fallback for production proxies
        # If running on Render, it usually has specific headers
        host = request.headers.get("host", "localhost:8000")
        scheme = request.headers.get("x-forwarded-proto", "http")
        base_url = f"{scheme}://{host}"
        
    user.avatar_url = f"{base_url}/avatars/{filename}"
    
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
        similarity = get_similarity(resume_text, jd_text)
        # Clamp between 0 and 1
        similarity = max(0.0, min(1.0, similarity))
    except Exception:
        similarity = 0.0

    # 3. JD Depth Penalty (Prevents inflated scores for low-effort or single-word JDs)
    jd_len = len(jd_text)
    jd_skill_count = len(jd_skills)
    
    # Length Multiplier
    if jd_len < 50: len_mult = 0.2
    elif jd_len < 200: len_mult = 0.5
    elif jd_len < 600: len_mult = 0.85
    else: len_mult = 1.0
    
    # Skill Density Multiplier
    if jd_skill_count == 0: skill_mult = 0.0
    elif jd_skill_count == 1: skill_mult = 0.35
    elif jd_skill_count == 2: skill_mult = 0.65
    elif jd_skill_count <= 4: skill_mult = 0.9
    else: skill_mult = 1.0
    
    # Final quality multiplier (weighted average)
    quality_multiplier = (len_mult * 0.4) + (skill_mult * 0.6)

    # 4. Final Adjustment Logic
    # If JD is extremely short and has no detected skills, return 0
    if jd_len < 10 and not jd_skills:
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
        if similarity < 0.5:
            jd_score = 0.0
        else:
            jd_score = similarity * 50.0 
    else:
        jd_score = similarity * 25.0

    # Apply the JD Depth Penalty to both scores
    skill_score = skill_score * quality_multiplier
    jd_score = jd_score * len_mult

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
    """Advanced Professional PDF Match Report"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- Professional Color Palette ---
    COLOR_NAVY = (0.02, 0.05, 0.1)      # Header
    COLOR_MINT = (0.0, 0.7, 0.6)        # Success/Accent (a bit darker for PDF print)
    COLOR_ROSE = (0.8, 0.1, 0.4)        # Alert
    COLOR_SKY = (0.2, 0.5, 0.8)         # Secondary
    COLOR_GRAY_BG = (0.96, 0.97, 0.98)  # Section Bg
    COLOR_TEXT = (0.15, 0.15, 0.15)     # Main Text
    
    def safe_text(text):
        if not text: return ""
        # ReportLab build-in fonts (Helvetica) are limited to Latin-1
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    # --- Header Banner ---
    c.setFillColorRGB(*COLOR_NAVY)
    c.rect(0, height - 100, width, 100, fill=1, stroke=0)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(40, height - 55, "ATS COMPLIANCE REPORT")
    
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawString(40, height - 75, f"Prepared for: {safe_text(result.get('user_name', 'Professional Candidate'))}")
    c.drawRightString(width - 40, height - 75, datetime.now().strftime("%B %d, %Y"))

    # --- Score Meter Section ---
    y = height - 150
    score = result['final_score']
    
    # Draw Score Card
    c.setFillColorRGB(*COLOR_GRAY_BG)
    c.roundRect(40, y - 60, width - 80, 80, 10, fill=1, stroke=0)
    
    c.setFillColorRGB(*COLOR_NAVY)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y - 5, "MATCH SCORE RELEVANCE")
    
    # Progress Bar Track
    bar_width = width - 200
    c.setFillColorRGB(0.85, 0.85, 0.85)
    c.roundRect(60, y - 35, bar_width, 15, 7, fill=1, stroke=0)
    
    # Progress Bar Fill
    fill_color = COLOR_MINT if score > 70 else (COLOR_SKY if score > 40 else COLOR_ROSE)
    c.setFillColorRGB(*fill_color)
    c.roundRect(60, y - 35, bar_width * (score / 100.0), 15, 7, fill=1, stroke=0)
    
    # Score Text
    c.setFillColorRGB(*COLOR_NAVY)
    c.setFont("Helvetica-Bold", 26)
    c.drawRightString(width - 65, y - 32, f"{score}%")
    
    # Role Badge
    y -= 80
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(*COLOR_TEXT)
    c.drawString(40, y, "TARGET ROLE:")
    c.setFillColorRGB(*COLOR_SKY)
    c.drawString(135, y, safe_text(result['role'].upper()))

    # Breakdown Details
    y -= 25
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(40, y, f"Skill Alignment: {result['skill_score']}% (75% weight)")
    c.drawString(240, y, f"Semantic Relevance: {result['jd_similarity_score']}% (25% weight)")
    
    y -= 30
    c.setStrokeColorRGB(0.85, 0.85, 0.85)
    c.setLineWidth(0.5)
    c.line(40, y, width - 40, y)
    y -= 30

    # --- Content Sections ---
    def draw_list_section(title, items, icon, color):
        nonlocal y
        if y < 150:
            c.showPage()
            y = height - 50
        
        c.setFillColorRGB(*color)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(40, y, f"{icon} {title}")
        y -= 22
        
        c.setFont("Helvetica", 10.5)
        c.setFillColorRGB(*COLOR_TEXT)
        if not items:
            c.drawString(60, y, "No specific items detected in this category.")
            y -= 16
        else:
            for item in items:
                if y < 60:
                    c.showPage()
                    y = height - 50
                c.drawString(62, y, "-") # Simple dash
                c.drawString(75, y, safe_text(item))
                y -= 16
        y -= 15

    draw_list_section("CORE COMPETENCIES MATCHED", result["matched_jd_skills"], "V", (0, 0.5, 0.2))
    draw_list_section("CRITICAL SKILL GAPS", result["missing_skills"], "X", (0.7, 0, 0.1))
    draw_list_section("RELEVANT DIFFERENTIATORS", result["resume_extra_skills"], "*", (0.1, 0.3, 0.7))

    # --- AI Recommendations Section ---
    if result.get("improved_summary") or result.get("bullet_suggestions"):
        if y < 220:
            c.showPage()
            y = height - 50
        
        y -= 10
        c.setFillColorRGB(*COLOR_GRAY_BG)
        c.rect(0, y - 25, width, 32, fill=1, stroke=0)
        c.setFillColorRGB(*COLOR_NAVY)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y - 5, "STRATEGIC AI RECOMMENDATIONS")
        y -= 50

        if result.get("improved_summary"):
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(*COLOR_TEXT)
            c.drawString(40, y, "TAILORED PROFESSIONAL SUMMARY:")
            y -= 20
            c.setFont("Helvetica", 10.5)
            # Text Wrap
            lines = simpleSplit(safe_text(result["improved_summary"]), "Helvetica", 10.5, width - 100)
            for line in lines:
                if y < 50: c.showPage(); y = height - 50
                c.drawString(60, y, line)
                y -= 15
            y -= 25

        if result.get("bullet_suggestions") and isinstance(result["bullet_suggestions"], list):
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(*COLOR_TEXT)
            c.drawString(40, y, "HIGH-IMPACT BULLET POINTS (STAR METHOD):")
            y -= 25
            for sug in result["bullet_suggestions"]:
                if y < 90: c.showPage(); y = height - 50
                
                # Handle both string and object formats
                bullet = sug.get("bullet", "") if isinstance(sug, dict) else str(sug)
                why = sug.get("why", "") if isinstance(sug, dict) else ""
                
                # Bullet Main
                c.setFont("Helvetica-Bold", 10.5)
                c.setFillColorRGB(*COLOR_NAVY)
                c.drawString(48, y, ">")
                
                b_lines = simpleSplit(safe_text(bullet), "Helvetica-Bold", 10.5, width - 120)
                for line in b_lines:
                    if y < 50: c.showPage(); y = height - 50
                    c.drawString(65, y, line)
                    y -= 15
                
                # Explanation (Why)
                if why:
                    c.setFont("Helvetica-Oblique", 9.5)
                    c.setFillColorRGB(0.4, 0.4, 0.4)
                    w_lines = simpleSplit(f"Strategy: {safe_text(why)}", "Helvetica-Oblique", 9.5, width - 130)
                    for line in w_lines:
                        if y < 50: c.showPage(); y = height - 50
                        c.drawString(75, y, line)
                        y -= 13
                y -= 12

    # --- Footer ---
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(width / 2, 25, "Confidential Document | Generated by ResumeMatch AI Pro | Higher hiring probability through data-driven analysis")

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
        
        # Enrich result with extra data for the professional PDF
        result["user_name"] = data.get("user_name") or "Guest"
        result["improved_summary"] = data.get("improved_summary")
        result["skills_to_add"] = data.get("skills_to_add")
        result["bullet_suggestions"] = data.get("bullet_suggestions")

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
    client = get_groq_client()
    if not client:
        return {"error": "Groq API key missing or client failed to initialize"}

    resume_text = data.get("resume") or ""
    jd_text = data.get("jd") or ""

    if not resume_text or not jd_text:
        return {"error": "Resume or JD missing"}

    prompt = f"""
Analyze the resume below against the provided Job Description (JD). 
Provide high-quality, professional improvements to make the candidate more competitive for this specific role.
Return a JSON object with exactly these keys:
1. "improved_summary": A professional summary (2-3 sentences) tailored to this JD.
2. "skills_to_add": A list of specific hard skills or tools from the JD that are not prominent in the resume.
3. "bullet_suggestions": A list of objects, each with:
   - "bullet": A polished, action-oriented resume bullet point using the STAR method (Situation, Task, Action, Result) that incorporates keywords from the JD.
   - "why": A short explanation of why this bullet point is particularly effective for this JD.

Rules:
- JSON format only.
- No conversational filler.
- Ensure the advice is actionable and high-impact.

Resume:
{resume_text[:3000]}

JD:
{jd_text[:3000]}
"""

    last_exception = "Unknown error"
    for attempt in range(2):
        try:
            print(f"DEBUG: AI Rewrite Attempt {attempt+1}...")
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
            print(f"DEBUG: AI Response received! Length: {len(reply)}")
            
            # Parsing
            start = reply.find("{")
            end = reply.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(reply[start:end])
        except Exception as e:
            last_exception = str(e)
            print(f"DEBUG: Attempt {attempt+1} failed: {last_exception}")
            import traceback
            traceback.print_exc()
            continue

    return {"error": f"AI service error: {last_exception}. Please try again."}

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
