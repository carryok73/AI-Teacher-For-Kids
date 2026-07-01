const state = {
  student: null,
  subject: "math",
  currentQuiz: null,
  lastTeacherText: "",
};

const subjectNames = {
  math: "Math Adventure",
  english: "English Story Room",
  science: "Science Lab",
  gk: "World Explorer",
};

const els = {
  avatar: document.querySelector("#avatar"),
  bubble: document.querySelector("#teacherBubble"),
  studentForm: document.querySelector("#studentForm"),
  studentName: document.querySelector("#studentName"),
  studentGrade: document.querySelector("#studentGrade"),
  chatForm: document.querySelector("#chatForm"),
  chatInput: document.querySelector("#chatInput"),
  chatLog: document.querySelector("#chatLog"),
  starCount: document.querySelector("#starCount"),
  streakCount: document.querySelector("#streakCount"),
  roomTitle: document.querySelector("#roomTitle"),
  quizQuestion: document.querySelector("#quizQuestion"),
  quizHint: document.querySelector("#quizHint"),
  quizOptions: document.querySelector("#quizOptions"),
  masteryList: document.querySelector("#masteryList"),
  recommendation: document.querySelector("#recommendation"),
  activityList: document.querySelector("#activityList"),
};

document.querySelectorAll(".subject-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".subject-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.subject = button.dataset.subject;
    els.roomTitle.textContent = subjectNames[state.subject];
    setTeacher(`Great choice. Let us learn ${button.textContent.trim()} today.`);
  });
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#${button.dataset.view}View`).classList.add("active");
    if (button.dataset.view === "progress" && state.student) loadProgress();
  });
});

els.studentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = await api("/api/students", {
    name: els.studentName.value,
    grade: els.studentGrade.value,
  });
  state.student = data.student;
  updateStats();
  setTeacher(`Hi ${state.student.name}. I am your AI teacher. Pick a lesson, ask a doubt, or try a quiz.`);
  addMessage("teacher", `Welcome ${state.student.name}! I will help you learn step by step.`);
});

els.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!requireStudent()) return;
  const message = els.chatInput.value.trim();
  if (!message) return;
  els.chatInput.value = "";
  addMessage("child", message);
  setAvatar("thinking");
  const data = await api("/api/chat", {
    student_id: state.student.id,
    subject: state.subject,
    message,
    mode: "guided",
  });
  addMessage("teacher", data.answer);
  setTeacher(data.answer, data.avatar_mood);
  loadProgress();
});

document.querySelector("#lessonButton").addEventListener("click", async () => {
  if (!requireStudent()) return;
  const data = await api("/api/lesson", {
    student_id: state.student.id,
    subject: state.subject,
    topic: "Mixed Practice",
  });
  const text = `${data.explanation} Micro task: ${data.micro_task}`;
  setTeacher(text, "speaking");
  addMessage("teacher", text);
  loadProgress();
});

document.querySelector("#newQuizButton").addEventListener("click", async () => {
  if (!requireStudent()) return;
  const data = await api("/api/quiz", {
    student_id: state.student.id,
    subject: state.subject,
    topic: "Mixed Practice",
  });
  state.currentQuiz = data;
  renderQuiz(data);
});

document.querySelector("#speakButton").addEventListener("click", () => {
  speak(state.lastTeacherText || els.bubble.textContent);
});

document.querySelector("#listenButton").addEventListener("click", () => {
  if (!requireStudent()) return;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    setTeacher("Voice listening is not supported in this browser. You can type your question.");
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  setAvatar("listening");
  setTeacher("I am listening. Ask your question.");
  recognition.onresult = (event) => {
    els.chatInput.value = event.results[0][0].transcript;
    els.chatForm.requestSubmit();
  };
  recognition.onerror = () => setTeacher("I could not hear clearly. Please try again or type your question.");
  recognition.onend = () => setAvatar("speaking");
  recognition.start();
});

function renderQuiz(quiz) {
  els.quizQuestion.textContent = quiz.question;
  els.quizHint.textContent = quiz.hint;
  els.quizOptions.innerHTML = "";
  quiz.options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = option;
    button.addEventListener("click", () => submitAnswer(option, button));
    els.quizOptions.appendChild(button);
  });
}

async function submitAnswer(selected, button) {
  if (!state.currentQuiz) return;
  const data = await api("/api/answer", {
    student_id: state.student.id,
    subject: state.subject,
    topic: state.currentQuiz.topic,
    question: state.currentQuiz.question,
    selected,
    correct: state.currentQuiz.correct,
  });
  button.classList.add(data.correct ? "correct" : "wrong");
  setTeacher(data.feedback, data.correct ? "celebrate" : "thinking");
  addMessage("teacher", data.feedback);
  await loadProgress();
}

async function loadProgress() {
  if (!state.student) return;
  const data = await fetch(`/api/progress/${state.student.id}`).then((res) => res.json());
  state.student = data.student;
  updateStats();
  els.recommendation.textContent = data.recommendation;
  els.masteryList.innerHTML = "";
  const entries = Object.entries(data.mastery);
  if (!entries.length) {
    els.masteryList.textContent = "No mastery data yet. Complete one lesson or quiz.";
  } else {
    entries.forEach(([subject, score]) => {
      const row = document.createElement("div");
      row.className = "mastery-row";
      row.innerHTML = `<strong>${subject.toUpperCase()} ${score}%</strong><div class="bar"><span style="width:${score}%"></span></div>`;
      els.masteryList.appendChild(row);
    });
  }
  els.activityList.innerHTML = "";
  data.events.forEach((event) => {
    const item = document.createElement("div");
    item.textContent = `${event.event_type.toUpperCase()} - ${event.subject} - ${event.topic} - ${event.score}`;
    els.activityList.appendChild(item);
  });
}

async function api(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail);
  }
  return response.json();
}

function requireStudent() {
  if (state.student) return true;
  setTeacher("Please start a session first so I can save your progress.");
  return false;
}

function setTeacher(text, mood = "speaking") {
  state.lastTeacherText = text;
  els.bubble.textContent = text;
  setAvatar(mood);
}

function setAvatar(mood) {
  els.avatar.className = `avatar ${mood}`;
}

function addMessage(type, text) {
  const article = document.createElement("article");
  article.className = `message ${type}`;
  article.textContent = text;
  els.chatLog.appendChild(article);
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
}

function updateStats() {
  els.starCount.textContent = state.student?.stars ?? 0;
  els.streakCount.textContent = state.student?.streak ?? 0;
}

function speak(text) {
  if (!("speechSynthesis" in window)) {
    setTeacher("Speech output is not supported in this browser.");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";
  utterance.rate = 0.9;
  utterance.pitch = 1.1;
  utterance.onstart = () => setAvatar("speaking");
  utterance.onend = () => setAvatar("celebrate");
  window.speechSynthesis.speak(utterance);
}
