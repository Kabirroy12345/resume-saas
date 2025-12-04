import { useState } from "react";

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  async function upload() {
    if (!file) return alert("Choose a file first!");
    const f = new FormData();
    f.append("file", file);
    const res = await fetch("http://127.0.0.1:8000/upload-resume", {
      method: "POST",
      body: f
    });
    const data = await res.json();
    setResult(data);
  }

  return (
    <div style={{ padding: 20 }}>
      <h2>Resume SaaS Upload</h2>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={upload}>Upload & Parse</button>

      {result && (
        <pre style={{ background: "#eee", padding: 10 }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}

