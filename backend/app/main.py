# backend/app/main.py

from fastapi import FastAPI, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware

from .parser import parse_resume
from .skills import SKILLS, SYNONYMS, ROLE_KEYWORDS

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


# Small, fast embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

app = FastAPI(title="Resume SaaS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev mode: allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_skills_from_text(text: str) -> set[str]:
    """Skill detector used by /score as a fallback."""
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
    """Very simple heuristic-based JD role detection."""
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
    """Upload + parse resume (PDF)."""
    content = await file.read()
    parsed = parse_resume(content)
    return {"filename": file.filename, "parsed": parsed}


@app.post("/score")
async def score_resume(data: dict = Body(...)):
    """
    Score resume vs job description.

    Expects JSON:
    {
      "resume": "...full text...",
      "jd": "...job description...",
      "skills": ["python","react",...]   # optional, from parser
    }
    """
    resume_text = (data.get("resume") or "").lower()
    jd_text = (data.get("jd") or "").lower()
    resume_skills_input = data.get("skills") or []

    if not resume_text or not jd_text:
        return {"error": "Resume or JD missing"}

    # Use skills sent from frontend, fall back to text-based extraction
    resume_skills: set[str] = set(s.lower() for s in resume_skills_input)
    if not resume_skills:
        resume_skills = _extract_skills_from_text(resume_text)

    # Skills present in JD
    jd_skills = _extract_skills_from_text(jd_text)

    # Intersections / differences
    matched_jd_skills = sorted(s for s in jd_skills if s in resume_skills)
    missing_skills = sorted(s for s in jd_skills if s not in resume_skills)
    resume_extra_skills = sorted(s for s in resume_skills if s not in jd_skills)

    # ===== Skill scoring =====
    # 60% weight → how many JD skills you actually have
    if jd_skills:
        coverage = len(matched_jd_skills) / len(jd_skills)
    else:
        coverage = 0.0

    skill_score_core = coverage * 60.0  # max 60

    # 10% weight → overall skill richness (more diverse skills = small bonus)
    if SKILLS:
        richness = min(len(resume_skills) / len(SKILLS), 1.0)
    else:
        richness = 0.0

    skill_score_bonus = richness * 10.0  # max 10

    skill_score = skill_score_core + skill_score_bonus
    if skill_score > 70.0:
        skill_score = 70.0

    # ===== JD semantic similarity (embeddings) =====
    try:
        emb_resume = model.encode([resume_text])
        emb_jd = model.encode([jd_text])
        similarity = float(cosine_similarity(emb_resume, emb_jd)[0][0])
        # clip to [0,1]
        if similarity < 0.0:
            similarity = 0.0
        if similarity > 1.0:
            similarity = 1.0
    except Exception:
        similarity = 0.0

    jd_score = similarity * 30.0  # 30% weight

    # ===== Final score =====
    final_score = round(skill_score + jd_score, 2)

    # Role detection
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

