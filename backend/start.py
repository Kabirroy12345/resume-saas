"""
Start script for Render deployment.
This ensures the PORT environment variable is properly read.
"""
import sys
import os

# Print immediately before any heavy imports
print("=" * 50, flush=True)
print("🔧 start.py is running!", flush=True)
print(f"PORT env variable: {os.environ.get('PORT', 'NOT SET')}", flush=True)
print("=" * 50, flush=True)
sys.stdout.flush()

# Now import uvicorn
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting server on 0.0.0.0:{port}...", flush=True)
    sys.stdout.flush()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
