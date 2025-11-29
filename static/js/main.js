document.addEventListener("DOMContentLoaded", () => {
    if (window.STUDENT_CONTEXT) {
        initStudentDashboard();
    }
    if (window.MENTOR_CONTEXT) {
        initMentorDashboard();
    }
});

/* ======= TAB HANDLING ======= */
function setupTabs() {
    const tabs = document.querySelectorAll(".tab");
    const contents = document.querySelectorAll(".tab-content");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-tab");
            tabs.forEach(t => t.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            const content = document.getElementById("tab-" + target);
            if (content) content.classList.add("active");
        });
    });
}

/* ======= STUDENT DASHBOARD ======= */
let STUDENT_PROGRESS_CACHE = null;

function initStudentDashboard() {
    setupTabs();
    setupSettings();
    setupMentorPanels();
    loadLearningPath();
    loadProgress().then(() => {
        generateLessonsFromProgress();
        loadServerLessons();
    });
    loadAssignments();
    setupQuiz();
}

/* --- Settings --- */
function setupSettings() {
    const toggleThemeBtn = document.getElementById("toggle-theme");
    const settingsBtn = document.getElementById("settings-btn");
    const saveGoalBtn = document.getElementById("save-goal-btn");

    if (toggleThemeBtn) {
        toggleThemeBtn.addEventListener("click", () => {
            document.body.classList.toggle("light-mode");
        });
    }

    if (settingsBtn) {
        settingsBtn.addEventListener("click", () => {
            const settingsTabBtn = document.querySelector('.tab[data-tab="settings"]');
            if (settingsTabBtn) settingsTabBtn.click();
        });
    }

    if (saveGoalBtn) {
        saveGoalBtn.addEventListener("click", () => {
            const goalInput = document.getElementById("daily-goal");
            const status = document.getElementById("goal-status");
            if (goalInput && status) {
                const val = goalInput.value || "0";
                status.textContent = `Saved daily goal: ${val} minutes.`;
            }
        });
    }
}

/* --- Progress --- */
async function loadProgress() {
    const url = STUDENT_CONTEXT.progressUrl;
    try {
        const res = await fetch(url);
        const data = await res.json();
        STUDENT_PROGRESS_CACHE = data;
        renderProgress(data);
        return data;
    } catch (e) {
        console.error("Progress error", e);
    }
}

function renderProgress(data) {
    const summaryEl = document.getElementById("progress-summary");
    const topicEl = document.getElementById("topic-stats");
    if (!summaryEl || !topicEl) return;

    summaryEl.innerHTML = "";
    topicEl.innerHTML = "";

    const tiles = [
        { label: "Overall Accuracy", value: data.overall_accuracy + "%"},
        { label: "Total Attempts", value: data.total_attempts },
        { label: "Time Spent", value: data.time_spent_minutes + " mins" },
        { label: "Strong Topics", value: (data.strengths || []).join(", ") || "None yet" },
        { label: "Weak Topics", value: (data.weaknesses || []).join(", ") || "None yet" }
    ];
    tiles.forEach(t => {
        const div = document.createElement("div");
        div.className = "progress-tile";
        div.innerHTML = `<div class="small muted">${t.label}</div><div><strong>${t.value}</strong></div>`;
        summaryEl.appendChild(div);
    });

    const stats = data.topic_stats || {};
    Object.keys(stats).forEach(key => {
        const info = stats[key];
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            <h4>${info.name}</h4>
            <p class="small muted">Accuracy: ${info.accuracy}% (${info.correct}/${info.total})</p>
        `;
        topicEl.appendChild(card);
    });
}

/* --- Learning Path --- */
async function loadLearningPath() {
    const url = STUDENT_CONTEXT.learningPathUrl;
    try {
        const res = await fetch(url);
        const data = await res.json();
        const container = document.getElementById("learning-path-container");
        if (!container) return;
        container.innerHTML = "";
        data.forEach(item => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <h4>${item.topic_name}</h4>
                <p class="small">Mastery: <strong>${item.mastery}</strong></p>
                <p class="muted small">${item.action}</p>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Learning path error", e);
    }
}

/* --- Lessons: AI + Mentor --- */
function generateLessonsFromProgress() {
    const container = document.getElementById("lessons-container");
    if (!container) return;
    container.innerHTML = "";
    const data = STUDENT_PROGRESS_CACHE;
    if (!data) return;

    const { strengths = [], weaknesses = [] } = data;

    if (weaknesses.length > 0) {
        const weakCard = document.createElement("div");
        weakCard.className = "card";
        weakCard.innerHTML = `
            <h4>Focus Zone</h4>
            <p class="small muted">These topics need revision:</p>
            <p>${weaknesses.join(", ")}</p>
            <p class="small muted">Recommended: Revisit basics and do smart quizzes focusing on these topics.</p>
        `;
        container.appendChild(weakCard);
    }

    if (strengths.length > 0) {
        const strongCard = document.createElement("div");
        strongCard.className = "card";
        strongCard.innerHTML = `
            <h4>Strength Boost</h4>
            <p class="small muted">You are good at:</p>
            <p>${strengths.join(", ")}</p>
            <p class="small muted">Recommended: Try mixed-topic smart quizzes and mentor-created manual quizzes.</p>
        `;
        container.appendChild(strongCard);
    }
}

async function loadServerLessons() {
    const url = STUDENT_CONTEXT.lessonsUrl;
    try {
        const res = await fetch(url);
        const data = await res.json();
        const container = document.getElementById("lessons-container");
        if (!container) return;

        data.forEach(l => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <h4>${l.title}</h4>
                <p class="small muted">${l.topic || ""}</p>
                <p class="small">${l.description || ""}</p>
                ${l.video_url ? `<a href="${l.video_url}" target="_blank" class="btn btn-outline small" style="margin-top:6px;">Open Video</a>` : ""}
                <p class="small muted" style="margin-top:4px;">By ${l.mentor_name}</p>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Lessons error", e);
    }
}

/* --- Assignments --- */
async function loadAssignments() {
    const url = STUDENT_CONTEXT.assignmentsUrl;
    try {
        const res = await fetch(url);
        const data = await res.json();
        const container = document.getElementById("assignments-container");
        if (!container) return;
        container.innerHTML = "";
        data.forEach(a => {
            const card = document.createElement("div");
            card.className = "card";
            const sub = a.submission || {};
            card.innerHTML = `
                <h4>${a.title}</h4>
                <p class="small">${a.description}</p>
                <p class="small muted">Due: ${a.due_date || "N/A"}</p>
                <textarea data-assignment-id="${a.id}" class="assignment-text" placeholder="Write your answer here...">${sub.content || ""}</textarea>
                <button class="btn btn-primary small submit-assignment-btn" data-assignment-id="${a.id}">Submit</button>
                ${sub.submitted_at ? `<p class="small muted">Submitted at: ${sub.submitted_at}</p>` : ""}
                ${sub.feedback ? `<p class="small">Feedback: ${sub.feedback}</p>` : ""}
                ${sub.rating ? `<p class="small">Rating: ${sub.rating}/10</p>` : ""}
            `;
            container.appendChild(card);
        });

        container.addEventListener("click", async (e) => {
            if (e.target.classList.contains("submit-assignment-btn")) {
                const id = parseInt(e.target.getAttribute("data-assignment-id"), 10);
                const textarea = container.querySelector(`textarea[data-assignment-id="${id}"]`);
                const content = textarea ? textarea.value : "";
                await submitAssignment(id, content);
                await loadAssignments();
            }
        });
    } catch (e) {
        console.error("Assignments error", e);
    }
}

async function submitAssignment(assignmentId, content) {
    const url = STUDENT_CONTEXT.assignmentSubmitUrl;
    await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ assignment_id: assignmentId, content })
    });
}

/* --- Quiz (smart + manual) --- */
function setupQuiz() {
    const modeSelect = document.getElementById("quiz-mode");
    const manualSelector = document.getElementById("manual-quiz-selector");
    const generateBtn = document.getElementById("generate-quiz-btn");

    if (!modeSelect || !generateBtn) return;

    modeSelect.addEventListener("change", () => {
        const mode = modeSelect.value;
        if (mode === "manual") {
            manualSelector.classList.remove("hidden");
            loadManualQuizzes();
        } else {
            manualSelector.classList.add("hidden");
        }
    });

    generateBtn.addEventListener("click", () => {
        const mode = modeSelect.value;
        let payload = { mode };
        if (mode === "manual") {
            const select = document.getElementById("manual-quiz-list");
            if (!select || !select.value) {
                alert("Select a manual quiz first.");
                return;
            }
            payload.quiz_id = parseInt(select.value, 10);
        }
        generateQuiz(payload);
    });
}

async function loadManualQuizzes() {
    const url = STUDENT_CONTEXT.manualQuizzesUrl;
    const select = document.getElementById("manual-quiz-list");
    if (!select) return;

    try {
        const res = await fetch(url);
        const data = await res.json();
        select.innerHTML = "";
        if (!data.length) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "No quizzes created by mentor yet";
            select.appendChild(opt);
            return;
        }
        data.forEach(q => {
            const opt = document.createElement("option");
            opt.value = q.id;
            opt.textContent = `${q.title} (${q.question_count} questions)`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error("Manual quizzes error", e);
    }
}

async function generateQuiz(payload) {
    const url = STUDENT_CONTEXT.quizGenerateUrl;
    const container = document.getElementById("quiz-container");
    if (!container) return;
    container.innerHTML = "<p class='muted small'>Loading quiz...</p>";

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload || {})
        });
        const questions = await res.json();
        container.innerHTML = "";

        if (!questions.length) {
            container.innerHTML = "<p class='muted small'>No questions available.</p>";
            return;
        }

        questions.forEach(q => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <p>${q.question}</p>
                <div class="small" style="margin-top:6px;">
                    <button class="btn btn-outline small quiz-opt" data-qid="${q.id}" data-opt="a">${q.option_a}</button>
                    <button class="btn btn-outline small quiz-opt" data-qid="${q.id}" data-opt="b">${q.option_b}</button>
                    <button class="btn btn-outline small quiz-opt" data-qid="${q.id}" data-opt="c">${q.option_c}</button>
                    <button class="btn btn-outline small quiz-opt" data-qid="${q.id}" data-opt="d">${q.option_d}</button>
                </div>
                <div class="small muted quiz-feedback" id="feedback-${q.id}" style="margin-top:6px;"></div>
            `;
            container.appendChild(card);
        });

        // Remove any existing listeners before adding new one
        const newContainer = container.cloneNode(true);
        container.replaceWith(newContainer);
        
        // Add event listener without 'once' so it persists for all questions
        const updatedContainer = document.getElementById("quiz-container");
        updatedContainer.addEventListener("click", async (e) => {
            if (e.target.classList.contains("quiz-opt")) {
                const qid = parseInt(e.target.getAttribute("data-qid"), 10);
                const opt = e.target.getAttribute("data-opt");
                const modeSelect = document.getElementById("quiz-mode");
                const mode = modeSelect ? modeSelect.value : "smart";
                await submitQuizAnswer(qid, opt, mode);
                // Disable the clicked button to prevent re-submission
                e.target.disabled = true;
                e.target.style.opacity = "0.5";
            }
        });
    } catch (e) {
        console.error("Generate quiz error", e);
    }
}

async function submitQuizAnswer(questionId, selectedOpt, mode) {
    const url = STUDENT_CONTEXT.quizSubmitUrl;
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                question_id: questionId,
                selected_option: selectedOpt,
                mode
            })
        });
        const data = await res.json();
        const fb = document.getElementById(`feedback-${questionId}`);
        if (fb) {
            const correct = data.correct_option;
            if (data.is_correct) {
                fb.innerHTML = `<span style="color:#22c55e;">Correct ✅</span><br>${data.explanation}`;
            } else {
                fb.innerHTML = `<span style="color:#ef4444;">Wrong ❌</span> (Correct: ${correct.toUpperCase()})<br>${data.explanation}`;
            }
        }
        // Refresh progress/learning path lightly
        loadProgress().then(() => {
            loadLearningPath();
            generateLessonsFromProgress();
        });
    } catch (e) {
        console.error("Submit quiz error", e);
    }
}

/* --- Mentor & AI mentor panels --- */
function setupMentorPanels() {
    const mentorBtn = document.getElementById("mentor-btn");
    const modal = document.getElementById("mentor-modal");
    const modalClose = document.getElementById("mentor-modal-close");
    const aiBtn = document.getElementById("ai-mentor-btn");
    const realBtn = document.getElementById("real-mentor-btn");

    const aiPanel = document.getElementById("ai-mentor-panel");
    const aiClose = document.getElementById("ai-mentor-close");
    const aiSend = document.getElementById("ai-mentor-send");
    const aiInput = document.getElementById("ai-mentor-input");
    const aiMessages = document.getElementById("ai-mentor-messages");

    const realPanel = document.getElementById("real-mentor-panel");
    const realClose = document.getElementById("real-mentor-close");
    const realSend = document.getElementById("real-mentor-send");
    const realInput = document.getElementById("real-mentor-input");

    if (mentorBtn) {
        mentorBtn.addEventListener("click", () => {
            modal.classList.remove("hidden");
        });
    }
    if (modalClose) {
        modalClose.addEventListener("click", () => modal.classList.add("hidden"));
    }

    if (aiBtn) {
        aiBtn.addEventListener("click", () => {
            modal.classList.add("hidden");
            aiPanel.classList.remove("hidden");
        });
    }
    if (realBtn) {
        realBtn.addEventListener("click", () => {
            modal.classList.add("hidden");
            realPanel.classList.remove("hidden");
        });
    }

    if (aiClose) {
        aiClose.addEventListener("click", () => aiPanel.classList.add("hidden"));
    }
    if (realClose) {
        realClose.addEventListener("click", () => realPanel.classList.add("hidden"));
    }

    if (aiSend) {
        aiSend.addEventListener("click", async () => {
            const msg = aiInput.value.trim();
            if (!msg) return;
            appendAiMessage(aiMessages, "You", msg);
            aiInput.value = "";
            const reply = await callAiMentor(msg);
            appendAiMessage(aiMessages, "AI Mentor", reply);
        });
    }

    if (realSend) {
        realSend.addEventListener("click", async () => {
            const msg = realInput.value.trim();
            if (!msg) return;
            await sendRealMentorMessage(msg);
            realInput.value = "";
            const panelBody = document.getElementById("real-mentor-messages");
            if (panelBody) {
                const p = document.createElement("p");
                p.className = "small";
                p.textContent = "Message sent to mentor: " + msg;
                panelBody.appendChild(p);
            }
        });
    }
}

function appendAiMessage(container, author, text) {
    if (!container) return;
    const div = document.createElement("div");
    div.className = "small";
    div.innerHTML = `<strong>${author}:</strong> ${text}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function callAiMentor(message) {
    const url = STUDENT_CONTEXT.aiMentorUrl;
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ message })
        });
        const data = await res.json();
        return data.reply || "I couldn't generate a reply.";
    } catch (e) {
        console.error("AI mentor error", e);
        return "Error talking to AI mentor.";
    }
}

async function sendRealMentorMessage(question_text) {
    const url = STUDENT_CONTEXT.mentorMessageUrl;
    try {
        await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ question_text })
        });
    } catch (e) {
        console.error("Real mentor message error", e);
    }
}

/* ======= MENTOR DASHBOARD ======= */
let MENTOR_SELECTED_ASSIGNMENT_ID = null;
let MENTOR_SELECTED_QUIZ_ID = null;

function initMentorDashboard() {
    loadMentorStudents();
    loadMentorLessons();
    loadMentorAssignments();
    loadMentorMessages();
    loadMentorQuizzes();
}

/* --- Mentor: students performance --- */
async function loadMentorStudents() {
    const url = MENTOR_CONTEXT.studentsUrl;
    const container = document.getElementById("mentor-students-performance");
    if (!container) return;
    try {
        const res = await fetch(url);
        const data = await res.json();
        container.innerHTML = "";
        data.forEach(s => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <h4>${s.name}</h4>
                <p class="small">Accuracy: ${s.overall_accuracy}%</p>
                <p class="small muted">Attempts: ${s.total_attempts}</p>
                <p class="small muted">Weak: ${(s.weaknesses || []).join(", ") || "None"}</p>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Mentor students error", e);
    }
}

/* --- Mentor: lessons --- */
async function loadMentorLessons() {
    const url = MENTOR_CONTEXT.lessonsUrl;
    const container = document.getElementById("mentor-lessons-list");
    const btn = document.getElementById("create-lesson-btn");

    if (!container) return;

    try {
        const res = await fetch(url);
        const data = await res.json();
        container.innerHTML = "";
        data.forEach(l => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <h4>${l.title}</h4>
                <p class="small muted">${l.topic || ""}</p>
                <p class="small">${l.description || ""}</p>
                ${l.video_url ? `<a href="${l.video_url}" target="_blank" class="btn btn-outline small" style="margin-top:6px;">Open Video</a>` : ""}
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Mentor lessons error", e);
    }

    if (btn) {
        btn.addEventListener("click", async () => {
            const title = document.getElementById("lesson-title").value.trim();
            const topic = document.getElementById("lesson-topic").value.trim();
            const urlInput = document.getElementById("lesson-url").value.trim();
            const desc = document.getElementById("lesson-desc").value.trim();
            if (!title) {
                alert("Title is required");
                return;
            }
            await fetch(MENTOR_CONTEXT.lessonsUrl, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    title,
                    topic,
                    video_url: urlInput,
                    description: desc
                })
            });
            document.getElementById("lesson-title").value = "";
            document.getElementById("lesson-topic").value = "";
            document.getElementById("lesson-url").value = "";
            document.getElementById("lesson-desc").value = "";
            loadMentorLessons();
        }, { once: true });
    }
}

/* --- Mentor: assignments --- */
async function loadMentorAssignments() {
    const url = MENTOR_CONTEXT.assignmentsUrl;
    const container = document.getElementById("mentor-assignments-list");
    const btn = document.getElementById("create-assignment-btn");
    if (!container) return;

    try {
        const res = await fetch(url);
        const data = await res.json();
        container.innerHTML = "";
        data.forEach(a => {
            const card = document.createElement("div");
            card.className = "card";
            card.dataset.assignmentId = a.id;
            card.innerHTML = `
                <h4>${a.title}</h4>
                <p class="small">${a.description}</p>
                <p class="small muted">Due: ${a.due_date || "N/A"}</p>
                <button class="btn btn-outline small view-submissions-btn" data-assignment-id="${a.id}">View Submissions</button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Mentor assignments error", e);
    }

    if (btn) {
        btn.addEventListener("click", async () => {
            const title = document.getElementById("new-assignment-title").value.trim();
            const desc = document.getElementById("new-assignment-desc").value.trim();
            const due = document.getElementById("new-assignment-due").value.trim();
            if (!title) {
                alert("Title is required");
                return;
            }
            await fetch(MENTOR_CONTEXT.assignmentsUrl, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ title, description: desc, due_date: due })
            });
            document.getElementById("new-assignment-title").value = "";
            document.getElementById("new-assignment-desc").value = "";
            document.getElementById("new-assignment-due").value = "";
            loadMentorAssignments();
        }, { once: true });
    }

    container.addEventListener("click", async (e) => {
        if (e.target.classList.contains("view-submissions-btn")) {
            const id = parseInt(e.target.getAttribute("data-assignment-id"), 10);
            MENTOR_SELECTED_ASSIGNMENT_ID = id;
            await loadMentorSubmissions(id);
        }
    });
}

async function loadMentorSubmissions(assignmentId) {
    const pattern = MENTOR_CONTEXT.submissionsPatternUrl;
    const url = pattern.replace("/0", "/" + assignmentId);
    const container = document.getElementById("mentor-submissions-list");
    if (!container) return;
    try {
        const res = await fetch(url);
        const data = await res.json();
        container.innerHTML = "";
        data.forEach(s => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <h4>${s.student_name}</h4>
                <p class="small">${s.content}</p>
                <p class="small muted">Submitted at: ${s.submitted_at}</p>
                <textarea class="feedback-text" data-submission-id="${s.submission_id}" placeholder="Feedback...">${s.feedback || ""}</textarea>
                <input type="number" min="0" max="10" class="rating-input" data-submission-id="${s.submission_id}" value="${s.rating || ""}" placeholder="Rating /10">
                <button class="btn btn-primary small save-feedback-btn" data-submission-id="${s.submission_id}">Save Feedback</button>
            `;
            container.appendChild(card);
        });

        container.addEventListener("click", async (e) => {
            if (e.target.classList.contains("save-feedback-btn")) {
                const sid = e.target.getAttribute("data-submission-id");
                const fbInput = container.querySelector(`textarea.feedback-text[data-submission-id="${sid}"]`);
                const ratingInput = container.querySelector(`input.rating-input[data-submission-id="${sid}"]`);
                const feedback = fbInput ? fbInput.value : "";
                const rating = ratingInput ? parseInt(ratingInput.value || "0", 10) : null;
                await saveMentorFeedback(sid, feedback, rating);
                await loadMentorSubmissions(assignmentId);
            }
        }, { once: true });
    } catch (e) {
        console.error("Submissions error", e);
    }
}

async function saveMentorFeedback(submissionId, feedback, rating) {
    const url = MENTOR_CONTEXT.feedbackUrl;
    await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ submission_id: submissionId, feedback, rating })
    });
}

/* --- Mentor: messages --- */
async function loadMentorMessages() {
    const url = MENTOR_CONTEXT.messagesUrl;
    const container = document.getElementById("mentor-messages");
    if (!container) return;
    try {
        const res = await fetch(url);
        const data = await res.json();
        container.innerHTML = "";
        data.forEach(m => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <h4>${m.student_name}</h4>
                <p class="small">${m.question_text}</p>
                <p class="small muted">Asked at: ${m.created_at}</p>
                <textarea class="answer-text" data-msg-id="${m.id}" placeholder="Type answer...">${m.answer_text || ""}</textarea>
                <button class="btn btn-primary small answer-msg-btn" data-msg-id="${m.id}">Send Answer</button>
                ${m.answered_at ? `<p class="small muted">Answered at: ${m.answered_at}</p>` : ""}
            `;
            container.appendChild(card);
        });

        container.addEventListener("click", async (e) => {
            if (e.target.classList.contains("answer-msg-btn")) {
                const id = e.target.getAttribute("data-msg-id");
                const textarea = container.querySelector(`textarea.answer-text[data-msg-id="${id}"]`);
                const answer = textarea ? textarea.value : "";
                await answerMentorMessage(id, answer);
                await loadMentorMessages();
            }
        });
    } catch (e) {
        console.error("Mentor messages error", e);
    }
}

async function answerMentorMessage(message_id, answer_text) {
    const url = MENTOR_CONTEXT.messagesUrl;
    await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message_id, answer_text })
    });
}

/* --- Mentor: manual quizzes --- */
async function loadMentorQuizzes() {
    const url = MENTOR_CONTEXT.quizzesUrl;
    const container = document.getElementById("mentor-quizzes-list");
    const createBtn = document.getElementById("create-quiz-btn");
    if (!container) return;

    try {
        const res = await fetch(url);
        const data = await res.json();
        container.innerHTML = "";
        data.forEach(q => {
            const card = document.createElement("div");
            card.className = "card";
            card.dataset.quizId = q.id;
            card.innerHTML = `
                <h4>${q.title}</h4>
                <p class="small">${q.description || ""}</p>
                <p class="small muted">Created at: ${q.created_at}</p>
                <button class="btn btn-outline small select-quiz-btn" data-quiz-id="${q.id}">Select</button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Mentor quizzes error", e);
    }

    if (createBtn) {
        createBtn.addEventListener("click", async () => {
            const title = document.getElementById("quiz-title").value.trim();
            const desc = document.getElementById("quiz-desc").value.trim();
            if (!title) {
                alert("Quiz title is required");
                return;
            }
            await fetch(MENTOR_CONTEXT.quizzesUrl, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ title, description: desc })
            });
            document.getElementById("quiz-title").value = "";
            document.getElementById("quiz-desc").value = "";
            await loadMentorQuizzes();
        }, { once: true });
    }

    container.addEventListener("click", async (e) => {
        if (e.target.classList.contains("select-quiz-btn")) {
            const id = parseInt(e.target.getAttribute("data-quiz-id"), 10);
            MENTOR_SELECTED_QUIZ_ID = id;
            const label = document.getElementById("selected-quiz-label");
            if (label) label.textContent = "Selected quiz ID: " + id;
            await loadMentorQuizQuestions(id);
        }
    }, { once: true });

    const addQuestionBtn = document.getElementById("add-quiz-question-btn");
    if (addQuestionBtn) {
        addQuestionBtn.addEventListener("click", async () => {
            if (!MENTOR_SELECTED_QUIZ_ID) {
                alert("Select a quiz first");
                return;
            }
            const qText = document.getElementById("quiz-question-text").value.trim();
            const a = document.getElementById("quiz-opt-a").value.trim();
            const b = document.getElementById("quiz-opt-b").value.trim();
            const c = document.getElementById("quiz-opt-c").value.trim();
            const d = document.getElementById("quiz-opt-d").value.trim();
            const correct = document.getElementById("quiz-correct").value.trim().toLowerCase();
            const topic = document.getElementById("quiz-topic").value.trim();

            if (!qText || !["a","b","c","d"].includes(correct)) {
                alert("Question and correct option (a/b/c/d) required");
                return;
            }

            const pattern = MENTOR_CONTEXT.quizQuestionsPatternUrl;
            const url = pattern.replace("/0", "/" + MENTOR_SELECTED_QUIZ_ID);

            await fetch(url, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    question: qText,
                    option_a: a,
                    option_b: b,
                    option_c: c,
                    option_d: d,
                    correct_option: correct,
                    topic
                })
            });

            document.getElementById("quiz-question-text").value = "";
            document.getElementById("quiz-opt-a").value = "";
            document.getElementById("quiz-opt-b").value = "";
            document.getElementById("quiz-opt-c").value = "";
            document.getElementById("quiz-opt-d").value = "";
            document.getElementById("quiz-correct").value = "";
            document.getElementById("quiz-topic").value = "";
            await loadMentorQuizQuestions(MENTOR_SELECTED_QUIZ_ID);
        }, { once: true });
    }
}

async function loadMentorQuizQuestions(quizId) {
    const pattern = MENTOR_CONTEXT.quizQuestionsPatternUrl;
    const url = pattern.replace("/0", "/" + quizId);
    const container = document.getElementById("mentor-quiz-questions-list");
    if (!container) return;
    try {
        const res = await fetch(url);
        const data = await res.json();
        container.innerHTML = "";
        data.forEach(q => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <p class="small">${q.question}</p>
                <p class="small muted">A: ${q.option_a}</p>
                <p class="small muted">B: ${q.option_b}</p>
                <p class="small muted">C: ${q.option_c}</p>
                <p class="small muted">D: ${q.option_d}</p>
                <p class="small">Correct: ${q.correct_option.toUpperCase()}</p>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Mentor quiz questions error", e);
    }
}
