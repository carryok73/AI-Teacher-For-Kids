import json
import os
import random
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency for demo mode
    OpenAI = None


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "ai_teacher.db"
load_dotenv(BASE_DIR.parent / ".env")

app = FastAPI(
    title="AI Teacher for Kids",
    description="Voice-enabled AI learning platform for KG to Grade 3 children.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


SUBJECTS: dict[str, dict[str, Any]] = {
    "math": {
        "name": "Math",
        "topics": ["Counting", "Addition", "Subtraction", "Shapes", "Patterns"],
        "starter": "Start by touching or counting real objects. Numbers become friendly when we can see them.",
        "sample_questions": [
            ("What is 2 + 3?", ["4", "5", "6", "7"], "5"),
            ("Which shape has 3 sides?", ["Circle", "Triangle", "Square", "Star"], "Triangle"),
            ("What comes after 8?", ["7", "8", "9", "10"], "9"),
        ],
    },
    "english": {
        "name": "English",
        "topics": ["Phonics", "Sight Words", "Rhyming", "Story Time", "Vocabulary"],
        "starter": "Read slowly, listen to sounds, and try one small word at a time.",
        "sample_questions": [
            ("Which word rhymes with cat?", ["sun", "hat", "dog", "pen"], "hat"),
            ("Which is a vowel?", ["b", "t", "a", "m"], "a"),
            ("Choose the correct sentence.", ["I am happy.", "I happy am.", "Happy I am.", "Am happy I."], "I am happy."),
        ],
    },
    "science": {
        "name": "Science",
        "topics": ["Plants", "Animals", "Weather", "Human Body", "Light"],
        "starter": "Science begins with noticing. Look, ask, test, and tell what changed.",
        "sample_questions": [
            ("What do plants need to grow?", ["Only toys", "Sunlight and water", "Shoes", "Books"], "Sunlight and water"),
            ("Which body part helps us see?", ["Eyes", "Feet", "Ears", "Hands"], "Eyes"),
            ("Rain comes from which?", ["Clouds", "Rocks", "Chairs", "Pencils"], "Clouds"),
        ],
    },
    "gk": {
        "name": "General Knowledge",
        "topics": ["My Family", "Community Helpers", "Good Habits", "Festivals", "Our Country"],
        "starter": "General knowledge helps us understand people, places, and the world around us.",
        "sample_questions": [
            ("Who helps sick people?", ["Doctor", "Chef", "Pilot", "Painter"], "Doctor"),
            ("Which habit keeps hands clean?", ["Washing hands", "Throwing books", "Skipping sleep", "Breaking toys"], "Washing hands"),
            ("What do we use to tell time?", ["Clock", "Plate", "Ball", "Spoon"], "Clock"),
        ],
    },
}


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    grade: str = Field(default="Grade 1", max_length=20)


class ChatRequest(BaseModel):
    student_id: int
    subject: str
    message: str = Field(min_length=1, max_length=500)
    mode: str = "guided"


class QuizRequest(BaseModel):
    student_id: int
    subject: str
    topic: str = "Mixed Practice"


class AnswerRequest(BaseModel):
    student_id: int
    subject: str
    topic: str
    question: str
    selected: str
    correct: str


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                grade TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'starter',
                stars INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS learning_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                event_type TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
            """
        )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, "subjects": SUBJECTS})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai-teacher-kids",
        "environment": os.getenv("APP_ENV", "development"),
    }


@app.post("/api/students")
def create_student(payload: StudentCreate) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO students (name, grade, created_at) VALUES (?, ?, ?)",
            (payload.name.strip(), payload.grade.strip(), now),
        )
        student_id = cur.lastrowid
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return {"student": dict(student)}


@app.get("/api/subjects")
def subjects() -> dict[str, Any]:
    return {"subjects": SUBJECTS}


@app.get("/api/progress/{student_id}")
def progress(student_id: int) -> dict[str, Any]:
    with db() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        events = conn.execute(
            """
            SELECT subject, topic, event_type, score, details, created_at
            FROM learning_events
            WHERE student_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (student_id,),
        ).fetchall()
    subject_scores: dict[str, list[int]] = {}
    for event in events:
        subject_scores.setdefault(event["subject"], []).append(event["score"])
    mastery = {
        subject: round(sum(scores) / max(len(scores), 1))
        for subject, scores in subject_scores.items()
    }
    return {
        "student": dict(student),
        "events": [dict(row) for row in events],
        "mastery": mastery,
        "recommendation": recommend_next_step(dict(student), mastery),
    }


@app.post("/api/lesson")
def lesson(payload: QuizRequest) -> dict[str, Any]:
    subject = ensure_subject(payload.subject)
    material = SUBJECTS[subject]
    topic = payload.topic if payload.topic != "Mixed Practice" else random.choice(material["topics"])
    explanation = (
        f"Today we are learning {topic} in {material['name']}. "
        f"{material['starter']} Try one example, say what you notice, then answer a tiny question."
    )
    log_event(payload.student_id, subject, topic, "lesson", 10, explanation)
    return {
        "subject": subject,
        "topic": topic,
        "explanation": explanation,
        "micro_task": make_micro_task(subject, topic),
    }


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict[str, Any]:
    subject = ensure_subject(payload.subject)
    answer = generate_tutor_reply(payload.student_id, subject, payload.message, payload.mode)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO conversations (student_id, subject, question, answer, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.student_id, subject, payload.message, answer, datetime.utcnow().isoformat()),
        )
    log_event(payload.student_id, subject, "Doubt Solving", "chat", 5, payload.message)
    return {"answer": answer, "avatar_mood": choose_mood(answer)}


@app.post("/api/quiz")
def quiz(payload: QuizRequest) -> dict[str, Any]:
    subject = ensure_subject(payload.subject)
    questions = SUBJECTS[subject]["sample_questions"].copy()
    random.shuffle(questions)
    question, options, correct = questions[0]
    return {
        "subject": subject,
        "topic": payload.topic,
        "question": question,
        "options": options,
        "correct": correct,
        "hint": build_hint(question, correct),
    }


@app.post("/api/answer")
def answer(payload: AnswerRequest) -> dict[str, Any]:
    is_correct = normalize(payload.selected) == normalize(payload.correct)
    score = 100 if is_correct else 35
    stars = 3 if is_correct else 1
    feedback = (
        "Wonderful thinking! You earned 3 stars. Tell me how you solved it."
        if is_correct
        else f"Good try. The answer is {payload.correct}. Let's notice the clue and try one more."
    )
    with db() as conn:
        conn.execute(
            """
            UPDATE students
            SET stars = stars + ?, streak = CASE WHEN ? THEN streak + 1 ELSE 0 END,
                level = CASE WHEN streak >= 4 THEN 'builder' ELSE level END
            WHERE id = ?
            """,
            (stars, 1 if is_correct else 0, payload.student_id),
        )
    log_event(payload.student_id, payload.subject, payload.topic, "quiz", score, payload.question)
    return {"correct": is_correct, "score": score, "stars": stars, "feedback": feedback}


def ensure_subject(subject: str) -> str:
    key = subject.lower().strip()
    if key not in SUBJECTS:
        raise HTTPException(status_code=400, detail="Unknown subject")
    return key


def generate_tutor_reply(student_id: int, subject: str, message: str, mode: str) -> str:
    student = get_student(student_id)
    fallback = local_tutor_reply(student["name"], student["grade"], subject, message, mode)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return fallback

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a warm AI teacher for KG to Grade 3 children. "
                        "Use short age-appropriate sentences. Prefer hints, examples, "
                        "and questions over direct answers. Never discuss unsafe adult content. "
                        "Celebrate effort and ask one tiny follow-up question."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Student: {student['name']}, {student['grade']}. "
                        f"Subject: {SUBJECTS[subject]['name']}. Mode: {mode}. "
                        f"Question: {message}"
                    ),
                },
            ],
            temperature=0.5,
            max_tokens=170,
        )
        return response.choices[0].message.content or fallback
    except Exception:
        return fallback


def local_tutor_reply(name: str, grade: str, subject: str, message: str, mode: str) -> str:
    clean = message.lower()
    subject_name = SUBJECTS[subject]["name"]
    if any(word in clean for word in ["answer", "solve", "homework"]):
        return (
            f"Let's learn it together, {name}. I will give a hint first. "
            f"In {subject_name}, find the important clue, try one small step, "
            "then tell me your guess. What do you notice?"
        )
    if subject == "math":
        return "Use your fingers or draw dots. Count slowly, then check once more. What number did you reach?"
    if subject == "english":
        return "Say the word aloud and listen to the first sound. Can you find another word with the same sound?"
    if subject == "science":
        return "Great question. Scientists look carefully, make a guess, and test it. What can you observe around you?"
    return "That is a smart question. Let us connect it to daily life. Can you give me one example you have seen?"


def get_student(student_id: int) -> sqlite3.Row:
    with db() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def log_event(student_id: int, subject: str, topic: str, event_type: str, score: int, details: str) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO learning_events (student_id, subject, topic, event_type, score, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, subject, topic, event_type, score, details, datetime.utcnow().isoformat()),
        )


def recommend_next_step(student: dict[str, Any], mastery: dict[str, int]) -> str:
    if not mastery:
        return "Start with a short Math or English warm-up lesson."
    weakest = min(mastery, key=mastery.get)
    if mastery[weakest] < 50:
        return f"Revise {SUBJECTS[weakest]['name']} with visual examples and two easy quiz questions."
    return "Move to a slightly harder mixed quiz and keep the learning streak alive."


def make_micro_task(subject: str, topic: str) -> str:
    tasks = {
        "math": f"Find 3 objects near you and count them aloud for {topic}.",
        "english": f"Say one word from {topic}, clap its sounds, and make a tiny sentence.",
        "science": f"Look around your room and name one example connected to {topic}.",
        "gk": f"Tell one real-life example related to {topic}.",
    }
    return tasks.get(subject, "Try one tiny example and explain it aloud.")


def build_hint(question: str, correct: str) -> str:
    return f"Look carefully at the question. The answer begins like this: {correct[:1]}"


def choose_mood(answer_text: str) -> str:
    if "Wonderful" in answer_text or "Great" in answer_text:
        return "celebrate"
    if "hint" in answer_text.lower():
        return "thinking"
    return "speaking"


def normalize(value: str) -> str:
    return value.strip().lower().replace(".", "")
