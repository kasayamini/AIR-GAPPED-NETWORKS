Deployment steps and required credentials

Frontend (Vercel):
- Create a Vercel project pointing to the `frontend` folder.
- Set the `VITE_API_BASE` environment variable in Vercel to the backend URL (e.g., `https://<your-backend>.onrender.com`).
- Build command: `npm run build` (Vercel auto-build will run this).

Backend (Render):
- Create a new Web Service on Render and connect the repo.
- Use the `render.yaml` manifest or configure manually:
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Set environment variables (in Render):
  - `OLLAMA_URL`: URL to Ollama server (if using Ollama) or leave default for local
  - `OLLAMA_MODEL`: model name

Credentials required:
- Vercel: You must authorize Vercel to access your Git repository and set `VITE_API_BASE`.
- Render: Authorize Render to access your Git repository and set `OLLAMA` environment variables if needed.
