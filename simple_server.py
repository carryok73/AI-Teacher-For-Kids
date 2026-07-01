import json
import mimetypes
import random
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "ai_teacher.db"

SUBJECTS = {
    "math": {
        "name": "Math",
        "topics": ["Counting", "Addition", "Subtraction", "Shapes", "Patterns"],
        "starter": "Start by touching or counting real objects.",
        "sample_questions": [
            ("What is 2 + 3?", ["4", "5", "6", "7"], "5"),
            ("Which shape has 3 sides?", ["Circle", "Triangle", "Square", "Star"], "Triangle"),
            ("What comes after 8?", ["7", "8", "9", "10"], "9"),
        ],
    },
    "english": {
        "name": "English",
        "topics": ["Phonics", "Sight Words", "Rhyming", "Story Time", "Vocabulary"],
        "starter": "Read slowly and listen to sounds.",
        "sample_questions": [
            ("Which word rhymes with cat?", ["sun", "hat", "dog", "pen"], "hat"),
            ("Which is a vowel?", ["b", "t", "a", "m"], "a"),
            ("Choose the correct sentence.", ["I am happy.", "I happy am.", "Happy I am.", "Am happy I."], "I am happy."),
        ],
    },
    "science": {
        "name": "Science",
        "topics": ["Plants", "Animals", "Weather", "Human Body", "Light"],
        "starter": "Science begins with noticing.",
        "sample_questions": [
            ("What do plants need to grow?", ["Only toys", "Sunlight and water", "Shoes", "Books"], "Sunlight and water"),
            ("Which body part helps us see?", ["Eyes", "Feet", "Ears", "Hands"], "Eyes"),
            ("Rain comes from which?", ["Clouds", "Rocks", "Chairs", "Pencils"], "Clouds"),
        ],
    },
    "gk": {
        "name": "General Knowledge",
        "topics": ["My Family", "Community Helpers", "Good Habits", "Festivals", "Our Country"],
        "starter": "General knowledge helps us understand the world.",
        "sample_questions": [
            ("Who helps sick people?", ["Doctor", "Chef", "Pilot", "Painter"], "Doctor"),
            ("Which habit keeps hands clean?", ["Washing hands", "Throwing books", "Skipping sleep", "Breaking toys"], "Washing hands"),
            ("What do we use to tell time?", ["Clock", "Plate", "Ball", "Spoon"], "Clock"),
        ],
    },
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
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
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def rows(query, args=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, args).fetchall()]


def execute(query, args=()):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, args)
        return cur.lastrowid


def log_event(student_id, subject, topic, event_type, score, details):
    execute(
        "INSERT INTO learning_events (student_id, subject, topic, event_type, score, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (student_id, subject, topic, event_type, score, details, datetime.utcnow().isoformat()),
    )


def tutor_reply(name, subject, message):
    lower = message.lower()
    if any(word in lower for word in ["answer", "solve", "homework"]):
        return f"Let's learn it together, {name}. I will give a hint first. What important clue do you notice?"
    if subject == "math":
        return "Draw dots or use your fingers. Count slowly, then check once more. What number did you reach?"
    if subject == "english":
        return "Say the word aloud and listen to the first sound. Can you make one tiny sentence?"
    if subject == "science":
        return "Great question. Scientists observe, guess, and test. What can you see around you?"
    return "Smart question. Connect it to daily life and tell me one example you have seen."


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send_file(ROOT / "app" / "templates" / "index.html", "text/html")
        elif path.startswith("/static/"):
            self.send_file(ROOT / "app" / path.lstrip("/"))
        elif path == "/api/health":
            self.send_json({"status": "ok", "service": "ai-teacher-kids", "environment": "demo"})
        elif path.startswith("/api/progress/"):
            self.progress(int(path.rsplit("/", 1)[-1]))
        else:
            self.send_error(404)

    def do_POST(self):
        body = self.read_json()
        path = urlparse(self.path).path
        if path == "/api/students":
            self.create_student(body)
        elif path == "/api/lesson":
            self.lesson(body)
        elif path == "/api/chat":
            self.chat(body)
        elif path == "/api/quiz":
            self.quiz(body)
        elif path == "/api/answer":
            self.answer(body)
        else:
            self.send_error(404)

    def read_json(self):
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size).decode("utf-8") or "{}")

    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path, content_type=None):
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        guessed = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", guessed)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def create_student(self, body):
        student_id = execute(
            "INSERT INTO students (name, grade, created_at) VALUES (?, ?, ?)",
            (body.get("name", "Student"), body.get("grade", "Grade 1"), datetime.utcnow().isoformat()),
        )
        self.send_json({"student": rows("SELECT * FROM students WHERE id = ?", (student_id,))[0]})

    def lesson(self, body):
        subject = body["subject"]
        topic = random.choice(SUBJECTS[subject]["topics"])
        text = f"Today we are learning {topic} in {SUBJECTS[subject]['name']}. {SUBJECTS[subject]['starter']} Try one example and tell me what you notice."
        log_event(body["student_id"], subject, topic, "lesson", 10, text)
        self.send_json({"subject": subject, "topic": topic, "explanation": text, "micro_task": "Try one tiny example aloud."})

    def chat(self, body):
        student = rows("SELECT * FROM students WHERE id = ?", (body["student_id"],))[0]
        answer = tutor_reply(student["name"], body["subject"], body["message"])
        execute(
            "INSERT INTO conversations (student_id, subject, question, answer, created_at) VALUES (?, ?, ?, ?, ?)",
            (body["student_id"], body["subject"], body["message"], answer, datetime.utcnow().isoformat()),
        )
        log_event(body["student_id"], body["subject"], "Doubt Solving", "chat", 5, body["message"])
        self.send_json({"answer": answer, "avatar_mood": "thinking" if "hint" in answer.lower() else "speaking"})

    def quiz(self, body):
        question, options, correct = random.choice(SUBJECTS[body["subject"]]["sample_questions"])
        self.send_json({"subject": body["subject"], "topic": body.get("topic", "Mixed Practice"), "question": question, "options": options, "correct": correct, "hint": f"The answer begins with {correct[:1]}."})

    def answer(self, body):
        is_correct = body["selected"].strip().lower().replace(".", "") == body["correct"].strip().lower().replace(".", "")
        stars = 3 if is_correct else 1
        score = 100 if is_correct else 35
        execute(
            "UPDATE students SET stars = stars + ?, streak = CASE WHEN ? THEN streak + 1 ELSE 0 END WHERE id = ?",
            (stars, 1 if is_correct else 0, body["student_id"]),
        )
        log_event(body["student_id"], body["subject"], body["topic"], "quiz", score, body["question"])
        feedback = "Wonderful thinking! You earned 3 stars." if is_correct else f"Good try. The answer is {body['correct']}. Let's try one more."
        self.send_json({"correct": is_correct, "score": score, "stars": stars, "feedback": feedback})

    def progress(self, student_id):
        student = rows("SELECT * FROM students WHERE id = ?", (student_id,))
        events = rows("SELECT subject, topic, event_type, score, details, created_at FROM learning_events WHERE student_id = ? ORDER BY id DESC LIMIT 20", (student_id,))
        mastery = {}
        for subject in {event["subject"] for event in events}:
            scores = [event["score"] for event in events if event["subject"] == subject]
            mastery[subject] = round(sum(scores) / len(scores))
        recommendation = "Start with a short Math or English warm-up lesson."
        if mastery:
            weakest = min(mastery, key=mastery.get)
            recommendation = f"Revise {SUBJECTS[weakest]['name']} with visual examples and two easy quiz questions."
        self.send_json({"student": student[0], "events": events, "mastery": mastery, "recommendation": recommendation})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("AI Teacher for Kids running at http://127.0.0.1:8000")
    server.serve_forever()
