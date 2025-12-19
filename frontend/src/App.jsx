import React, { useState, useEffect, useRef } from "react";

const API_BASE = (import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL.startsWith('http'))
  ? import.meta.env.VITE_API_URL
  : "/api";

async function apiFetch(path, opts = {}, token) {
  const headers = opts.headers ? { ...opts.headers } : {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const cfg = { ...opts, headers };
  // FOOLPROOF FIX: Use URL constructor
  const fullUrl = API_BASE.startsWith('http')
    ? new URL(path, API_BASE).href
    : `${API_BASE}${path}`.replace(/\/+/g, '/'); // Ensure single slashes

  const res = await fetch(fullUrl, cfg);
  return res;
}

const themes = {
  neon: {
    bg: "radial-gradient(circle at 0 0, #1d3557 0, transparent 55%), radial-gradient(circle at 100% 100%, #2a9d8f 0, #02030a 55%)",
    text: "#f5f5ff",
    cardBg: "radial-gradient(circle at top, rgba(0,255,170,0.12), transparent 60%), #070b10",
    cardBorder: "1px solid rgba(0,255,170,0.25)",
    cardShadow: "0 0 25px rgba(0,255,170,0.25), 0 0 60px rgba(0,150,255,0.25)",
    pillBg: "rgba(255,255,255,0.06)",
    pillBorder: "1px solid rgba(255,255,255,0.25)",
    buttonText: "#fff",
    accent: "#00f5d4",
    chartPrimary: "#01ff8b",
    chartTrack: "#181818",
    chartInner: "#05070c",
    scoreText: "#00ffb3",
    scoreSecondary: "#4cc9f0",
    inputBg: "rgba(2,6,23,0.9)",
    inputBorder: "1px solid rgba(255,255,255,0.16)",
    inputText: "#e9fffd",
    jdBtnBg: "rgba(255,255,255,0.08)",
    jdBtnText: "white",
    jdBtnBorder: "1px solid rgba(255,255,255,0.1)",
  },
  dark: {
    bg: "#0f172a",
    text: "#e2e8f0",
    cardBg: "#1e293b",
    cardBorder: "1px solid #334155",
    cardShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    pillBg: "#334155",
    pillBorder: "1px solid #475569",
    buttonText: "#f1f5f9",
    accent: "#38bdf8",
    chartPrimary: "#38bdf8",
    chartTrack: "#334155",
    chartInner: "#0f172a",
    scoreText: "#38bdf8",
    scoreSecondary: "#94a3b8",
    inputBg: "#0f172a",
    inputBorder: "1px solid #334155",
    inputText: "#e2e8f0",
    jdBtnBg: "#334155",
    jdBtnText: "#f1f5f9",
    jdBtnBorder: "1px solid #475569",
  },
  light: {
    bg: "#f8fafc",
    text: "#1e293b",
    cardBg: "#ffffff",
    cardBorder: "1px solid #e2e8f0",
    cardShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    pillBg: "#f1f5f9",
    pillBorder: "1px solid #cbd5e1",
    buttonText: "#334155",
    accent: "#0ea5e9",
    chartPrimary: "#0ea5e9",
    chartTrack: "#e2e8f0",
    chartInner: "#f8fafc",
    scoreText: "#0284c7",
    scoreSecondary: "#64748b",
    inputBg: "#f1f5f9",
    inputBorder: "1px solid #cbd5e1",
    inputText: "#1e293b",
    jdBtnBg: "#f1f5f9",
    jdBtnText: "#334155",
    jdBtnBorder: "1px solid #cbd5e1",
  }
};

export default function App({ token: initialToken = null, onLogout }) {
  const [token, setToken] = useState(initialToken);
  const [currentTheme, setCurrentTheme] = useState("neon");
  const t = themes[currentTheme];

  function toggleTheme() {
    setCurrentTheme(p => p === "neon" ? "dark" : p === "dark" ? "light" : "neon");
  }

  async function apiFetchAuth(path, options = {}, authKey = null) {
    const res = await apiFetch(path, options, authKey || token);
    if (res.status === 401) {
      console.warn("Session expired - logging out");
      handleLogoutLocal();
    }
    return res;
  }
  const [showProfile, setShowProfile] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [profileData, setProfileData] = useState({
    name: "",
    email: "",
    username: "",
    avatar_url: "",
    created_at: null,
  });
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [passwordData, setPasswordData] = useState({
    old_password: "",
    new_password: "",
  });
  const [avatarPreview, setAvatarPreview] = useState(null);
  const fileRef = useRef(null);

  const [file, setFile] = useState(null);
  const [parsed, setParsed] = useState(null);
  const [jd, setJD] = useState("");
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingScore, setLoadingScore] = useState(false);

  const [finalScore, setFinalScore] = useState(null);
  const [skillScore, setSkillScore] = useState(null);
  const [jdScore, setJdScore] = useState(null);
  const [matchedSkills, setMatchedSkills] = useState([]);
  const [missingSkills, setMissingSkills] = useState([]);
  const [extraSkills, setExtraSkills] = useState([]);
  const [role, setRole] = useState(null);
  const [lastPayload, setLastPayload] = useState(null);

  const [improvedSummary, setImprovedSummary] = useState("");
  const [skillsToAdd, setSkillsToAdd] = useState([]);
  const [bulletSuggestions, setBulletSuggestions] = useState([]);
  const [loadingRewrite, setLoadingRewrite] = useState(false);

  const [message, setMessage] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (token) fetchProfile();
  }, [token]);

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  async function fetchProfile() {
    if (!token) return;
    try {
      const res = await apiFetchAuth("/auth/me", { method: "GET" }, token);
      if (!res.ok) {
        console.warn("Profile fetch failed", res.status);
        return;
      }
      const data = await res.json();

      // FIX: If avatar_url points to localhost/127.0.0.1 and we are in production, try to fix it
      if (data.avatar_url && data.avatar_url.includes('127.0.0.1') && API_BASE.startsWith('http')) {
        const apiBaseUrl = new URL(API_BASE);
        const avatarPath = new URL(data.avatar_url).pathname;
        data.avatar_url = `${apiBaseUrl.origin}${avatarPath}`;
      }

      setProfileData((p) => ({ ...p, ...data }));
    } catch (err) {
      console.error("fetchProfile error", err);
    }
  }

  async function updateProfile() {
    if (!token) {
      setMessage({ type: "error", text: "Not authenticated. Please login." });
      return;
    }
    setLoadingProfile(true);
    try {
      const res = await apiFetchAuth(
        "/auth/update-profile",
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: profileData.name || null,
            email: profileData.email || null,
            username: profileData.username || null,
          }),
        },
        token
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Profile update failed");
      }
      await fetchProfile();
      setMessage({ type: "success", text: "Profile updated successfully" });
      setShowProfile(false);
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "Update failed" });
    } finally {
      setLoadingProfile(false);
    }
  }

  async function changePassword() {
    if (!token) {
      setMessage({ type: "error", text: "Not authenticated. Please login." });
      return;
    }
    if (!passwordData.old_password || !passwordData.new_password) {
      setMessage({ type: "error", text: "Enter both passwords" });
      return;
    }
    if (passwordData.new_password.length < 6) {
      setMessage({ type: "error", text: "New password must be at least 6 characters" });
      return;
    }
    try {
      const res = await apiFetchAuth(
        "/auth/change-password",
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(passwordData),
        },
        token
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Password change failed");
      }
      setMessage({ type: "success", text: "Password changed successfully" });
      setPasswordData({ old_password: "", new_password: "" });
      setShowProfile(false);
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "Change password failed" });
    }
  }

  async function uploadAvatar(e) {
    if (!token) {
      setMessage({ type: "error", text: "Not authenticated. Please login." });
      return;
    }
    const f = e.target.files?.[0];
    if (!f) return;

    if (!f.type.startsWith('image/')) {
      setMessage({ type: "error", text: "Please upload a valid image file" });
      return;
    }

    if (f.size > 5 * 1024 * 1024) {
      setMessage({ type: "error", text: "Image size must be less than 5MB" });
      return;
    }

    setAvatarPreview(URL.createObjectURL(f));

    const form = new FormData();
    form.append("file", f);

    try {
      const res = await apiFetchAuth("/auth/upload-avatar", { method: "POST", body: form }, token);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Avatar upload failed");
      }
      const data = await res.json();
      setProfileData((p) => ({ ...p, avatar_url: data.avatar_url }));
      setMessage({ type: "success", text: "Avatar uploaded successfully" });
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "Avatar upload failed" });
      setAvatarPreview(null);
    }
  }

  async function upload() {
    if (!file) return setMessage({ type: "error", text: "Choose a PDF first" });

    if (file.type !== 'application/pdf') {
      setMessage({ type: "error", text: "Please upload a PDF file" });
      return;
    }

    setLoadingUpload(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiFetchAuth("/upload-resume", { method: "POST", body: form }, token);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed");
      }
      const data = await res.json();
      setParsed(data.parsed || null);
      setMessage({ type: "success", text: "Resume parsed successfully" });
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "Upload & parse failed" });
    } finally {
      setLoadingUpload(false);
    }
  }

  async function matchScore() {
    if (!parsed) return setMessage({ type: "error", text: "Upload & parse a resume first." });
    if (!jd || !jd.trim()) return setMessage({ type: "error", text: "Paste a job description first." });

    setLoadingScore(true);
    setMessage(null);

    const payload = {
      resume: parsed.full_text || parsed.snippet || "",
      jd: jd,
      skills: parsed.skills || [],
    };
    setLastPayload(payload);

    try {
      const res = await apiFetchAuth("/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }, token);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Scoring failed");
      }
      const data = await res.json();

      setFinalScore(data.final_score ?? 0);
      setSkillScore(data.skill_score ?? 0);
      setJdScore(data.jd_similarity_score ?? 0);
      setMatchedSkills(data.matched_jd_skills || []);
      setMissingSkills(data.missing_skills || []);
      setExtraSkills(data.resume_extra_skills || []);
      setRole(data.role || null);

      setImprovedSummary("");
      setSkillsToAdd([]);
      setBulletSuggestions([]);
      setMessage({ type: "success", text: "Scored successfully" });
    } catch (err) {
      console.error(err);
      const isTimeout = err.message && (err.message.includes("Failed to fetch") || err.name === "TypeError");
      const msg = isTimeout
        ? "Network error or CORS issue. Please ensure the backend is running and allow-origins is set correctly. (Current API: " + API_BASE + ")"
        : (err.message || "Scoring failed");
      setMessage({ type: "error", text: msg });
    } finally {
      setLoadingScore(false);
    }
  }

  async function downloadReport() {
    if (!lastPayload) return setMessage({ type: "error", text: "Calculate a score first." });
    const enrichPayload = {
      ...lastPayload,
      improved_summary: improvedSummary,
      skills_to_add: skillsToAdd,
      bullet_suggestions: bulletSuggestions,
      user_name: profileData.name || profileData.username || "Guest"
    };

    try {
      const res = await apiFetchAuth("/init-score-download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(enrichPayload),
      }, token);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Report generation failed");
      }

      const data = await res.json();
      // Navigate to the download URL. Browser will handle "attachment" header by downloading it
      // and keeping the user on the current page.
      if (data.download_url) {
        window.location.href = `${API_BASE}${data.download_url}`;
        setMessage({ type: "success", text: "Report download started..." });
      } else {
        throw new Error("No download URL returned");
      }

    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "Failed to download report." });
    }
  }

  async function saveAnalysis() {
    if (!token) {
      setMessage({ type: "error", text: "Please login to save analysis." });
      return;
    }
    if (!lastPayload || finalScore === null) {
      setMessage({ type: "error", text: "Calculate a score before saving." });
      return;
    }

    try {
      const payload = {
        resume: lastPayload.resume,
        jd: lastPayload.jd,
        skills: lastPayload.skills,
        resume_name: file?.name || "resume.pdf",
      };

      const res = await apiFetchAuth("/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload),
      }, token);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Save failed");
      }
      setMessage({ type: "success", text: "Saved analysis to your history" });
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "Failed to save analysis." });
    }
  }

  async function improveResume() {
    if (!lastPayload) return setMessage({ type: "error", text: "Calculate a score before calling AI." });
    setLoadingRewrite(true);
    setMessage(null);

    try {
      const res = await apiFetchAuth("/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastPayload),
      }, token);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "AI rewrite failed");
      }
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }

      setImprovedSummary(data.improved_summary || "");
      setSkillsToAdd(data.skills_to_add || []);
      setBulletSuggestions(data.bullet_suggestions || []);
      setMessage({ type: "success", text: "AI suggestions ready" });
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "AI rewrite failed" });
    } finally {
      setLoadingRewrite(false);
    }
  }

  async function fetchHistory() {
    if (!token) {
      setMessage({ type: "error", text: "Please login to view history." });
      return;
    }
    setLoadingHistory(true);
    try {
      const res = await apiFetchAuth("/analyses", { method: "GET" }, token);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to fetch history");
      }
      const data = await res.json();
      setAnalysisHistory(Array.isArray(data) ? data : []);
      setShowHistory(true);
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: err.message || "Failed to load history" });
    } finally {
      setLoadingHistory(false);
    }
  }

  function handleLogoutLocal() {
    setToken(null);
    setParsed(null);
    setJD("");
    setFile(null);
    setFinalScore(null);
    if (typeof onLogout === "function") onLogout();
  }

  function clearAll() {
    setParsed(null);
    setJD("");
    setFile(null);
    setFinalScore(null);
    setSkillScore(null);
    setJdScore(null);
    setMatchedSkills([]);
    setMissingSkills([]);
    setExtraSkills([]);
    setRole(null);
    setLastPayload(null);
    setImprovedSummary("");
    setSkillsToAdd([]);
    setBulletSuggestions([]);
    if (fileRef.current) fileRef.current.value = "";
    setMessage({ type: "success", text: "All data cleared" });
  }

  const hasScore = finalScore !== null;

  const neonCard = {
    background: t.cardBg,
    borderRadius: "18px",
    border: t.cardBorder,
    boxShadow: t.cardShadow,
    padding: "24px 26px",
    color: t.text,
  };

  const pill = (bg, color = "#fff") => ({
    padding: "6px 12px",
    borderRadius: "999px",
    fontSize: 13,
    background: bg,
    color,
    whiteSpace: "nowrap",
  });

  const scoreCircle = {
    width: 190,
    height: 190,
    borderRadius: "50%",
    background: hasScore ? `conic-gradient(${t.chartPrimary} ${finalScore}%, ${t.chartTrack} 0)` : `conic-gradient(#444 0, ${t.chartTrack} 0)`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: `0 0 40px ${t.chartPrimary}66`, // add some transparency
  };

  const scoreInner = {
    width: 140,
    height: 140,
    borderRadius: "50%",
    background: t.chartInner,
    border: `2px solid ${t.cardBorder.split(' ').pop()}`, // use border color
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    color: t.text,
  };

  return (
    <div style={{ minHeight: "100vh", width: "100%", margin: 0, padding: "32px 40px", fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif", background: t.bg, color: t.text, transition: "all 0.3s ease" }}>

      <header style={{ maxWidth: 1200, margin: "0 auto 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 28, fontWeight: 800, background: "linear-gradient(90deg, #00f5d4, #f72585)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            {(() => {
              const h = new Date().getHours();
              return `Good ${h < 12 ? "Morning" : h < 18 ? "Afternoon" : "Evening"}, ${profileData.name || profileData.username || "Guest"}`;
            })()}
          </div>
        </div>

        <div style={{ textAlign: "center", flex: 1 }}>
          <h1 style={{ fontSize: 34, fontWeight: 800, margin: 0 }}>
            <span style={{ color: "#00f5d4" }}>Resume</span> <span style={{ color: "#f72585" }}>Match</span> <span style={{ color: "#4cc9f0" }}>Engine</span>
          </h1>
          <p style={{ marginTop: 6, opacity: 0.8, fontSize: 14 }}>AI-powered resume vs job-description scoring</p>
        </div>

        <div style={{ flex: 1, display: "flex", justifyContent: "end", gap: 10, flexWrap: "wrap" }}>
          <button onClick={fetchHistory} disabled={loadingHistory} style={{ padding: "10px 18px", borderRadius: "999px", border: "1px solid rgba(255,255,255,0.25)", background: "rgba(255,255,255,0.06)", color: "#fff", cursor: "pointer", backdropFilter: "blur(10px)", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
            📊 {loadingHistory ? "Loading..." : "History"}
          </button>

          <button onClick={() => setShowProfile(true)} style={{ padding: "10px 18px", borderRadius: "999px", border: "1px solid rgba(255,255,255,0.25)", background: "rgba(255,255,255,0.06)", color: "#fff", cursor: "pointer", backdropFilter: "blur(10px)", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
            {profileData.avatar_url ? (
              <img src={profileData.avatar_url} alt="avatar" style={{ width: 24, height: 24, borderRadius: "50%", objectFit: "cover" }} />
            ) : (
              <span>👤</span>
            )}
            {profileData.name || profileData.username || "User"}
          </button>

          <button onClick={toggleTheme} style={{ padding: "10px", borderRadius: "50%", border: t.pillBorder, background: t.pillBg, color: t.buttonText, cursor: "pointer", backdropFilter: "blur(10px)", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center", width: 40, height: 40 }}>
            {currentTheme === "neon" ? "🌙" : currentTheme === "dark" ? "☀️" : "🎨"}
          </button>

          <button onClick={handleLogoutLocal} style={{ padding: "10px 20px", borderRadius: "999px", border: "none", background: "linear-gradient(135deg, #ff006e, #ff4d6d)", color: "#fff", cursor: "pointer", fontWeight: 600, fontSize: 13, boxShadow: "0 0 18px rgba(255, 0, 110, 0.45)" }}>
            🚪 Logout
          </button>
        </div>
      </header >

      {showHistory && (
        <div onClick={() => setShowHistory(false)} style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 9999 }}>
          <div onClick={(e) => e.stopPropagation()} style={{ width: 700, maxHeight: "90vh", overflow: "auto", padding: 32, borderRadius: 20, background: "linear-gradient(135deg, rgba(10,15,22,0.98), rgba(5,10,18,0.95))", boxShadow: "0 0 40px rgba(0,255,200,0.3), 0 0 80px rgba(0,150,255,0.2)", border: "1px solid rgba(0,255,200,0.3)", color: "white" }}>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, display: "flex", alignItems: "center", gap: 10 }}>
                <span>📊</span> Analysis History
              </h2>
              <button onClick={() => setShowHistory(false)} style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)", borderRadius: "50%", width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", fontSize: 18, color: "#fff" }}>
                ×
              </button>
            </div>

            {analysisHistory.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 20px", opacity: 0.7 }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>📭</div>
                <div style={{ fontSize: 16 }}>No saved analyses yet</div>
                <div style={{ fontSize: 13, marginTop: 8, opacity: 0.8 }}>Complete an analysis and click Save to see it here</div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {analysisHistory.map((item, idx) => (
                  <div key={idx} style={{ padding: 18, borderRadius: 12, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{item.resume_name || "Resume"}</div>
                      <div style={{ fontSize: 12, opacity: 0.7 }}>{item.job_title || "Role"}</div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
                      <span style={{ fontSize: 18, fontWeight: 700, color: "#00ffb3" }}>{item.match_score}%</span>
                      <span style={{ fontSize: 12, opacity: 0.8 }}>Match Score</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )
      }

      {
        showProfile && (
          <div onClick={() => setShowProfile(false)} style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 9999 }}>
            <div onClick={(e) => e.stopPropagation()} style={{ width: 480, maxHeight: "90vh", overflow: "auto", padding: 32, borderRadius: 20, background: "linear-gradient(135deg, rgba(10,15,22,0.98), rgba(5,10,18,0.95))", boxShadow: "0 0 40px rgba(0,255,200,0.3), 0 0 80px rgba(0,150,255,0.2)", border: "1px solid rgba(0,255,200,0.3)", color: "white" }}>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, display: "flex", alignItems: "center", gap: 10 }}>
                  <span>👤</span> Profile Settings
                </h2>
                <button onClick={() => setShowProfile(false)} style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)", borderRadius: "50%", width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", fontSize: 18, color: "#fff" }}>
                  ×
                </button>
              </div>

              <div style={{ marginBottom: 28 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 8, color: "#a0d9ff" }}>Full Name</label>
                <input type="text" value={profileData.name || ""} onChange={(e) => setProfileData({ ...profileData, name: e.target.value })} placeholder="Enter your name" style={{ width: "100%", borderRadius: 12, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.15)", padding: "12px 14px", color: "#fff", fontSize: 14, outline: "none", transition: "all 0.2s" }} />
              </div>

              <div style={{ marginBottom: 28 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 8, color: "#a0d9ff" }}>Email Address</label>
                <input type="email" value={profileData.email || ""} onChange={(e) => setProfileData({ ...profileData, email: e.target.value })} placeholder="your.email@example.com" style={{ width: "100%", borderRadius: 12, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.15)", padding: "12px 14px", color: "#fff", fontSize: 14, outline: "none" }} />
              </div>

              <button onClick={updateProfile} disabled={loadingProfile} style={{ marginTop: 8, width: "100%", padding: "13px", borderRadius: 12, background: "linear-gradient(135deg,#00f5d4,#4cc9f0)", fontWeight: 700, border: "none", cursor: loadingProfile ? "wait" : "pointer", fontSize: 15, color: "#021018", boxShadow: "0 4px 20px rgba(0,245,212,0.4)", opacity: loadingProfile ? 0.7 : 1 }}>
                {loadingProfile ? "Saving..." : "💾 Save Changes"}
              </button>

              <div style={{ height: 1, background: "rgba(255,255,255,0.1)", margin: "32px 0" }} />

              <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
                <span>🔐</span> Change Password
              </h3>

              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 8, color: "#a0d9ff" }}>Current Password</label>
                <input type="password" placeholder="Enter current password" value={passwordData.old_password} onChange={(e) => setPasswordData({ ...passwordData, old_password: e.target.value })} style={{ width: "100%", borderRadius: 12, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.15)", padding: "12px 14px", color: "#fff", fontSize: 14, outline: "none" }} />
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 8, color: "#a0d9ff" }}>New Password</label>
                <input type="password" placeholder="Enter new password (min 6 characters)" value={passwordData.new_password} onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })} style={{ width: "100%", borderRadius: 12, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.15)", padding: "12px 14px", color: "#fff", fontSize: 14, outline: "none" }} />
              </div>

              <button onClick={changePassword} style={{ width: "100%", padding: "13px", borderRadius: 12, background: "linear-gradient(135deg,#f72585,#7209b7)", fontWeight: 700, border: "none", cursor: "pointer", color: "#fff", fontSize: 15, boxShadow: "0 4px 20px rgba(247,37,133,0.4)" }}>
                🔑 Update Password
              </button>

              <div style={{ height: 1, background: "rgba(255,255,255,0.1)", margin: "32px 0" }} />

              <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
                <span>📸</span> Profile Picture
              </h3>

              <div style={{ textAlign: "center" }}>
                <div style={{ width: 120, height: 120, borderRadius: "50%", overflow: "hidden", margin: "0 auto 16px", border: "3px solid #00f5d4", boxShadow: "0 0 20px rgba(0,245,212,0.3)" }}>
                  <img src={avatarPreview || profileData.avatar_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Crect fill='%23667' width='120' height='120'/%3E%3Ctext fill='%23fff' font-size='60' x='50%25' y='50%25' text-anchor='middle' dy='.3em'%3E👤%3C/text%3E%3C/svg%3E"} alt="avatar" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>

                <label style={{ display: "inline-block", padding: "10px 20px", borderRadius: 12, background: "rgba(100,200,255,0.15)", border: "1px solid rgba(100,200,255,0.3)", cursor: "pointer", fontSize: 14, fontWeight: 600, color: "#a0d9ff" }}>
                  📁 Choose Image
                  <input type="file" accept="image/*" onChange={uploadAvatar} style={{ display: "none" }} />
                </label>
              </div>
            </div>
          </div>
        )
      }

      <main style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1fr)", gap: 22 }}>
        <section style={neonCard}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18, flexWrap: "wrap", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <label style={{ padding: "9px 14px", borderRadius: "999px", border: "1px solid rgba(255,255,255,0.18)", background: "rgba(5,8,15,0.9)", cursor: "pointer", fontSize: 13 }}>
                📄 Choose PDF Resume
                <input ref={fileRef} type="file" accept="application/pdf" style={{ display: "none" }} onChange={(e) => setFile(e.target.files?.[0] || null)} />
              </label>

              <span style={{ fontSize: 13, opacity: 0.85 }}>{file ? file.name : "No file selected"}</span>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={upload} disabled={!file || loadingUpload} style={{ padding: "9px 18px", borderRadius: "999px", border: "none", cursor: file && !loadingUpload ? "pointer" : "not-allowed", fontSize: 13, fontWeight: 600, background: "linear-gradient(135deg, #00f5d4, #00bbf9, #f72585)", color: "#050816", boxShadow: "0 0 18px rgba(0,245,212,0.45)", opacity: file ? 1 : 0.5 }}>
                {loadingUpload ? "Parsing..." : "Upload & Parse"}
              </button>

              {parsed && (
                <button onClick={clearAll} style={{ padding: "9px 18px", borderRadius: "999px", border: "1px solid rgba(255,100,100,0.3)", background: "rgba(255,50,50,0.1)", cursor: "pointer", fontSize: 13, fontWeight: 600, color: "#ffaaaa" }}>
                  🗑️ Clear
                </button>
              )}
            </div>
          </div>
          <div style={{ fontSize: 11, color: "#ffcc00", marginBottom: 15, opacity: 0.9 }}>
            ⚠️ Note: First-time analysis may take ~60 seconds to boot up the AI models. Please be patient!
          </div>

          {parsed ? (
            <div style={{ marginTop: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <span style={{ fontSize: 22 }}>👤</span>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: "#e9fffc" }}>{parsed.name || "Name not detected"}</div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>AI-extracted from your resume header</div>
                </div>
              </div>

              <div style={{ fontSize: 14, marginTop: 8 }}>
                <p style={{ margin: "4px 0" }}><b>📧 Email:</b> <span style={{ opacity: 0.9 }}>{parsed.emails?.length ? parsed.emails.join(", ") : "Not detected"}</span></p>
                <p style={{ margin: "4px 0" }}><b>📞 Phone:</b> <span style={{ opacity: 0.9 }}>{parsed.phones?.length ? parsed.phones.join(", ") : "Not detected"}</span></p>
              </div>

              <div style={{ marginTop: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span>✨</span><h3 style={{ margin: 0, fontSize: 15 }}>Skills detected ({parsed.skills?.length || 0})</h3>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
                  {parsed.skills?.length ? parsed.skills.map((s, i) => <span key={i} style={pill("linear-gradient(135deg,#00bbf9,#4cc9f0)", "#021015")}>{s}</span>) : <span style={{ fontSize: 13, opacity: 0.7 }}>No skills detected from resume text.</span>}
                </div>
              </div>

              <div style={{ marginTop: 18 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}><span>📄</span><h3 style={{ margin: 0, fontSize: 15 }}>Profile Snippet</h3></div>
                <p style={{ fontSize: 13, opacity: 0.9, maxHeight: 140, overflow: "auto", paddingRight: 6, lineHeight: 1.5 }}>{parsed.snippet}</p>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 13, opacity: 0.75, marginTop: 12, textAlign: "center", padding: "60px 20px" }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>📄</div>
              <div>Upload a PDF resume to see extracted name, contacts & skills.</div>
            </div>
          )}
        </section>

        <section style={neonCard}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span>📑</span><h3 style={{ margin: 0, fontSize: 15 }}>Job Description</h3>
          </div>

          <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
            {[
              { label: "Frontend", text: "Looking for a Frontend Developer with React, TypeScript, and CSS skills. Experience with Redux and responsive design is a plus." },
              { label: "Backend", text: "Hiring a Backend Engineer proficient in Python, FastAPI, and PostgreSQL. Must know Docker and AWS using Jenkins for CI/CD." },
              { label: "ML Engineer", text: "Machine Learning Engineer needed. Must have strong skills in Python, TensorFlow, PyTorch, and NLP. Experience with scikit-learn and data analysis required." },
              { label: "Cloud/DevOps", text: "Cloud Engineer needed with AWS/Azure expertise. Must know Docker, Kubernetes, Terraform, and CI/CD pipelines (Jenkins/GitHub Actions)." },
              { label: "Cybersecurity", text: "Cyber Security Analyst. Experience with Penetration Testing, SIEM, Firewalls, Python, and tools like Metasploit/Burp Suite. CISSP is a plus." },
              { label: "Blockchain", text: "Web3 Developer needed. Experience with Solidity, Ethereum/Smart Contracts, Rust, and DeFi protocols. Knowledge of cryptography is essential." }
            ].map(sample => (
              <button key={sample.label} onClick={() => setJD(sample.text)} style={{ fontSize: 11, background: t.jdBtnBg, border: t.jdBtnBorder, borderRadius: 20, padding: "4px 10px", color: t.jdBtnText, cursor: "pointer", transition: "0.2s" }} onMouseOver={e => e.target.style.background = t.accent + "44"} onMouseOut={e => e.target.style.background = t.jdBtnBg}>
                + {sample.label}
              </button>
            ))}
          </div>

          <textarea placeholder="Paste the JD here (role, responsibilities, required skills)..." value={jd} onChange={(e) => setJD(e.target.value)} style={{ width: "100%", minHeight: 140, resize: "vertical", borderRadius: 10, border: t.inputBorder, background: t.inputBg, color: t.inputText, padding: "10px 12px", fontSize: 13, outline: "none", lineHeight: 1.5 }} />

          <button onClick={matchScore} disabled={loadingScore} style={{ marginTop: 14, padding: "10px 18px", borderRadius: "999px", border: "none", cursor: !loadingScore ? "pointer" : "wait", fontSize: 14, fontWeight: 600, background: "linear-gradient(135deg,#00ffb3,#42a5f5,#f72585)", color: "#050816", boxShadow: "0 0 24px rgba(0,255,179,0.5)", width: "100%" }}>
            {loadingScore ? "Analyzing... (This may take 1 min on first run)" : "Calculate Match Score"}
          </button>

          {hasScore && (
            <>
              <div style={{ marginTop: 22, display: "grid", gridTemplateColumns: "auto 1fr", gap: 18, alignItems: "center" }}>
                <div style={scoreCircle}>
                  <div style={scoreInner}>
                    <div style={{ fontSize: 12, opacity: 0.7 }}>Match Score</div>
                    <div style={{ fontSize: 32, fontWeight: 800, marginTop: 4, color: t.scoreText }}>{finalScore.toFixed(2)}%</div>
                    <div style={{ fontSize: 11, marginTop: 4, opacity: 0.65, textAlign: "center", padding: "0 8px" }}>{role || "Role detected from JD"}</div>
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 14, marginBottom: 10 }}><span style={{ marginRight: 6 }}>🧠</span><b>Score Breakdown</b></div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
                    <div><span style={{ opacity: 0.8 }}>Skill Match:</span> <b style={{ color: t.scoreText }}>{skillScore.toFixed(2)}%</b> <span style={{ opacity: 0.6 }}>(max 75%)</span></div>
                    <div><span style={{ opacity: 0.8 }}>JD Similarity:</span> <b style={{ color: t.scoreSecondary }}>{jdScore.toFixed(2)}%</b> <span style={{ opacity: 0.6 }}>(max 25%)</span></div>
                  </div>

                  <div style={{ marginTop: 14 }}>
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}><span>✅</span><span style={{ fontSize: 13, fontWeight: 600 }}>JD Skills you have ({matchedSkills.length})</span></div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{matchedSkills.length ? matchedSkills.map((s, i) => (<span key={i} style={pill("rgba(0,255,140,0.18)", "#a9ffdc")}>{s}</span>)) : <span style={{ fontSize: 12, opacity: 0.7 }}>No explicit overlap detected.</span>}</div>
                    </div>

                    <div style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}><span>⚠️</span><span style={{ fontSize: 13, fontWeight: 600 }}>Missing skills ({missingSkills.length})</span></div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{missingSkills.length ? missingSkills.map((s, i) => (<span key={i} style={pill("rgba(244,63,94,0.22)", "#fecaca")}>{s}</span>)) : <span style={{ fontSize: 12, opacity: 0.7 }}>Great! No missing skills detected.</span>}</div>
                    </div>

                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}><span>💎</span><span style={{ fontSize: 13, fontWeight: 600 }}>Bonus skills ({extraSkills.length})</span></div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{extraSkills.length ? extraSkills.map((s, i) => (<span key={i} style={pill("rgba(129,140,248,0.25)", "#e0e7ff")}>{s}</span>)) : <span style={{ fontSize: 12, opacity: 0.7 }}>No extra skills detected.</span>}</div>
                    </div>
                  </div>
                </div>
              </div>

              <button onClick={downloadReport} style={{ marginTop: 20, width: "100%", padding: "10px 16px", borderRadius: "999px", border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600, background: "linear-gradient(135deg,#6366f1,#22d3ee)", color: "#020617", boxShadow: "0 0 16px rgba(129,140,248,0.6)" }}>📄 Download ATS PDF Report</button>

              <div style={{ marginTop: 18, padding: "14px 14px 16px", borderRadius: 14, border: "1px solid rgba(34,197,94,0.45)", background: "radial-gradient(circle at top, rgba(22,163,74,0.13), rgba(3,7,18,0.95))", boxShadow: "0 0 20px rgba(34,197,94,0.25)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}><span>🎯</span><span>AI Resume Improvement for this JD</span></div>
                    <div style={{ fontSize: 11, opacity: 0.8, marginTop: 2 }}>Get a tailored summary, skills to add & bullet points based on this role.</div>
                  </div>

                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button onClick={improveResume} disabled={loadingRewrite} style={{ padding: "8px 14px", borderRadius: "999px", border: "none", cursor: loadingRewrite ? "wait" : "pointer", fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", background: "linear-gradient(135deg,#22c55e,#4ade80,#a3e635)", color: "#022c22", boxShadow: "0 0 14px rgba(34,197,94,0.6)" }}>{loadingRewrite ? "Optimizing..." : "Improve Resume"}</button>
                    <button onClick={saveAnalysis} disabled={!token} style={{ padding: "8px 14px", borderRadius: "999px", border: "none", cursor: token ? "pointer" : "not-allowed", fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", background: "linear-gradient(90deg,#00f5d4,#4cc9f0)", color: "#021018", boxShadow: "0 0 10px rgba(4,200,180,0.2)", opacity: token ? 1 : 0.5 }}>💾 Save</button>
                  </div>
                </div>

                {(improvedSummary || skillsToAdd.length > 0 || bulletSuggestions.length > 0) && (
                  <div style={{ marginTop: 12 }}>
                    {improvedSummary && (<div style={{ marginBottom: 10 }}><div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>📌 Improved Summary</div><div style={{ fontSize: 12, lineHeight: 1.5, opacity: 0.95 }}>{improvedSummary}</div></div>)}
                    {skillsToAdd.length > 0 && (<div style={{ marginBottom: 10 }}><div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>✨ Skills to Add</div><div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{skillsToAdd.map((s, i) => (<span key={i} style={pill("rgba(190,242,100,0.15)", "#ecfccb")}>{typeof s === 'object' ? (s.skill || s.name || JSON.stringify(s)) : s}</span>))}</div></div>)}
                    {bulletSuggestions.length > 0 && (<div><div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>💡 Bullet Suggestions</div><ul style={{ fontSize: 12, paddingLeft: 18, margin: 0, opacity: 0.95, lineHeight: 1.6 }}>{bulletSuggestions.map((b, i) => (<li key={i} style={{ marginBottom: 6 }}>{typeof b === 'object' ? (<span><b style={{ color: '#00f5d4' }}>{b.bullet || b.text || JSON.stringify(b)}</b> {b.why && <span style={{ display: 'block', fontSize: 11, opacity: 0.7, marginTop: 2 }}>{b.why}</span>}</span>) : b}</li>))}</ul></div>)}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </main>

      {message && (<div style={{ maxWidth: 1200, margin: "18px auto", padding: 12, borderRadius: 10, background: message.type === "error" ? "rgba(244,63,94,0.12)" : "rgba(0,245,212,0.08)", color: message.type === "error" ? "#ffd1da" : "#bfffe9", border: message.type === "error" ? "1px solid rgba(244,63,94,0.18)" : "1px solid rgba(0,245,212,0.12)", display: "flex", alignItems: "center", gap: 10, animation: "slideIn 0.3s ease-out" }}><span>{message.type === "error" ? "⚠️" : "✅"}</span>{message.text}</div>)}

      <div style={{ maxWidth: 800, margin: "50px auto 0", display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Roadmap Section - Compact List */}
        <div style={{ padding: 20, borderRadius: 12, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 15, background: "linear-gradient(90deg, #00f5d4, #f72585)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", fontWeight: 800, textTransform: "uppercase", letterSpacing: 1 }}>🚀 Coming Soon</h3>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "10px 24px", opacity: 0.8, fontSize: 13 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span>🎙️</span> AI Interview Mockup</div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span>📝</span> Auto Cover Letter</div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span>👔</span> LinkedIn Optimizer</div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span>📈</span> Application Tracker</div>
          </div>
        </div>

        {/* Support Section - Compact Horizontal Bar */}
        <div style={{ padding: "12px 24px", borderRadius: 12, background: "linear-gradient(90deg, rgba(255,215,0,0.1), rgba(0,0,0,0.3))", border: "1px solid rgba(255,215,0,0.2)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16, boxShadow: "0 0 20px rgba(0,0,0,0.2)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 24 }}>☕</div>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, color: "#ffd700", fontWeight: 700 }}>Loved it? Buy me a coffee</h3>
              <p style={{ margin: "4px 0 0", fontSize: 12, opacity: 0.7 }}>Help support the server costs!</p>
            </div>
          </div>
          <button onClick={() => setShowPayment(true)} style={{ padding: "8px 20px", borderRadius: "99px", background: "linear-gradient(135deg, #ffd700, #ffaa00)", color: "#000", fontWeight: 700, border: "none", cursor: "pointer", fontSize: 13, boxShadow: "0 4px 12px rgba(255,215,0,0.3)", whiteSpace: "nowrap" }}>
            Contribute
          </button>
        </div>

      </div>

      <footer style={{ marginTop: 60, textAlign: "center", fontSize: 12, opacity: 0.4 }}>
        Created with ❤️ by <b>Kabir Roy</b> |
        <a href="https://github.com/Kabirroy12345" target="_blank" rel="noopener noreferrer" style={{ color: "#4cc9f0", marginLeft: 6, textDecoration: "none" }}>GitHub</a> |
        <a href="https://www.linkedin.com/in/kabir-roy-01474527a" target="_blank" rel="noopener noreferrer" style={{ color: "#4cc9f0", marginLeft: 6, textDecoration: "none" }}>LinkedIn</a>
      </footer>

      {
        showPayment && (
          <div onClick={() => setShowPayment(false)} style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "rgba(0,0,0,0.8)", backdropFilter: "blur(5px)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 10000 }}>
            <div onClick={(e) => e.stopPropagation()} style={{ width: 350, padding: 30, borderRadius: 24, background: "#0f1218", border: "1px solid rgba(255,215,0,0.3)", textAlign: "center", boxShadow: "0 0 50px rgba(255,215,0,0.15)", position: "relative" }}>
              <button onClick={() => setShowPayment(false)} style={{ position: "absolute", top: 15, right: 15, background: "none", border: "none", color: "#fff", fontSize: 24, cursor: "pointer" }}>×</button>

              <div style={{ fontSize: 40, marginBottom: 10 }}>☕</div>
              <h2 style={{ color: "#ffd700", margin: "0 0 10px", fontSize: 22 }}>Buy me a Coffee</h2>
              <p style={{ margin: "0 0 20px", fontSize: 14, opacity: 0.8, lineHeight: 1.5 }}>
                Scan using <b>GPay</b>, <b>PhonePe</b> or <b>Paytm</b> to contribute.
              </p>

              {/* QR Code Container */}
              <div style={{ background: "#fff", padding: 15, borderRadius: 16, display: "inline-block", marginBottom: 20 }}>
                {/* PUBLIC QR API - REPLACE 'pa' PARAM WITH YOUR VPA */}
                <img
                  src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa=7011171787@ptsbi%26pn=ResumeSaaS%26cu=INR"
                  alt="UPI QR"
                  style={{ width: 180, height: 180, display: "block" }}
                />
              </div>

              <div style={{ fontSize: 12, color: "#888", marginBottom: 20, background: "rgba(255,255,255,0.05)", padding: 8, borderRadius: 8 }}>
                UPI ID: <span style={{ color: "#fff", fontWeight: 600 }}>7011171787@ptsbi</span>
              </div>

              <button onClick={() => { setShowPayment(false); setMessage({ type: "success", text: "Thanks for the support! ❤️" }); }} style={{ width: "100%", padding: "12px", borderRadius: 12, background: "#ffd700", color: "#000", border: "none", fontWeight: 700, cursor: "pointer" }}>
                I made the payment
              </button>
            </div>
          </div>
        )
      }

      <style>{`
        html, body, #root { margin: 0; padding: 0; width: 100%; }
        @keyframes slideIn {
          from { transform: translateY(-20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        @media (max-width: 1024px) { 
          main { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 768px) {
          header { flex-direction: column; gap: 15px; }
          header h1 { font-size: 24px !important; }
          header > div { flex: 1 !important; width: 100%; justify-content: center !important; }
        }
      `}</style>
    </div >
  );
}