import re
import random
import streamlit as st

from database import (
    create_tables,
    get_connection,
    save_speaking_session,
    save_interview_session,
    get_user_progress,
    get_activity_counts,
    get_recent_activities,
    get_streak,
)

from auth import register_user, login_user
from ai_service import get_ai_response, analyze_voice


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SpeakMate AI",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# DATABASE
# ============================================================

create_tables()


def create_extra_tables():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS grammar_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sentence TEXT,
            score REAL,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


create_extra_tables()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_SCORES = {
    "Speaking": 0,
    "Grammar": 0,
    "Interview": 0,
}


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "skill_scores" not in st.session_state:
    st.session_state.skill_scores = DEFAULT_SCORES.copy()

if "vocabulary_result" not in st.session_state:
    st.session_state.vocabulary_result = None

if "vocabulary_level" not in st.session_state:
    st.session_state.vocabulary_level = "Intermediate"

if "interview_questions_used" not in st.session_state:
    st.session_state.interview_questions_used = {}

if "current_interview_question" not in st.session_state:
    st.session_state.current_interview_question = None

if "current_interview_type" not in st.session_state:
    st.session_state.current_interview_type = None


# ============================================================
# HELPERS
# ============================================================

def extract_score(text):
    patterns = [
        r"Score\s*:\s*(\d{1,3})\s*/\s*100",
        r"Score\s*:\s*(\d{1,3})\s*%",
        r"Score\s*[-:]\s*(\d{1,3})",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return max(
                0,
                min(
                    100,
                    int(match.group(1))
                )
            )

    return None


def ask_ai(prompt):
    return get_ai_response(
        prompt,
        []
    )


def go_to(page):
    st.session_state.page = page
    st.rerun()


def update_score(skill, result):
    score = extract_score(result)

    if score is not None:
        st.session_state.skill_scores[skill] = score

    return score


# ============================================================
# GRAMMAR DATABASE
# ============================================================

def save_grammar_session(
    user_id,
    sentence,
    score,
    feedback
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO grammar_sessions
        (
            user_id,
            sentence,
            score,
            feedback
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            sentence,
            score,
            feedback,
        )
    )

    connection.commit()
    connection.close()


def get_grammar_score(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT score
        FROM grammar_sessions
        WHERE user_id = ?
        AND score IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    connection.close()

    if row:
        return float(row[0])

    return 0


# ============================================================
# LOAD USER PROGRESS
# ============================================================

def load_user_progress(user_id):

    progress = get_user_progress(user_id)

    grammar_score = get_grammar_score(user_id)

    st.session_state.skill_scores = {
        "Speaking": progress.get(
            "Speaking",
            0
        ),
        "Grammar": grammar_score,
        "Interview": progress.get(
            "Interview",
            0
        ),
    }


# ============================================================
# INTERVIEW QUESTIONS
# ============================================================

INTERVIEW_QUESTIONS = {

    "HR Interview": [

        "Tell me about yourself.",

        "What are your greatest strengths?",

        "What is one weakness you are working on?",

        "Why should we hire you?",

        "Where do you see yourself in five years?",

        "Why do you want to join our company?",

        "How do you handle pressure?",

        "Tell me about a time you worked in a team.",

        "What motivates you?",

        "Why did you choose your field of study?",
    ],

    "Technical Interview": [

        "Explain the difference between a list and a tuple in Python.",

        "What is object-oriented programming?",

        "What is the difference between a compiler and an interpreter?",

        "What is a database and why is it used?",

        "Explain primary key and foreign key.",

        "What is an API?",

        "What is the difference between frontend and backend?",

        "Explain the concept of inheritance in programming.",

        "What is the difference between SQL and NoSQL databases?",

        "What is version control and why is Git useful?",
    ],

    "Python Interview": [

        "What are the main features of Python?",

        "What is the difference between a list and a tuple?",

        "What are Python dictionaries?",

        "What is a Python function?",

        "What is the difference between == and is?",

        "What are *args and **kwargs?",

        "What is exception handling in Python?",

        "What is list comprehension?",

        "What is the difference between shallow copy and deep copy?",

        "What are modules and packages in Python?",
    ],

    "Communication Round": [

        "Tell me about yourself.",

        "Describe your biggest achievement.",

        "How do you handle disagreements with others?",

        "Describe a situation where you showed leadership.",

        "How do you manage your time?",

        "Tell me about a challenge you faced and how you handled it.",

        "How would your friends describe you?",

        "What does good communication mean to you?",

        "How do you handle constructive criticism?",

        "What are your career goals?",
    ],
}


def get_new_interview_question(interview_type):

    questions = INTERVIEW_QUESTIONS.get(
        interview_type,
        INTERVIEW_QUESTIONS["HR Interview"]
    )

    used = st.session_state.interview_questions_used.get(
        interview_type,
        []
    )

    available = [
        question
        for question in questions
        if question not in used
    ]

    if not available:

        used = []

        available = questions.copy()

    question = random.choice(
        available
    )

    used.append(
        question
    )

    st.session_state.interview_questions_used[
        interview_type
    ] = used

    return question


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 48px;
        font-weight: 800;
        text-align: center;
    }

    .subtitle {
        text-align: center;
        font-size: 21px;
        margin-bottom: 25px;
    }

    div.stButton > button[kind="primary"] {
        background-color: #6C63FF;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #574FE0;
        color: white;
    }

    section[data-testid="stSidebar"] {
        padding-top: 1rem;
    }

    .active-page {
        background-color: #6C63FF;
        color: white;
        padding: 10px;
        border-radius: 8px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .user-email {
        font-size: 13px;
        color: #777;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PUBLIC AREA
# ============================================================

if not st.session_state.logged_in:

    st.markdown(
        '<div class="main-title">🎤 SpeakMate AI</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="subtitle">'
        'Improve English. Speak with Confidence. 🚀'
        '</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "An AI-powered English speaking, grammar, "
        "vocabulary and interview practice assistant."
    )

    st.divider()

    option = st.radio(
        "Navigation",
        [
            "🏠 Home",
            "🔐 Login",
            "📝 Register",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )


    # ========================================================
    # HOME
    # ========================================================

    if option == "🏠 Home":

        st.header(
            "👋 Welcome to SpeakMate AI"
        )

        st.write(
            "Build your English communication skills "
            "through AI-powered practice."
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.info(
                """
                ### 🎤 Speaking Practice

                Record your voice or type your answer
                and receive AI feedback.
                """
            )

        with c2:

            st.info(
                """
                ### 🤖 AI Conversation

                Have a natural conversation
                with your AI English tutor.
                """
            )

        with c3:

            st.info(
                """
                ### 💼 AI Interview

                Practice interview questions
                and improve your answers.
                """
            )

        c1, c2 = st.columns(2)

        with c1:

            st.success(
                """
                ### ✍️ Grammar Correction

                Find grammar mistakes and learn
                how to correct them.
                """
            )

        with c2:

            st.success(
                """
                ### 📚 Vocabulary Builder

                Generate level-based vocabulary
                with short meanings and examples.
                """
            )


    # ========================================================
    # REGISTER
    # ========================================================

    elif option == "📝 Register":

        st.header(
            "📝 Create Your SpeakMate Account"
        )

        st.write(
            "Create an account and start improving your English."
        )

        c1, c2 = st.columns(2)

        with c1:

            name = st.text_input(
                "Full Name",
                placeholder="Enter your full name"
            )

            email = st.text_input(
                "Email",
                placeholder="Enter your email"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            confirm = st.text_input(
                "Confirm Password",
                type="password"
            )

            if st.button(
                "🚀 Create Account",
                type="primary",
                use_container_width=True
            ):

                if not name or not email or not password:

                    st.error(
                        "Please fill in all fields."
                    )

                elif password != confirm:

                    st.error(
                        "Passwords do not match."
                    )

                else:

                    success, message = register_user(
                        name,
                        email,
                        password
                    )

                    if success:

                        st.success(
                            message
                        )

                        st.info(
                            "Account created. "
                            "Go to Login to continue."
                        )

                    else:

                        st.error(
                            message
                        )

        with c2:

            st.info(
                """
                ### 🎯 Why join SpeakMate AI?

                ✅ AI Speaking Practice

                ✅ Voice Recording

                ✅ Grammar Correction

                ✅ Vocabulary Builder

                ✅ AI Interview Practice

                ✅ Progress Tracking
                """
            )


    # ========================================================
    # LOGIN
    # ========================================================

    elif option == "🔐 Login":

        st.header(
            "🔐 Welcome Back!"
        )

        st.write(
            "Login to continue your English learning journey."
        )

        c1, c2 = st.columns(2)

        with c1:

            email = st.text_input(
                "Email",
                placeholder="Enter your email"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            if st.button(
                "🔐 Login",
                type="primary",
                use_container_width=True
            ):

                user = login_user(
                    email,
                    password
                )

                if user:

                    st.session_state.logged_in = True

                    st.session_state.user = user

                    st.session_state.page = "Dashboard"

                    load_user_progress(
                        user["id"]
                    )

                    st.success(
                        "Login successful! 🎉"
                    )

                    st.rerun()

                else:

                    st.error(
                        "Invalid email or password."
                    )

        with c2:

            st.success(
                """
                ### 🤖 Your AI Learning Assistant

                🎤 Practice speaking

                🤖 Chat with AI

                ✍️ Correct grammar

                📚 Build vocabulary

                💼 Practice interviews

                📈 Track progress
                """
            )


# ============================================================
# MAIN APPLICATION
# ============================================================

else:

    user = st.session_state.user


    # ========================================================
    # SIDEBAR
    # ========================================================

    with st.sidebar:

        st.markdown(
            "## 🎤 SpeakMate AI"
        )

        st.write(
            f"👋 Hello, **{user['name']}**"
        )

        st.markdown(
            f'<div class="user-email">'
            f'{user["email"]}'
            f'</div>',
            unsafe_allow_html=True
        )

        st.divider()

        pages = [

            ("🏠 Dashboard", "Dashboard"),

            ("🎤 Speaking Practice", "Speaking"),

            ("🤖 AI Conversation", "Conversation"),

            ("✍️ Grammar Correction", "Grammar"),

            ("💼 AI Interview", "Interview"),

            ("📈 Progress", "Progress"),
        ]

        for label, page_name in pages:

            if page_name == st.session_state.page:

                st.markdown(
                    f'<div class="active-page">'
                    f'{label}'
                    f'</div>',
                    unsafe_allow_html=True
                )

            else:

                if st.button(
                    label,
                    use_container_width=True,
                    key=f"nav_{page_name}"
                ):

                    go_to(
                        page_name
                    )

        st.divider()

        if st.button(
            "🚪 Logout",
            use_container_width=True
        ):

            st.session_state.logged_in = False

            st.session_state.user = None

            st.session_state.page = "Dashboard"

            st.session_state.conversation_history = []

            st.session_state.skill_scores = (
                DEFAULT_SCORES.copy()
            )

            st.rerun()


    # ========================================================
    # DASHBOARD
    # ========================================================

    if st.session_state.page == "Dashboard":

        st.title(
            f"Welcome back, {user['name']}! 👋"
        )

        st.success(
            "🟢 SpeakMate AI is ready."
        )

        scores = st.session_state.skill_scores

        completed = [
            score
            for score in scores.values()
            if score > 0
        ]

        if completed:

            overall = round(
                sum(completed) / len(completed)
            )

        else:

            overall = 0

        counts = get_activity_counts(
            user["id"]
        )

        total_activities = sum(
            counts.values()
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "⭐ Overall Score",
            f"{overall}%"
        )

        c2.metric(
            "🎯 Activities",
            total_activities
        )

        c3.metric(
            "🏆 Skills",
            f"{len(completed)}/3"
        )

        c4.metric(
            "🔥 Streak",
            f"{get_streak(user['id'])} day(s)"
        )

        st.divider()

        st.header(
            "🚀 Start Practicing"
        )

        c1, c2 = st.columns(2)

        with c1:

            st.subheader(
                "🎤 Speaking Practice"
            )

            st.write(
                "Practice English by typing "
                "or recording your answer."
            )

            if st.button(
                "🎤 Start Speaking",
                key="dash_speaking",
                use_container_width=True
            ):

                go_to(
                    "Speaking"
                )

        with c2:

            st.subheader(
                "🤖 AI Conversation"
            )

            st.write(
                "Practice a natural conversation "
                "with your AI tutor."
            )

            if st.button(
                "🤖 Start Conversation",
                key="dash_conversation",
                use_container_width=True
            ):

                go_to(
                    "Conversation"
                )

        c1, c2 = st.columns(2)

        with c1:

            st.subheader(
                "✍️ Grammar Correction"
            )

            st.write(
                "Find mistakes and learn "
                "the correct English."
            )

            if st.button(
                "✍️ Check Grammar",
                key="dash_grammar",
                use_container_width=True
            ):

                go_to(
                    "Grammar"
                )

        with c2:

            st.subheader(
                "💼 AI Interview"
            )

            st.write(
                "Practice interview questions "
                "with AI feedback."
            )

            if st.button(
                "💼 Start Interview",
                key="dash_interview",
                use_container_width=True
            ):

                go_to(
                    "Interview"
                )

        c1, c2 = st.columns(2)

        with c1:

            st.subheader(
                "📈 Progress"
            )

            st.write(
                "Track your English "
                "learning progress."
            )

            if st.button(
                "📈 View Progress",
                key="dash_progress",
                use_container_width=True
            ):

                go_to(
                    "Progress"
                )


    # ========================================================
    # SPEAKING
    # ========================================================

    elif st.session_state.page == "Speaking":

        st.title(
            "🎤 English Speaking Practice"
        )

        st.write(
            "Choose a topic and answer by "
            "typing or speaking."
        )

        topic = st.selectbox(
            "Choose a topic",
            [
                "Introduce Yourself",
                "My College",
                "My Hobbies",
                "Technology",
                "My Career Goals",
                "Daily Life",
            ]
        )

        st.info(
            f"Tell me about: **{topic}**"
        )

        answer = st.text_area(
            "✍️ Type your answer",
            height=180,
            placeholder="Write what you would say..."
        )

        audio = st.audio_input(
            "🎤 Or record your answer"
        )

        if audio is not None:

            st.success(
                "✅ Voice recording captured!"
            )

            st.audio(
                audio
            )

        if st.button(
            "✨ Analyze My Answer with AI",
            type="primary",
            use_container_width=True
        ):

            if answer.strip():

                prompt = f"""
You are an English speaking tutor.

Topic:
{topic}

Student answer:
{answer}

Return exactly:

Score: [NUMBER]/100
The NUMBER must be an integer from 0 to 100. Never write NN or a placeholder.

Fluency:
Give brief feedback.

Grammar:
Mention important grammar mistakes.

Vocabulary:
Comment on vocabulary and suggest improvements.

Correction:
Give a natural improved version.

Feedback:
Give 2 useful tips.

Next Practice:
Ask one short follow-up question.

Evaluate English quality, not knowledge of the topic.
Be encouraging.
"""

                try:

                    with st.spinner(
                        "🤖 AI is analyzing your answer..."
                    ):

                        result = ask_ai(
                            prompt
                        )

                    score = update_score(
                        "Speaking",
                        result
                    )

                    if score is None:
                        score = 0

                    save_speaking_session(
                        user["id"],
                        transcript=answer,
                        overall_score=score
                    )

                    st.subheader(
                        "🤖 AI Speaking Feedback"
                    )

                    st.markdown(
                        result
                    )

                except Exception as e:

                    st.error(
                        f"AI error: {e}"
                    )

            elif audio is not None:

                try:

                    with st.spinner(
                        "🎤 AI is listening to your answer..."
                    ):

                        result = analyze_voice(
                            audio.getvalue(),
                            topic
                        )

                    score = update_score(
                        "Speaking",
                        result
                    )

                    if score is None:
                        score = 0

                    save_speaking_session(
                        user["id"],
                        transcript="Voice recording",
                        overall_score=score
                    )

                    st.subheader(
                        "🤖 AI Voice Speaking Feedback"
                    )

                    st.markdown(
                        result
                    )

                except Exception as e:

                    st.error(
                        f"Voice AI error: {e}"
                    )

            else:

                st.warning(
                    "Please type an answer or "
                    "record your voice first."
                )


    # ========================================================
    # AI CONVERSATION
    # ========================================================

    elif st.session_state.page == "Conversation":

        st.title(
            "🤖 AI Conversation"
        )

        st.success(
            "🟢 AI Conversation is active."
        )

        st.divider()

        for message in st.session_state.conversation_history:

            with st.chat_message(
                message["role"]
            ):

                st.write(
                    message["content"]
                )

        user_message = st.chat_input(
            "Type your message here..."
        )

        if user_message:

            st.session_state.conversation_history.append(
                {
                    "role": "user",
                    "content": user_message
                }
            )

            try:

                ai_response = get_ai_response(
                    user_message,
                    st.session_state.conversation_history[:-1]
                )

                st.session_state.conversation_history.append(
                    {
                        "role": "assistant",
                        "content": ai_response
                    }
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"AI error: {e}"
                )

        if st.button(
            "🔄 Start New Conversation"
        ):

            st.session_state.conversation_history = []

            st.rerun()


    # ========================================================
    # GRAMMAR
    # ========================================================

    elif st.session_state.page == "Grammar":

        st.title(
            "✍️ Grammar Correction"
        )

        st.write(
            "Enter a sentence and AI "
            "will correct it."
        )

        sentence = st.text_area(
            "Your sentence",
            height=150,
            placeholder="Example: I am go to college yesterday."
        )

        if st.button(
            "✨ Check Grammar with AI",
            type="primary",
            use_container_width=True
        ):

            if not sentence.strip():

                st.warning(
                    "Please enter a sentence."
                )

            else:

                prompt = f"""
You are an English grammar tutor.

Student sentence:
"{sentence}"

Return exactly these sections:

Score: [NUMBER]/100
The NUMBER must be an integer from 0 to 100. Never write NN or a placeholder.

Corrected Sentence:
Give the correct sentence.

Mistakes:
List important grammar mistakes.

Explanation:
Explain the mistakes using simple English.

Natural English:
Give a more natural version.

Practice:
Give one short practice sentence.

Be encouraging and suitable for a college student.
"""

                try:

                    with st.spinner(
                        "AI is checking your grammar..."
                    ):

                        result = ask_ai(
                            prompt
                        )

                    score = update_score(
                        "Grammar",
                        result
                    )

                    if score is None:
                        score = 0

                    save_grammar_session(
                        user["id"],
                        sentence,
                        score,
                        result
                    )

                    st.subheader(
                        "🤖 AI Grammar Feedback"
                    )

                    st.markdown(
                        result
                    )

                except Exception as e:

                    st.error(
                        f"AI error: {e}"
                    )


    # ========================================================
    # AI INTERVIEW
    # ========================================================

    elif st.session_state.page == "Interview":

        st.title(
            "💼 AI Interview Practice"
        )

        st.write(
            "Practice different interview questions "
            "using text or your voice."
        )

        interview_type = st.selectbox(
            "Interview Type",
            [
                "HR Interview",
                "Technical Interview",
                "Python Interview",
                "Communication Round",
            ],
            key="interview_type_select"
        )


        # ----------------------------------------------------
        # CREATE QUESTION WHEN CATEGORY CHANGES
        # ----------------------------------------------------

        if (
            st.session_state.current_interview_type
            != interview_type
        ):

            st.session_state.current_interview_type = (
                interview_type
            )

            st.session_state.current_interview_question = (
                get_new_interview_question(
                    interview_type
                )
            )


        # ----------------------------------------------------
        # CREATE QUESTION IF NONE EXISTS
        # ----------------------------------------------------

        if (
            st.session_state.current_interview_question
            is None
        ):

            st.session_state.current_interview_question = (
                get_new_interview_question(
                    interview_type
                )
            )


        question = (
            st.session_state.current_interview_question
        )


        st.info(
            f"**Interview Type:** {interview_type}"
        )

        st.subheader(
            "Question"
        )

        st.write(
            f"### {question}"
        )


        # ----------------------------------------------------
        # NEXT QUESTION
        # ----------------------------------------------------

        if st.button(
            "🔄 Give Me Another Question",
            use_container_width=True
        ):

            st.session_state.current_interview_question = (
                get_new_interview_question(
                    interview_type
                )
            )

            st.rerun()


        # ----------------------------------------------------
        # TEXT ANSWER
        # ----------------------------------------------------

        answer = st.text_area(
            "⌨️ Type Your Answer",
            height=180,
            placeholder="Type your interview answer here..."
        )


        # ----------------------------------------------------
        # VOICE ANSWER
        # ----------------------------------------------------

        st.write(
            "### 🎤 Or Speak Your Answer"
        )

        audio = st.audio_input(
            "🎤 Record your interview answer"
        )


        if audio is not None:

            st.success(
                "✅ Voice recording captured!"
            )

            st.audio(
                audio
            )


        # ----------------------------------------------------
        # EVALUATE
        # ----------------------------------------------------

        if st.button(
            "✨ Evaluate Answer with AI",
            type="primary",
            use_container_width=True
        ):

            if not answer.strip() and audio is None:

                st.warning(
                    "Please type your answer or "
                    "record your voice first."
                )

            else:

                try:

                    # ==================================================
                    # VOICE INTERVIEW
                    # ==================================================

                    if audio is not None and not answer.strip():

                        with st.spinner(
                            "🎤 AI is listening to your interview answer..."
                        ):

                            result = analyze_voice(
                                audio.getvalue(),
                                question
                            )

                        score = update_score(
                            "Interview",
                            result
                        )

                        if score is None:
                            score = 0

                        save_interview_session(
                            user["id"],
                            interview_type,
                            question,
                            "Voice Answer",
                            score,
                            result
                        )

                        st.subheader(
                            "🤖 AI Interview Feedback"
                        )

                        st.markdown(
                            result
                        )


                    # ==================================================
                    # TEXT INTERVIEW
                    # ==================================================

                    else:

                        prompt = f"""
You are a professional interview coach.

Interview type:
{interview_type}

Question:
{question}

Candidate answer:
{answer}

Evaluate the answer.

Return exactly these sections:

Score: [NUMBER]/100
The NUMBER must be an integer from 0 to 100. Never write NN or a placeholder.

Strengths:
Mention what was done well.

Weaknesses:
Mention important areas to improve.

Communication:
Evaluate clarity, grammar, confidence and organization.

Technical/Content Feedback:
Evaluate relevance and quality of the answer.

Improved Answer:
Give a stronger but realistic answer for a college student.

Interview Tip:
Give 2 short tips.

Follow-up Question:
Ask one realistic interviewer question.

Be honest but encouraging.
"""

                        with st.spinner(
                            "🤖 AI is evaluating your answer..."
                        ):

                            result = ask_ai(
                                prompt
                            )

                        score = update_score(
                            "Interview",
                            result
                        )

                        if score is None:
                            score = 0

                        save_interview_session(
                            user["id"],
                            interview_type,
                            question,
                            answer,
                            score,
                            result
                        )

                        st.subheader(
                            "🤖 AI Interview Feedback"
                        )

                        st.markdown(
                            result
                        )

                except Exception as e:

                    st.error(
                        f"Interview AI error: {e}"
                    )


    # ========================================================
    # PROGRESS
    # ========================================================

    elif st.session_state.page == "Progress":

        st.title(
            "📈 Your AI Learning Progress"
        )

        load_user_progress(
            user["id"]
        )

        scores = st.session_state.skill_scores

        st.write(
            "Your progress is saved to your account."
        )

        st.divider()


        # ----------------------------------------------------
        # SKILL SCORES
        # ----------------------------------------------------

        for skill, score in scores.items():

            if score > 0:

                st.write(
                    f"### {skill} — {score:.0f}%"
                )

                st.progress(
                    min(
                        score / 100,
                        1.0
                    )
                )

            else:

                st.write(
                    f"### {skill} — Not attempted yet"
                )


        completed = [
            score
            for score in scores.values()
            if score > 0
        ]


        if completed:

            overall = round(
                sum(completed) / len(completed)
            )

            st.divider()

            st.metric(
                "⭐ Overall AI Score",
                f"{overall}%"
            )


        # ----------------------------------------------------
        # ACTIVITY HISTORY
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "📋 Recent Activities"
        )

        activities = get_recent_activities(
            user["id"],
            10
        )

        if activities:

            for activity in activities:

                score = activity.get(
                    "score",
                    0
                )

                created = activity.get(
                    "created_at",
                    ""
                )

                st.write(
                    f"• **{activity['activity']}** "
                    f"— {score:.0f}% "
                    f"— {created}"
                )

        else:

            st.info(
                "No activities completed yet."
            )


        # ----------------------------------------------------
        # AI PROGRESS COACH
        # ----------------------------------------------------

        if completed:

            progress_prompt = f"""
You are SpeakMate AI's learning coach.

Current scores:

Speaking: {scores['Speaking']}%
Grammar: {scores['Grammar']}%
Interview: {scores['Interview']}%

Give a short personalized progress report.

Include:

1. Strongest area
2. Area needing most improvement
3. A practical 3-step study plan
4. One encouraging message

Do not invent scores.
"""

            try:

                with st.spinner(
                    "🤖 AI is preparing your progress report..."
                ):

                    progress_report = ask_ai(
                        progress_prompt
                    )

                st.subheader(
                    "🤖 AI Progress Coach"
                )

                st.markdown(
                    progress_report
                )

            except Exception as e:

                st.error(
                    f"AI error: {e}"
                )

        else:

            st.info(
                "Complete at least one AI activity "
                "to generate your progress report."
            )