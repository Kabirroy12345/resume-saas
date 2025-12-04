// frontend/src/App.jsx

import React, { useState } from "react";

export default function App() {
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

  async function upload() {
    if (!file) return alert("Upload a resume first!");

    setLoadingUpload(true);
    setFinalScore(null); // reset old score when uploading new resume

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/upload-resume", {
        method: "POST",
        body: formData,
      });

      const json = await res.json();

      if (json.parsed) {
        setParsed(json.parsed);
      } else {
        alert("Failed to parse resume.");
      }
    } catch (err) {
      console.error(err);
      alert("Error uploading resume. Check backend console.");
    } finally {
      setLoadingUpload(false);
    }
  }

  async function matchScore() {
    if (!parsed) return alert("Upload & parse a resume first!");
    if (!jd.trim()) return alert("Paste a Job Description!");

    setLoadingScore(true);

    const payload = {
      resume: parsed.full_text || parsed.snippet || "",
      jd: jd,
      skills: parsed.skills || [],
    };

    try {
      const res = await fetch("http://127.0.0.1:8000/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (data.error) {
        alert(data.error);
      } else {
        setFinalScore(data.final_score ?? 0);
        setSkillScore(data.skill_score ?? 0);
        setJdScore(data.jd_similarity_score ?? 0);
        setMatchedSkills(data.matched_jd_skills || []);
        setMissingSkills(data.missing_skills || []);
        setExtraSkills(data.resume_extra_skills || []);
        setRole(data.role || null);
      }
    } catch (err) {
      console.error(err);
      alert("Error calculating score. Check backend console.");
    } finally {
      setLoadingScore(false);
    }
  }

  const hasScore = finalScore !== null;

  const neonCard = {
    background:
      "radial-gradient(circle at top, rgba(0,255,170,0.12), transparent 60%), #070b10",
    borderRadius: "18px",
    border: "1px solid rgba(0,255,170,0.25)",
    boxShadow:
      "0 0 25px rgba(0,255,170,0.25), 0 0 60px rgba(0,150,255,0.25)",
    padding: "24px 26px",
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
    background: hasScore
      ? `conic-gradient(#01ff8b ${finalScore}%, #181818 0)`
      : "conic-gradient(#444 0, #181818 0)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 0 40px rgba(0,255,140,0.4)",
  };

  const scoreInner = {
    width: 140,
    height: 140,
    borderRadius: "50%",
    background: "#05070c",
    border: "2px solid rgba(255,255,255,0.05)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    color: "#e8fff9",
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        margin: 0,
        padding: "32px 20px",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        background:
          "radial-gradient(circle at 0 0, #1d3557 0, transparent 55%), radial-gradient(circle at 100% 100%, #2a9d8f 0, #02030a 55%)",
        color: "#f5f5ff",
      }}
    >
      {/* Header */}
      <header
        style={{
          maxWidth: 1150,
          margin: "0 auto 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 32,
              fontWeight: 800,
              letterSpacing: 0.5,
              margin: 0,
            }}
          >
            <span style={{ color: "#00f5d4" }}>Resume</span>{" "}
            <span style={{ color: "#f72585" }}>Match</span>{" "}
            <span style={{ color: "#4cc9f0" }}>Engine</span>
          </h1>
          <p style={{ marginTop: 6, opacity: 0.8, fontSize: 14 }}>
            AI-powered resume vs job-description scoring with neon vibes ⚡
          </p>
        </div>

        <div
          style={{
            fontSize: 12,
            padding: "6px 12px",
            borderRadius: "999px",
            border: "1px solid rgba(255,255,255,0.25)",
            background: "rgba(3,7,18,0.65)",
          }}
        >
          Local Dev •{" "}
          <span style={{ color: "#4cc9f0" }}>http://127.0.0.1:8000</span>
        </div>
      </header>

      {/* Layout */}
      <main
        style={{
          maxWidth: 1150,
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1fr)",
          gap: 22,
        }}
      >
        {/* LEFT: Resume Upload & Parsed Details */}
        <section style={neonCard}>
          {/* Upload block */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 18,
            }}
          >
            <label
              style={{
                padding: "9px 14px",
                borderRadius: "999px",
                border: "1px solid rgba(255,255,255,0.18)",
                background: "rgba(5,8,15,0.9)",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              📄 Choose PDF Resume
              <input
                type="file"
                accept="application/pdf"
                style={{ display: "none" }}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>

            <span style={{ fontSize: 13, opacity: 0.85 }}>
              {file ? file.name : "No file selected"}
            </span>

            <button
              onClick={upload}
              disabled={!file || loadingUpload}
              style={{
                marginLeft: "auto",
                padding: "9px 18px",
                borderRadius: "999px",
                border: "none",
                cursor: file && !loadingUpload ? "pointer" : "not-allowed",
                fontSize: 13,
                fontWeight: 600,
                background:
                  "linear-gradient(135deg, #00f5d4, #00bbf9, #f72585)",
                color: "#050816",
                boxShadow: "0 0 18px rgba(0,245,212,0.45)",
                opacity: file ? 1 : 0.5,
                transition: "transform 0.08s ease, box-shadow 0.08s ease",
              }}
            >
              {loadingUpload ? "Parsing..." : "Upload & Parse"}
            </button>
          </div>

          {/* Parsed details */}
          {parsed ? (
            <div style={{ marginTop: 8 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <span style={{ fontSize: 22 }}>👤</span>
                <div>
                  <div
                    style={{ fontSize: 18, fontWeight: 600, color: "#e9fffc" }}
                  >
                    {parsed.name || "Name not detected"}
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    AI-extracted from your resume header
                  </div>
                </div>
              </div>

              <div style={{ fontSize: 14, marginTop: 8 }}>
                <p style={{ margin: "4px 0" }}>
                  <b>📧 Email:</b>{" "}
                  <span style={{ opacity: 0.9 }}>
                    {parsed.emails?.length
                      ? parsed.emails.join(", ")
                      : "Not detected"}
                  </span>
                </p>
                <p style={{ margin: "4px 0" }}>
                  <b>📞 Phone:</b>{" "}
                  <span style={{ opacity: 0.9 }}>
                    {parsed.phones?.length
                      ? parsed.phones.join(", ")
                      : "Not detected"}
                  </span>
                </p>
              </div>

              {/* Skills */}
              <div style={{ marginTop: 16 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <span>✨</span>
                  <h3 style={{ margin: 0, fontSize: 15 }}>Skills detected</h3>
                </div>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 8,
                    marginTop: 6,
                  }}
                >
                  {parsed.skills?.length ? (
                    parsed.skills.map((s, i) => (
                      <span
                        key={i}
                        style={pill(
                          "linear-gradient(135deg,#00bbf9,#4cc9f0)",
                          "#021015"
                        )}
                      >
                        {s}
                      </span>
                    ))
                  ) : (
                    <span style={{ fontSize: 13, opacity: 0.7 }}>
                      No skills detected from resume text.
                    </span>
                  )}
                </div>
              </div>

              {/* Snippet */}
              <div style={{ marginTop: 18 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 6,
                  }}
                >
                  <span>📄</span>
                  <h3 style={{ margin: 0, fontSize: 15 }}>Profile Snippet</h3>
                </div>
                <p
                  style={{
                    fontSize: 13,
                    opacity: 0.9,
                    maxHeight: 140,
                    overflow: "auto",
                    paddingRight: 6,
                  }}
                >
                  {parsed.snippet}
                </p>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 13, opacity: 0.75, marginTop: 12 }}>
              👈 Upload a PDF resume to see extracted name, contacts & skills.
            </div>
          )}
        </section>

        {/* RIGHT: JD + Scoring */}
        <section style={neonCard}>
          {/* JD input */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 8,
            }}
          >
            <span>📑</span>
            <h3 style={{ margin: 0, fontSize: 15 }}>Job Description</h3>
          </div>
          <textarea
            placeholder="Paste the JD here (role, responsibilities, required skills)..."
            value={jd}
            onChange={(e) => setJD(e.target.value)}
            style={{
              width: "100%",
              minHeight: 140,
              resize: "vertical",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.16)",
              background: "rgba(2,6,23,0.9)",
              color: "#e9fffd",
              padding: "10px 12px",
              fontSize: 13,
              outline: "none",
              boxShadow: "0 0 0 1px rgba(0,0,0,0.4)",
            }}
          />

          <button
            onClick={matchScore}
            disabled={loadingScore}
            style={{
              marginTop: 14,
              padding: "10px 18px",
              borderRadius: "999px",
              border: "none",
              cursor: !loadingScore ? "pointer" : "wait",
              fontSize: 14,
              fontWeight: 600,
              background: "linear-gradient(135deg,#00ffb3,#42a5f5,#f72585)",
              color: "#050816",
              boxShadow: "0 0 24px rgba(0,255,179,0.5)",
            }}
          >
            {loadingScore ? "Analyzing match..." : "Calculate Match Score"}
          </button>

          {/* Score display */}
          {hasScore && (
            <div
              style={{
                marginTop: 22,
                display: "grid",
                gridTemplateColumns: "auto 1fr",
                gap: 18,
                alignItems: "center",
              }}
            >
              {/* Neon score donut */}
              <div style={scoreCircle}>
                <div style={scoreInner}>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Match Score</div>
                  <div
                    style={{
                      fontSize: 32,
                      fontWeight: 800,
                      marginTop: 4,
                      color: "#00ffb3",
                    }}
                  >
                    {finalScore.toFixed(2)}%
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      marginTop: 4,
                      opacity: 0.65,
                      textAlign: "center",
                    }}
                  >
                    {role || "Role detected from JD"}
                  </div>
                </div>
              </div>

              {/* Breakdown */}
              <div>
                <div style={{ fontSize: 14, marginBottom: 10 }}>
                  <span style={{ marginRight: 6 }}>🧠</span>
                  <b>Score Breakdown</b>
                </div>

                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                    fontSize: 13,
                  }}
                >
                  <div>
                    <span style={{ opacity: 0.8 }}>Skill Match:</span>{" "}
                    <b style={{ color: "#00ffb3" }}>
                      {skillScore.toFixed(2)}%
                    </b>{" "}
                    <span style={{ opacity: 0.6 }}>(max 70%)</span>
                  </div>
                  <div>
                    <span style={{ opacity: 0.8 }}>JD Similarity:</span>{" "}
                    <b style={{ color: "#4cc9f0" }}>
                      {jdScore.toFixed(2)}%
                    </b>{" "}
                    <span style={{ opacity: 0.6 }}>(max 30%)</span>
                  </div>
                </div>

                {/* Matched skills */}
                <div style={{ marginTop: 14 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      marginBottom: 4,
                    }}
                  >
                    <span>✅</span>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>
                      JD Skills you already have
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 6,
                    }}
                  >
                    {matchedSkills.length ? (
                      matchedSkills.map((s, i) => (
                        <span
                          key={i}
                          style={pill("rgba(0,255,140,0.18)", "#a9ffdc")}
                        >
                          {s}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: 12, opacity: 0.7 }}>
                        No explicit overlap detected from JD wording.
                      </span>
                    )}
                  </div>
                </div>

                {/* Missing skills */}
                <div style={{ marginTop: 12 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      marginBottom: 4,
                    }}
                  >
                    <span>⚠️</span>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>
                      Important skills missing for this JD
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 6,
                    }}
                  >
                    {missingSkills.length ? (
                      missingSkills.map((s, i) => (
                        <span
                          key={i}
                          style={pill("rgba(244,63,94,0.22)", "#fecaca")}
                        >
                          {s}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: 12, opacity: 0.7 }}>
                        Great! No strong missing skills detected from JD text.
                      </span>
                    )}
                  </div>
                </div>

                {/* Extra skills */}
                <div style={{ marginTop: 12 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      marginBottom: 4,
                    }}
                  >
                    <span>💎</span>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>
                      Bonus skills in your resume
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 6,
                    }}
                  >
                    {extraSkills.length ? (
                      extraSkills.map((s, i) => (
                        <span
                          key={i}
                          style={pill("rgba(129,140,248,0.25)", "#e0e7ff")}
                        >
                          {s}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: 12, opacity: 0.7 }}>
                        No extra skills beyond JD keywords detected.
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}


