import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_cors import CORS
from dotenv import load_dotenv
import requests

from db import get_db, close_db, init_db

COURSE_NAME = "SMARTPATH"

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")
CORS(app)

# Gemini v2 config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# DB lifecycle
db_initialized = False


@app.before_request
def initialize_database_once():
    global db_initialized
    if not db_initialized:
        init_db()
        db_initialized = True


@app.teardown_appcontext
def teardown_db(exception):
    close_db()


# Helpers
def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    return c.fetchone()


def login_required(role=None):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("index"))
            if role and user["role"] != role:
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key not configured on server."
    try:
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY
        }
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }
        resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=20)
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception as e:
        print("Gemini error:", e)
        return "Error contacting AI service."


def compute_overall_progress_for_user(user_id: int):
    db = get_db()
    c = db.cursor()

    # only count smart/bank questions in analytics
    c.execute("""
        SELECT COUNT(*) AS total
        FROM quiz_attempts
        WHERE user_id = ? AND source = 'bank'
    """, (user_id,))
    total_attempts = c.fetchone()["total"]

    c.execute("""
        SELECT COUNT(*) AS correct
        FROM quiz_attempts
        WHERE user_id = ? AND is_correct = 1 AND source = 'bank'
    """, (user_id,))
    correct_attempts = c.fetchone()["correct"]

    overall_accuracy = int(correct_attempts * 100 / total_attempts) if total_attempts else 0

    c.execute("""
        SELECT q.topic,
               SUM(CASE WHEN qa.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
               COUNT(*) AS total
        FROM quiz_attempts qa
        JOIN questions q ON q.id = qa.question_id
        WHERE qa.user_id = ? AND qa.source = 'bank'
        GROUP BY q.topic
    """, (user_id,))
    rows = c.fetchall()

    topic_stats = {}
    weaknesses = []
    for r in rows:
        acc = int(r["correct"] * 100 / r["total"]) if r["total"] else 0
        topic_stats[r["topic"]] = {
            "name": r["topic"],
            "accuracy": acc,
            "correct": r["correct"],
            "total": r["total"]
        }
        if acc <= 50:
            weaknesses.append(r["topic"])

    return {
        "overall_accuracy": overall_accuracy,
        "total_attempts": total_attempts,
        "topic_stats": topic_stats,
        "weaknesses": weaknesses
    }


# Routes: Landing
@app.route("/")
def index():
    return render_template("base.html", course_name=COURSE_NAME)


# Registration
@app.route("/register/student", methods=["GET", "POST"])
def register_student():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            flash("All fields are required.", "error")
        else:
            c = db.cursor()
            try:
                c.execute("""
                    INSERT INTO users (name, email, password, role)
                    VALUES (?, ?, ?, 'student')
                """, (name, email, password))
                db.commit()
                flash("Student registered. Please login.", "success")
                return redirect(url_for("login_student"))
            except Exception:
                flash("A student with this email already exists.", "error")

    return render_template("register_student.html", course_name=COURSE_NAME)


@app.route("/register/mentor", methods=["GET", "POST"])
def register_mentor():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            flash("All fields are required.", "error")
        else:
            c = db.cursor()
            try:
                c.execute("""
                    INSERT INTO users (name, email, password, role)
                    VALUES (?, ?, ?, 'mentor')
                """, (name, email, password))
                db.commit()
                flash("Mentor registered. Please login.", "success")
                return redirect(url_for("login_mentor"))
            except Exception:
                flash("A mentor with this email already exists.", "error")

    return render_template("register_mentor.html", course_name=COURSE_NAME)


# Login / Logout
@app.route("/login/student", methods=["GET", "POST"])
def login_student():
    db = get_db()
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        c = db.cursor()
        c.execute("""
            SELECT * FROM users
            WHERE email = ? AND password = ? AND role = 'student'
        """, (email, password))
        stu = c.fetchone()
        if not stu:
            flash("Invalid student credentials or account not registered.", "error")
        else:
            session["user_id"] = stu["id"]
            session["role"] = "student"
            return redirect(url_for("student_dashboard"))
    return render_template("login_student.html", course_name=COURSE_NAME)


@app.route("/login/mentor", methods=["GET", "POST"])
def login_mentor():
    db = get_db()
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        c = db.cursor()
        c.execute("""
            SELECT * FROM users
            WHERE email = ? AND password = ? AND role = 'mentor'
        """, (email, password))
        mentor = c.fetchone()
        if not mentor:
            flash("Invalid mentor credentials or account not registered.", "error")
        else:
            session["user_id"] = mentor["id"]
            session["role"] = "mentor"
            return redirect(url_for("mentor_dashboard"))
    return render_template("login_mentor.html", course_name=COURSE_NAME)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# Dashboards
@app.route("/student/dashboard")
@login_required(role="student")
def student_dashboard():
    user = current_user()
    return render_template("student_dashboard.html", user=user, course_name=COURSE_NAME)


@app.route("/mentor/dashboard")
@login_required(role="mentor")
def mentor_dashboard():
    user = current_user()
    return render_template("mentor_dashboard.html", user=user, course_name=COURSE_NAME)


# APIs: Progress & learning path
@app.route("/api/student/progress")
@login_required(role="student")
def api_progress():
    user = current_user()
    prog = compute_overall_progress_for_user(user["id"])
    data = {
        "overall_accuracy": prog["overall_accuracy"],
        "total_attempts": prog["total_attempts"],
        "time_spent_minutes": prog["total_attempts"] * 2,
        "strengths": [t for t, info in prog["topic_stats"].items() if info["accuracy"] >= 80],
        "weaknesses": prog["weaknesses"],
        "topic_stats": prog["topic_stats"]
    }
    return jsonify(data)


@app.route("/api/student/learning-path")
@login_required(role="student")
def api_learning_path():
    user = current_user()
    db = get_db()
    c = db.cursor()

    c.execute("""
        SELECT q.topic,
               SUM(CASE WHEN qa.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
               COUNT(*) AS total
        FROM quiz_attempts qa
        JOIN questions q ON q.id = qa.question_id
        WHERE qa.user_id = ? AND qa.source = 'bank'
        GROUP BY q.topic
    """, (user["id"],))
    rows = c.fetchall()

    path = []
    for r in rows:
        acc = int(r["correct"] * 100 / r["total"]) if r["total"] else 0
        if acc >= 80:
            mastery = "strong"
            action = "Move to tougher problems and mixed-topic quizzes."
        elif acc <= 50:
            mastery = "weak"
            action = "Revisit basics and complete easy-level quizzes."
        else:
            mastery = "medium"
            action = "Do a mix of revision and moderate problems."

        path.append({
            "topic_name": r["topic"],
            "mastery": mastery,
            "action": action
        })

    if not path:
        path = [{
            "topic_name": "No data yet",
            "mastery": "unknown",
            "action": "Start by taking your first smart quiz."
        }]

    return jsonify(path)


# APIs: Quiz (smart + manual)
@app.route("/api/student/manual-quizzes")
@login_required(role="student")
def api_student_manual_quizzes():
    db = get_db()
    c = db.cursor()
    # Only quizzes that have at least one question
    c.execute("""
        SELECT mq.id, mq.title, mq.description, mq.created_at, u.name AS mentor_name,
               COUNT(mqq.id) AS qcount
        FROM mentor_quizzes mq
        JOIN users u ON u.id = mq.created_by
        JOIN mentor_quiz_questions mqq ON mqq.quiz_id = mq.id
        GROUP BY mq.id
        ORDER BY mq.created_at DESC
    """)
    rows = c.fetchall()
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "created_at": r["created_at"],
            "mentor_name": r["mentor_name"],
            "question_count": r["qcount"]
        })
    return jsonify(res)


@app.route("/api/student/quiz/generate", methods=["POST"])
@login_required(role="student")
def api_generate_quiz():
    db = get_db()
    c = db.cursor()
    data = request.get_json() or {}
    mode = data.get("mode", "smart")
    quiz_id = data.get("quiz_id")

    if mode == "manual" and quiz_id:
        c.execute("""
            SELECT id, question, option_a, option_b, option_c, option_d, correct_option
            FROM mentor_quiz_questions
            WHERE quiz_id = ?
        """, (quiz_id,))
        rows = c.fetchall()
    else:
        c.execute("""
            SELECT id, topic, difficulty, question,
                   option_a, option_b, option_c, option_d, correct_option
            FROM questions
            ORDER BY RANDOM()
            LIMIT 5
        """)
        rows = c.fetchall()

    questions = []
    for q in rows:
        questions.append({
            "id": q["id"],
            "question": q["question"],
            "option_a": q["option_a"],
            "option_b": q["option_b"],
            "option_c": q["option_c"],
            "option_d": q["option_d"],
            "correct_option": q["correct_option"]
        })
    return jsonify(questions)


@app.route("/api/student/quiz/submit", methods=["POST"])
@login_required(role="student")
def api_submit_quiz():
    user = current_user()
    db = get_db()
    data = request.get_json() or {}
    question_id = data.get("question_id")
    selected_option = data.get("selected_option")
    mode = data.get("mode", "smart")

    c = db.cursor()
    source = "manual" if mode == "manual" else "bank"

    if source == "manual":
        c.execute("SELECT * FROM mentor_quiz_questions WHERE id = ?", (question_id,))
    else:
        c.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    q = c.fetchone()
    if not q:
        return jsonify({"error": "Question not found"}), 400

    is_correct = 1 if selected_option == q["correct_option"] else 0

    c.execute("""
        INSERT INTO quiz_attempts (user_id, question_id, is_correct, source, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user["id"], question_id, is_correct, source, datetime.utcnow().isoformat()))
    db.commit()

    prompt = f"""
    Question: {q['question']}
    Student's chosen option: {selected_option}
    Correct option: {q['correct_option']}

    Explain in 2-3 simple sentences why the student's answer is correct or incorrect,
    and give one small hint + one short recommended topic title.
    """
    explanation_text = call_gemini(prompt)

    return jsonify({
        "is_correct": bool(is_correct),
        "correct_option": q["correct_option"],
        "explanation": explanation_text,
        "recommendation": "Focus on the concept mentioned in the explanation."
    })


# APIs: Assignments
@app.route("/api/student/assignments")
@login_required(role="student")
def api_student_assignments():
    user = current_user()
    db = get_db()
    c = db.cursor()

    c.execute("SELECT * FROM assignments")
    assignments = c.fetchall()
    res = []

    for a in assignments:
        c.execute("""
            SELECT * FROM assignment_submissions
            WHERE assignment_id = ? AND student_id = ?
        """, (a["id"], user["id"]))
        sub = c.fetchone()
        res.append({
            "id": a["id"],
            "title": a["title"],
            "description": a["description"],
            "due_date": a["due_date"],
            "submission": {
                "content": sub["content"] if sub else None,
                "submitted_at": sub["submitted_at"] if sub else None,
                "feedback": sub["feedback"] if sub else None,
                "rating": sub["rating"] if sub else None
            } if sub else {
                "content": None,
                "submitted_at": None,
                "feedback": None,
                "rating": None
            }
        })

    return jsonify(res)


@app.route("/api/student/assignments/submit", methods=["POST"])
@login_required(role="student")
def api_submit_assignment():
    user = current_user()
    db = get_db()
    data = request.get_json() or {}
    assignment_id = data.get("assignment_id")
    content = data.get("content", "")

    c = db.cursor()
    c.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,))
    a = c.fetchone()
    if not a:
        return jsonify({"error": "Assignment not found"}), 400

    c.execute("""
        SELECT id FROM assignment_submissions
        WHERE assignment_id = ? AND student_id = ?
    """, (assignment_id, user["id"]))
    existing = c.fetchone()

    if existing:
        c.execute("""
            UPDATE assignment_submissions
            SET content = ?, submitted_at = ?
            WHERE id = ?
        """, (content, datetime.utcnow().isoformat(), existing["id"]))
    else:
        c.execute("""
            INSERT INTO assignment_submissions (assignment_id, student_id, content, submitted_at)
            VALUES (?, ?, ?, ?)
        """, (assignment_id, user["id"], content, datetime.utcnow().isoformat()))
    db.commit()

    return jsonify({"status": "ok"})


# Mentor: assignments
@app.route("/api/mentor/assignments", methods=["GET", "POST"])
@login_required(role="mentor")
def api_mentor_assignments():
    db = get_db()
    c = db.cursor()

    if request.method == "POST":
        data = request.get_json() or {}
        title = data.get("title")
        description = data.get("description")
        due_date = data.get("due_date")
        c.execute("""
            INSERT INTO assignments (title, description, due_date)
            VALUES (?, ?, ?)
        """, (title, description, due_date))
        db.commit()
        return jsonify({"status": "created"})

    c.execute("SELECT * FROM assignments")
    assignments = c.fetchall()
    res = []
    for a in assignments:
        res.append({
            "id": a["id"],
            "title": a["title"],
            "description": a["description"],
            "due_date": a["due_date"]
        })
    return jsonify(res)


@app.route("/api/mentor/assignments/<int:assignment_id>/submissions")
@login_required(role="mentor")
def api_mentor_submissions(assignment_id):
    db = get_db()
    c = db.cursor()

    c.execute("""
        SELECT s.id AS submission_id,
               s.student_id,
               u.name AS student_name,
               s.content,
               s.submitted_at,
               s.feedback,
               s.rating
        FROM assignment_submissions s
        JOIN users u ON u.id = s.student_id
        WHERE s.assignment_id = ?
    """, (assignment_id,))
    rows = c.fetchall()

    res = []
    for r in rows:
        res.append({
            "submission_id": f"{assignment_id}_{r['student_id']}",
            "student_id": r["student_id"],
            "student_name": r["student_name"],
            "content": r["content"],
            "submitted_at": r["submitted_at"],
            "feedback": r["feedback"],
            "rating": r["rating"]
        })
    return jsonify(res)


@app.route("/api/mentor/submissions/feedback", methods=["POST"])
@login_required(role="mentor")
def api_mentor_feedback():
    db = get_db()
    data = request.get_json() or {}
    submission_id = data.get("submission_id")
    feedback = data.get("feedback")
    rating = data.get("rating")

    try:
        assignment_id_str, student_id_str = submission_id.split("_")
        assignment_id = int(assignment_id_str)
        student_id = int(student_id_str)
    except Exception:
        return jsonify({"error": "Invalid submission id"}), 400

    c = db.cursor()
    c.execute("""
        SELECT id FROM assignment_submissions
        WHERE assignment_id = ? AND student_id = ?
    """, (assignment_id, student_id))
    sub = c.fetchone()
    if not sub:
        return jsonify({"error": "Submission not found"}), 400

    c.execute("""
        UPDATE assignment_submissions
        SET feedback = ?, rating = ?
        WHERE id = ?
    """, (feedback, rating, sub["id"]))
    db.commit()

    return jsonify({"status": "updated"})


# Mentor: students overview
@app.route("/api/mentor/students")
@login_required(role="mentor")
def api_mentor_students():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, name FROM users WHERE role = 'student'")
    students = c.fetchall()
    result = []
    for s in students:
        prog = compute_overall_progress_for_user(s["id"])
        result.append({
            "id": s["id"],
            "name": s["name"],
            "overall_accuracy": prog["overall_accuracy"],
            "total_attempts": prog["total_attempts"],
            "weaknesses": prog["weaknesses"]
        })
    return jsonify(result)


# Lessons / classes
@app.route("/api/student/lessons")
@login_required(role="student")
def api_student_lessons():
    db = get_db()
    c = db.cursor()
    c.execute("""
        SELECT l.id, l.title, l.description, l.video_url, l.topic, l.created_at, u.name AS mentor_name
        FROM lessons l
        LEFT JOIN users u ON u.id = l.created_by
        ORDER BY l.created_at DESC
    """)
    rows = c.fetchall()
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "video_url": r["video_url"],
            "topic": r["topic"],
            "created_at": r["created_at"],
            "mentor_name": r["mentor_name"] or "Mentor"
        })
    return jsonify(res)


@app.route("/api/mentor/lessons", methods=["GET", "POST"])
@login_required(role="mentor")
def api_mentor_lessons():
    db = get_db()
    c = db.cursor()
    user = current_user()

    if request.method == "POST":
        data = request.get_json() or {}
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        video_url = data.get("video_url", "").strip()
        topic = data.get("topic", "").strip()

        c.execute("""
            INSERT INTO lessons (title, description, video_url, topic, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, description, video_url, topic, user["id"], datetime.utcnow().isoformat()))
        db.commit()
        return jsonify({"status": "created"})

    c.execute("""
        SELECT l.id, l.title, l.description, l.video_url, l.topic, l.created_at
        FROM lessons l
        WHERE l.created_by = ?
        ORDER BY l.created_at DESC
    """, (user["id"],))
    rows = c.fetchall()
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "video_url": r["video_url"],
            "topic": r["topic"],
            "created_at": r["created_at"]
        })
    return jsonify(res)


# Mentor: manual quizzes
@app.route("/api/mentor/quizzes", methods=["GET", "POST"])
@login_required(role="mentor")
def api_mentor_quizzes():
    db = get_db()
    c = db.cursor()
    user = current_user()

    if request.method == "POST":
        data = request.get_json() or {}
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        c.execute("""
            INSERT INTO mentor_quizzes (title, description, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (title, description, user["id"], datetime.utcnow().isoformat()))
        db.commit()
        return jsonify({"status": "created"})

    c.execute("""
        SELECT id, title, description, created_at
        FROM mentor_quizzes
        WHERE created_by = ?
        ORDER BY created_at DESC
    """, (user["id"],))
    rows = c.fetchall()
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "created_at": r["created_at"]
        })
    return jsonify(res)


@app.route("/api/mentor/quizzes/<int:quiz_id>/questions", methods=["GET", "POST"])
@login_required(role="mentor")
def api_mentor_quiz_questions(quiz_id):
    db = get_db()
    c = db.cursor()

    if request.method == "POST":
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        option_a = data.get("option_a", "").strip()
        option_b = data.get("option_b", "").strip()
        option_c = data.get("option_c", "").strip()
        option_d = data.get("option_d", "").strip()
        correct_option = data.get("correct_option", "").strip().lower()
        topic = data.get("topic", "").strip()
        difficulty = data.get("difficulty", "manual").strip()

        c.execute("""
            INSERT INTO mentor_quiz_questions (
                quiz_id, question, option_a, option_b, option_c, option_d,
                correct_option, topic, difficulty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (quiz_id, question, option_a, option_b, option_c, option_d,
              correct_option, topic, difficulty))
        db.commit()
        return jsonify({"status": "created"})

    c.execute("""
        SELECT id, question, option_a, option_b, option_c, option_d, correct_option
        FROM mentor_quiz_questions
        WHERE quiz_id = ?
    """, (quiz_id,))
    rows = c.fetchall()
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "question": r["question"],
            "option_a": r["option_a"],
            "option_b": r["option_b"],
            "option_c": r["option_c"],
            "option_d": r["option_d"],
            "correct_option": r["correct_option"],
        })
    return jsonify(res)


# Mentor messages
@app.route("/api/student/mentor/message", methods=["POST"])
@login_required(role="student")
def api_student_message_mentor():
    user = current_user()
    db = get_db()
    data = request.get_json() or {}
    question_text = data.get("question_text", "").strip()

    c = db.cursor()
    c.execute("SELECT * FROM users WHERE role = 'mentor' ORDER BY id LIMIT 1")
    mentor = c.fetchone()
    if not mentor:
        return jsonify({"error": "No mentor registered yet."}), 400

    c.execute("""
        INSERT INTO mentor_messages (student_id, mentor_id, question_text, created_at)
        VALUES (?, ?, ?, ?)
    """, (user["id"], mentor["id"], question_text, datetime.utcnow().isoformat()))
    db.commit()

    return jsonify({"status": "sent"})


@app.route("/api/mentor/messages", methods=["GET", "POST"])
@login_required(role="mentor")
def api_mentor_messages():
    db = get_db()
    c = db.cursor()

    if request.method == "POST":
        data = request.get_json() or {}
        msg_id = data.get("message_id")
        answer_text = data.get("answer_text")
        c.execute("""
            UPDATE mentor_messages
            SET answer_text = ?, answered_at = ?
            WHERE id = ?
        """, (answer_text, datetime.utcnow().isoformat(), msg_id))
        db.commit()
        return jsonify({"status": "answered"})

    c.execute("""
        SELECT m.id,
               u.name AS student_name,
               m.question_text,
               m.answer_text,
               m.created_at,
               m.answered_at
        FROM mentor_messages m
        JOIN users u ON u.id = m.student_id
        ORDER BY m.created_at DESC
    """)
    rows = c.fetchall()

    res = []
    for m in rows:
        res.append({
            "id": m["id"],
            "student_name": m["student_name"],
            "question_text": m["question_text"],
            "answer_text": m["answer_text"],
            "created_at": m["created_at"],
            "answered_at": m["answered_at"],
        })
    return jsonify(res)


# AI Mentor
@app.route("/api/student/ai-mentor", methods=["POST"])
@login_required(role="student")
def api_student_ai_mentor():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"reply": "Type a question so I can actually help you."})

    prompt = f"""
    You are a clear, concise AI mentor for a college-level CS student
    studying an Introduction to Python course.
    Explain in 3–5 short sentences, straight to the point. Avoid fluff.

    Student's doubt: {user_message}
    """
    reply = call_gemini(prompt)
    return jsonify({"reply": reply})


# Misc
@app.route("/health")
def health():
    return {"status": "ok", "course": COURSE_NAME}


if __name__ == "__main__":
    app.run(debug=True)
