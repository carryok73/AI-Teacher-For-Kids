# AI Teacher for Kids

AI Teacher for Kids is an AI-powered learning platform for KG to Grade 3 students. It includes a voice-enabled virtual teacher, adaptive lessons, guided Q&A, gamified quizzes, progress tracking, and a parent/teacher dashboard.

## Excellent Features Added

- Socratic tutor mode: guides children with hints instead of directly giving answers.
- Adaptive learning path: lesson difficulty changes based on quiz score and confidence.
- Animated teacher avatar: reacts while listening, speaking, and celebrating.
- Voice interaction: browser speech recognition and speech synthesis.
- Parent/teacher dashboard: progress, stars, mastery, and recent activity.
- Safety-first teaching: age-appropriate tone, short answers, no sensitive content.
- Offline demo mode: works without an API key using built-in lesson logic.
- OpenAI-ready mode: uses `OPENAI_API_KEY` automatically when provided.

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python, FastAPI
- AI: OpenAI API ready, LangChain dependency included
- Voice: Browser Web Speech API, SpeechRecognition and gTTS dependencies
- Database: SQLite for demo, MySQL schema included for deployment

## Run Locally

Instant no-install demo:

```bash
python simple_server.py
```

Open:

```text
http://127.0.0.1:8000
```

Full FastAPI version:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Optional OpenAI setup:

```bash
set OPENAI_API_KEY=your_api_key_here
```

## Deploy Online With Render

Render is the easiest option for this project because it can run the FastAPI backend and serve the HTML/CSS/JavaScript frontend from the same web service.

### 1. Prepare the project

Make sure these files exist in the project root:

```text
requirements.txt
Procfile
runtime.txt
render.yaml
app/main.py
```

They are already included.

### 2. Create a GitHub repository

```bash
git init
git add .
git commit -m "Initial AI Teacher for Kids deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-teacher-kids.git
git push -u origin main
```

If Git says the folder is already a repository, only run:

```bash
git add .
git commit -m "Prepare app for deployment"
git push
```

### 3. Create the Render web service

1. Go to https://render.com
2. Sign in with GitHub.
3. Click **New +**.
4. Choose **Web Service**.
5. Select your `ai-teacher-kids` GitHub repository.
6. Use these settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /api/health
```

### 4. Add environment variables

In Render, open your service, go to **Environment**, and add:

```text
APP_ENV=production
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key_here
```

`OPENAI_API_KEY` is optional. Without it, the project still works in built-in demo tutor mode.

### 5. Deploy and test

After deployment finishes, open the Render URL. Test these:

```text
https://YOUR-APP.onrender.com
https://YOUR-APP.onrender.com/api/health
https://YOUR-APP.onrender.com/docs
```

The `/docs` page is FastAPI's automatic API documentation.

## Optional Docker Deployment

This project also includes a `Dockerfile`.

Build locally:

```bash
docker build -t ai-teacher-kids .
```

Run locally:

```bash
docker run -p 8000:8000 -e PORT=8000 ai-teacher-kids
```

Open:

```text
http://127.0.0.1:8000
```

## Deployment Notes

- The current app uses SQLite for a simple hosted demo.
- On free hosting, SQLite data may reset after redeploys or restarts.
- For a final college/company-level version, connect MySQL or PostgreSQL.
- The included `database/mysql_schema.sql` gives the MySQL table design.
- Do not commit your real `.env` or API keys to GitHub.

## Project Structure

```text
ai-teacher-kids/
  Dockerfile
  Procfile
  render.yaml
  app/
    main.py
    static/
      css/styles.css
      js/app.js
    templates/
      index.html
  database/
    mysql_schema.sql
  requirements.txt
  README.md
```

## Resume-Friendly Summary

Developed an AI-powered personalized learning platform for primary school students using Python, FastAPI, OpenAI API, LangChain-ready architecture, voice interaction, animated teacher avatars, gamified quizzes, and database-backed progress tracking.
