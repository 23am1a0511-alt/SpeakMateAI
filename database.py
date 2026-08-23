import sqlite3
from datetime import date, datetime, timedelta


DATABASE_NAME = "speakmate.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    return connection


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # SPEAKING SESSIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS speaking_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transcript TEXT,
            grammar_score REAL,
            fluency_score REAL,
            vocabulary_score REAL,
            pronunciation_score REAL,
            overall_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # VOCABULARY
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            meaning TEXT,
            example TEXT,
            learned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # INTERVIEW SESSIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            interview_type TEXT,
            question TEXT,
            answer TEXT,
            score REAL,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # STREAKS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_practice_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --------------------------------------------------------
    # BADGES
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_name TEXT NOT NULL,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


# ============================================================
# SAVE SPEAKING ACTIVITY
# ============================================================

def save_speaking_session(
    user_id,
    transcript="",
    overall_score=0,
    grammar_score=0,
    fluency_score=0,
    vocabulary_score=0,
    pronunciation_score=0
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO speaking_sessions (
            user_id,
            transcript,
            grammar_score,
            fluency_score,
            vocabulary_score,
            pronunciation_score,
            overall_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        transcript,
        grammar_score,
        fluency_score,
        vocabulary_score,
        pronunciation_score,
        overall_score
    ))

    connection.commit()
    connection.close()

    update_streak(user_id)


# ============================================================
# SAVE INTERVIEW ACTIVITY
# ============================================================

def save_interview_session(
    user_id,
    interview_type,
    question,
    answer,
    score,
    feedback
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO interview_sessions (
            user_id,
            interview_type,
            question,
            answer,
            score,
            feedback
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        interview_type,
        question,
        answer,
        score,
        feedback
    ))

    connection.commit()
    connection.close()

    update_streak(user_id)


# ============================================================
# SAVE VOCABULARY WORD
# ============================================================

def save_vocabulary_word(
    user_id,
    word,
    meaning="",
    example=""
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO vocabulary (
            user_id,
            word,
            meaning,
            example
        )
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        word,
        meaning,
        example
    ))

    connection.commit()
    connection.close()


# ============================================================
# GET USER SPEAKING SCORE
# ============================================================

def get_speaking_score(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT overall_score
        FROM speaking_sessions
        WHERE user_id = ?
        AND overall_score IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))

    row = cursor.fetchone()

    connection.close()

    if row:
        return float(row["overall_score"])

    return 0


# ============================================================
# GET USER INTERVIEW SCORE
# ============================================================

def get_interview_score(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT score
        FROM interview_sessions
        WHERE user_id = ?
        AND score IS NOT NULL
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))

    row = cursor.fetchone()

    connection.close()

    if row:
        return float(row["score"])

    return 0


# ============================================================
# GET ACTIVITY COUNTS
# ============================================================

def get_activity_counts(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM speaking_sessions
        WHERE user_id = ?
    """, (user_id,))

    speaking_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM interview_sessions
        WHERE user_id = ?
    """, (user_id,))

    interview_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM vocabulary
        WHERE user_id = ?
    """, (user_id,))

    vocabulary_count = cursor.fetchone()[0]

    connection.close()

    return {
        "Speaking": speaking_count,
        "Interview": interview_count,
        "Vocabulary": vocabulary_count
    }


# ============================================================
# GET USER PROGRESS
# ============================================================

def get_user_progress(user_id):

    speaking_score = get_speaking_score(user_id)
    interview_score = get_interview_score(user_id)

    return {
        "Speaking": speaking_score,
        "Grammar": 0,
        "Vocabulary": 0,
        "Interview": interview_score
    }


# ============================================================
# GET RECENT ACTIVITIES
# ============================================================

def get_recent_activities(user_id, limit=10):

    connection = get_connection()
    cursor = connection.cursor()

    activities = []

    cursor.execute("""
        SELECT
            'Speaking' AS activity,
            overall_score AS score,
            created_at
        FROM speaking_sessions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))

    speaking_rows = cursor.fetchall()

    for row in speaking_rows:
        activities.append({
            "activity": row["activity"],
            "score": row["score"],
            "created_at": row["created_at"]
        })

    cursor.execute("""
        SELECT
            interview_type AS activity,
            score,
            created_at
        FROM interview_sessions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))

    interview_rows = cursor.fetchall()

    for row in interview_rows:
        activities.append({
            "activity": row["activity"],
            "score": row["score"],
            "created_at": row["created_at"]
        })

    activities.sort(
        key=lambda x: x["created_at"],
        reverse=True
    )

    connection.close()

    return activities[:limit]


# ============================================================
# STREAK
# ============================================================

def update_streak(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    today = date.today().isoformat()

    cursor.execute("""
        SELECT
            current_streak,
            longest_streak,
            last_practice_date
        FROM streaks
        WHERE user_id = ?
    """, (user_id,))

    row = cursor.fetchone()

    if row is None:

        cursor.execute("""
            INSERT INTO streaks (
                user_id,
                current_streak,
                longest_streak,
                last_practice_date
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            1,
            1,
            today
        ))

    else:

        current_streak = row["current_streak"]
        longest_streak = row["longest_streak"]
        last_date = row["last_practice_date"]

        if last_date == today:
            connection.close()
            return

        current_streak += 1

        if current_streak > longest_streak:
            longest_streak = current_streak

        cursor.execute("""
            UPDATE streaks
            SET
                current_streak = ?,
                longest_streak = ?,
                last_practice_date = ?
            WHERE user_id = ?
        """, (
            current_streak,
            longest_streak,
            today,
            user_id
        ))

    connection.commit()
    connection.close()


# ============================================================
# GET STREAK
# ============================================================

def get_streak(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT current_streak
        FROM streaks
        WHERE user_id = ?
    """, (user_id,))

    row = cursor.fetchone()

    connection.close()

    if row:
        return row["current_streak"]

    return 0


# ============================================================
# GET USER
# ============================================================

def get_user_by_id(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, email
        FROM users
        WHERE id = ?
    """, (user_id,))

    row = cursor.fetchone()

    connection.close()

    if row:
        return {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"]
        }

    return None


# ============================================================
# GET DAILY PROGRESS
# ============================================================

def get_daily_progress(user_id, days=30):

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # SPEAKING DATA
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            DATE(created_at) AS practice_date,
            AVG(overall_score) AS average_score,
            COUNT(*) AS activity_count
        FROM speaking_sessions
        WHERE user_id = ?
        GROUP BY DATE(created_at)
    """, (user_id,))

    speaking_rows = cursor.fetchall()

    # --------------------------------------------------------
    # INTERVIEW DATA
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            DATE(created_at) AS practice_date,
            AVG(score) AS average_score,
            COUNT(*) AS activity_count
        FROM interview_sessions
        WHERE user_id = ?
        GROUP BY DATE(created_at)
    """, (user_id,))

    interview_rows = cursor.fetchall()

    connection.close()

    # --------------------------------------------------------
    # COMBINE DATA
    # --------------------------------------------------------

    daily_data = {}

    for row in speaking_rows:

        day = row["practice_date"]

        if day not in daily_data:
            daily_data[day] = {
                "date": day,
                "total_score": 0,
                "activities": 0
            }

        score = float(row["average_score"] or 0)
        count = int(row["activity_count"])

        daily_data[day]["total_score"] += score * count
        daily_data[day]["activities"] += count

    for row in interview_rows:

        day = row["practice_date"]

        if day not in daily_data:
            daily_data[day] = {
                "date": day,
                "total_score": 0,
                "activities": 0
            }

        score = float(row["average_score"] or 0)
        count = int(row["activity_count"])

        daily_data[day]["total_score"] += score * count
        daily_data[day]["activities"] += count

    # --------------------------------------------------------
    # CREATE RESULT
    # --------------------------------------------------------

    result = []

    for day in sorted(daily_data.keys()):

        data = daily_data[day]

        if data["activities"] > 0:
            average = (
                data["total_score"]
                / data["activities"]
            )
        else:
            average = 0

        result.append({
            "Date": day,
            "Score": round(average, 2),
            "Activities": data["activities"]
        })

    # Return only the requested number of days
    return result[-days:]


# ============================================================
# INITIALIZE DATABASE
# ============================================================

create_tables()