Deployment notes — Render (recommended)

1) Prepare repository
- Ensure all project files are committed to a Git repository (create a new GitHub repo and push).
- Include `Procfile` (web: gunicorn app:app) and `requirements.txt` with `gunicorn`.

2) Create GitHub repo and push
- git init
- git add .
- git commit -m "Initial"
- git remote add origin <your-github-repo-url>
- git push -u origin main

3) Deploy to Render (free tier available)
- Create an account at https://render.com
- Click "New" → "Web Service"
- Connect your GitHub account and select the repo
- Build command: (leave blank)
- Start command: `gunicorn app:app`
- Set environment variables in Render dashboard (Environment → Environment Variables):
  - `SECRET_KEY` (a random secret for Flask sessions)
  - `AI_API_KEY` (if you want AI features; store securely)
- Deploy — Render will build using `requirements.txt` and start your service.

4) Use custom domain (optional)
- In Render dashboard, go to your service → Settings → Custom Domains
- Add your domain and follow provider instructions to point DNS to Render.

5) Quick local test
- Create and activate a venv
- pip install -r requirements.txt
- python app.py
- Open http://localhost:5000

If you want, I can:
- Prepare a small `deploy.sh` script to automate git commit & push.
- Walk you through creating the GitHub repo and connecting Render step-by-step.
