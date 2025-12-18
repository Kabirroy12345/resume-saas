import { useState } from 'react';

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    username: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    const endpoint = isLogin ? '/auth/login' : '/auth/register';
    const payload = isLogin
      ? { email: formData.email, password: formData.password }
      : formData;

    // FOOLPROOF FIX: Force 127.0.0.1 to avoid localhost IPv6 issues
    const baseUrl = (import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL.startsWith('http'))
      ? import.meta.env.VITE_API_URL
      : "/api";
    const fullUrl = baseUrl.startsWith('http')
      ? new URL(endpoint, baseUrl).href
      : `${baseUrl}${endpoint}`.replace(/\/+/g, '/');


    console.log("v1.5 Auth Request:", fullUrl); // Version tagged log

    try {
      console.log("Full Login URL:", fullUrl); // DEBUG: Log to console

      // Add 60s timeout for cold starts
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);

      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      const data = await response.json();

      if (!response.ok) {
        // DEBUG: Alert the user to the exact error URL if it fails
        // This helps verify if the double slash fix is actually applied on Vercel
        console.error("Login failed:", data);
        setError(data.detail || 'Something went wrong');
        // alert(`Debug Error: Failed to reach ${fullUrl}\nDetails: ${data.detail}`); 
        return;
      }

      setSuccess(isLogin ? 'Login successful! 🎉' : 'Account created! Welcome! 🚀');
      localStorage.setItem('token', data.access_token);

      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError("Request timed out (Server Sleeping). Please try again in 30s.");
      } else {
        // Use baseUrl instead of API_BASE if API_BASE is not defined
        const urlToCheck = typeof baseUrl !== 'undefined' ? baseUrl : "backend";
        console.error("Network Error Details:", err);
        const detailedError = err.message || "Unknown error";
        setError(`Network error. Ensure backend is running at ${baseUrl}. (Detail: ${detailedError})`);
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setSuccess('');
    setFormData({ email: '', password: '', username: '' });
  };

  return (
    <div className="auth-container">
      <div className="background">
        <div className="glow glow-1"></div>
        <div className="glow glow-2"></div>
        <div className="glow glow-3"></div>
      </div>

      <div className="auth-card">
        <div className="header">
          <div className="logo">⚡</div>
          <h1>Resume Match Engine</h1>
          <p className="subtitle">AI-Powered Resume Scoring</p>
        </div>

        <div className="form">
          <div className="form-header">
            <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
            <p>{isLogin ? 'Sign in to your account' : 'Join the revolution'}</p>
          </div>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}

          <div className="input-group">
            {!isLogin && (
              <div className="input-wrapper">
                <label htmlFor="username">Username</label>
                <input
                  id="username"
                  type="text"
                  name="username"
                  placeholder="Choose your username"
                  value={formData.username}
                  onChange={handleChange}
                  required={!isLogin}
                />
                <div className="input-glow"></div>
              </div>
            )}

            <div className="input-wrapper">
              <label htmlFor="email">Email Address</label>
              <input
                id="email"
                type="email"
                name="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                required
              />
              <div className="input-glow"></div>
            </div>

            <div className="input-wrapper">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                name="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                required
              />
              <div className="input-glow"></div>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="submit-btn"
          >
            <span className="btn-text">
              {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Create Account')}
            </span>
          </button>
        </div>

        <div className="toggle-section">
          <p>
            {isLogin ? "Don't have an account? " : 'Already have an account? '}
            <button
              onClick={toggleMode}
              className="toggle-btn"
            >
              {isLogin ? 'Sign Up' : 'Sign In'}
            </button>
          </p>
        </div>

        <div className="features">
          <div className="feature">
            <span className="icon">🎯</span>
            <span>Smart Matching</span>
          </div>
          <div className="feature">
            <span className="icon">🔒</span>
            <span>Secure Login</span>
          </div>
          <div className="feature">
            <span className="icon">⚡</span>
            <span>Fast Results</span>
          </div>
        </div>
      </div>

      <style>{`
        /* FIXED CSS - Scroll Enabled */
        html, body, #root {
          margin: 0;
          padding: 0;
          width: 100%;
          min-height: 100vh; /* Changed from height: 100% */
        }

        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        .auth-container {
          width: 100%;
          min-height: 100vh; /* Changed from fixed 100vh */
          display: flex;
          justify-content: center;
          align-items: center;
          background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1628 100%);
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          padding: 20px; /* Added padding for mobile */
          position: relative; /* Changed from fixed */
          overflow-y: auto; /* Enable vertical scroll */
          overflow-x: hidden; /* Prevent horizontal scroll */
        }

        .background {
          position: fixed; /* Keep background fixed */
          width: 100vw;
          height: 100vh;
          top: 0;
          left: 0;
          z-index: 1;
          pointer-events: none; /* Allow clicks through */
        }

        .glow {
          position: absolute;
          border-radius: 50%;
          opacity: 0.15;
          filter: blur(80px);
          animation: float 8s ease-in-out infinite;
        }

        .glow-1 {
          width: 400px;
          height: 400px;
          background: #00ff88;
          top: -100px;
          left: -100px;
        }

        .glow-2 {
          width: 300px;
          height: 300px;
          background: #ff006e;
          top: 50%;
          right: -50px;
          animation-delay: 2s;
        }

        .glow-3 {
          width: 350px;
          height: 350px;
          background: #00d9ff;
          bottom: -100px;
          left: 50%;
          animation-delay: 4s;
        }

        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(30px); }
        }

        .auth-card {
          position: relative;
          z-index: 10;
          background: rgba(20, 25, 50, 0.95);
          backdrop-filter: blur(20px);
          border: 2px solid rgba(0, 255, 136, 0.3);
          border-radius: 20px;
          padding: 60px 50px;
          width: 100%;
          max-width: 450px;
          box-shadow: 
            0 8px 32px rgba(0, 255, 136, 0.1),
            0 0 60px rgba(0, 255, 136, 0.05),
            inset 0 0 40px rgba(0, 255, 136, 0.05);
          animation: slideUp 0.6s ease-out;
          margin: 20px 0; /* Added margin for spacing */
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(40px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .header {
          text-align: center;
          margin-bottom: 40px;
        }

        .logo {
          font-size: 48px;
          margin-bottom: 15px;
          display: inline-block;
          animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }

        .header h1 {
          color: #00ff88;
          font-size: 28px;
          margin-bottom: 5px;
          font-weight: 700;
          text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        }

        .subtitle {
          color: #00d9ff;
          font-size: 13px;
          letter-spacing: 2px;
          text-transform: uppercase;
        }

        .form-header {
          margin-bottom: 35px;
        }

        .form-header h2 {
          color: #fff;
          font-size: 24px;
          margin-bottom: 8px;
        }

        .form-header p {
          color: #99b3cc;
          font-size: 14px;
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 20px;
          margin-bottom: 30px;
        }

        .input-wrapper {
          position: relative;
        }

        .input-wrapper label {
          display: block;
          color: #00ff88;
          font-size: 12px;
          font-weight: 600;
          margin-bottom: 8px;
          letter-spacing: 1px;
          text-transform: uppercase;
        }

        .input-wrapper input {
          width: 100%;
          padding: 14px 16px;
          background: rgba(0, 255, 136, 0.05);
          border: 2px solid rgba(0, 255, 136, 0.3);
          color: #fff;
          border-radius: 10px;
          font-size: 14px;
          transition: all 0.3s ease;
        }

        .input-wrapper input::placeholder {
          color: rgba(255, 255, 255, 0.4);
        }

        .input-wrapper input:focus {
          outline: none;
          border-color: #00ff88;
          background: rgba(0, 255, 136, 0.1);
          box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }

        .input-glow {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 2px;
          background: linear-gradient(90deg, transparent, #00ff88, transparent);
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .input-wrapper input:focus ~ .input-glow {
          opacity: 1;
        }

        .error-message {
          background: rgba(255, 0, 100, 0.15);
          border: 1px solid #ff006e;
          color: #ff6b9d;
          padding: 12px;
          border-radius: 8px;
          font-size: 13px;
          margin-bottom: 20px;
          animation: shake 0.5s ease;
        }

        .success-message {
          background: rgba(0, 255, 136, 0.15);
          border: 1px solid #00ff88;
          color: #00ff88;
          padding: 12px;
          border-radius: 8px;
          font-size: 13px;
          margin-bottom: 20px;
        }

        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }

        .submit-btn {
          width: 100%;
          padding: 14px;
          background: linear-gradient(135deg, #00ff88 0%, #00d9ff 100%);
          color: #000;
          border: none;
          border-radius: 10px;
          font-weight: 700;
          font-size: 15px;
          cursor: pointer;
          transition: all 0.3s ease;
          position: relative;
          overflow: hidden;
          letter-spacing: 1px;
        }

        .submit-btn:hover:not(:disabled) {
          box-shadow: 0 0 30px rgba(0, 255, 136, 0.5);
          transform: translateY(-2px);
        }

        .submit-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .toggle-section {
          text-align: center;
          margin-top: 25px;
          padding-top: 25px;
          border-top: 1px solid rgba(0, 255, 136, 0.2);
        }

        .toggle-section p {
          color: #99b3cc;
          font-size: 14px;
        }

        .toggle-btn {
          background: none;
          border: none;
          color: #00ff88;
          cursor: pointer;
          font-weight: 600;
          font-size: 14px;
          transition: all 0.3s ease;
          position: relative;
        }

        .toggle-btn:hover {
          text-decoration: underline;
        }

        .features {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 15px;
          margin-top: 30px;
        }

        .feature {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 15px;
          background: rgba(0, 255, 136, 0.05);
          border: 1px solid rgba(0, 255, 136, 0.2);
          border-radius: 8px;
          transition: all 0.3s ease;
        }

        .feature:hover {
          background: rgba(0, 255, 136, 0.1);
          border-color: rgba(0, 255, 136, 0.4);
        }

        .feature .icon {
          font-size: 24px;
        }

        .feature span:last-child {
          color: #99b3cc;
          font-size: 11px;
          text-align: center;
          font-weight: 500;
        }

        @media (max-width: 600px) {
          .auth-container {
            padding: 10px; /* Reduced padding on mobile */
            align-items: flex-start; /* Start from top on mobile */
            padding-top: 40px; /* Add top padding */
          }

          .auth-card {
            margin: 0 auto;
            padding: 40px 25px;
            max-width: 95%;
            margin-top: 20px;
            margin-bottom: 40px; /* Space at bottom */
          }

          .header h1 {
            font-size: 22px;
          }

          .form-header h2 {
            font-size: 20px;
          }

          .features {
            grid-template-columns: 1fr;
          }
        }

        /* Extra small screens */
        @media (max-width: 400px) {
          .auth-card {
            padding: 30px 20px;
          }
          
          .header h1 {
            font-size: 20px;
          }
          
          .form-header h2 {
            font-size: 18px;
          }
        }
      `}</style>
    </div>
  );
}