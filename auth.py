import bcrypt
from database import get_connection


def hash_password(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def check_password(password, password_hash):
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


def register_user(name, email, password):
    connection = get_connection()
    cursor = connection.cursor()

    password_hash = hash_password(password)

    try:
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (name, email, password_hash)
        )

        connection.commit()
        return True, "Registration successful!"

    except Exception:
        return False, "Email already registered."

    finally:
        connection.close()


def login_user(email, password):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name, email, password_hash
        FROM users
        WHERE email = ?
        """,
        (email,)
    )

    user = cursor.fetchone()
    connection.close()

    if user and check_password(password, user[3]):
        return {
            "id": user[0],
            "name": user[1],
            "email": user[2]
        }

    return None