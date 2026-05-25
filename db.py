import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

import hashlib
import secrets

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pitches (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL DEFAULT 'anonymous',
                title TEXT NOT NULL,
                pitch TEXT NOT NULL,
                style TEXT DEFAULT 'corporate',
                grading TEXT DEFAULT '',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );        
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Database ready")
    except Exception as e:
        print(f"DB init failed {e}")


def save_pitch(session_id, title, pitch, style, grading, user_id=None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pitches (session_id, title, pitch, style, grading, user_id) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (session_id, title, pitch, style, grading, user_id),
        )
        pitch_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return pitch_id
    except Exception as e:
        print(f"saving pitch failed {e}")
        return None


def get_pitch_history(session_id, limit=20):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, title, style, grading, created_at FROM pitches WHERE session_id=%s ORDER BY created_at DESC LIMIT %s",
            (session_id, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"⚠️ get_history failed: {e}")
        return []


def get_pitch_by_id(pitch_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM pitches WHERE id=%s", (pitch_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        result = dict(row)
        if result.get("created_at"):
            result["created_at"] = result["created_at"].isoformat()
        return result
    except Exception as e:
        print(f"⚠️ get_by_id failed: {e}")
        return None


def hash_password(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password, stored):
    try:
        salt, hashed = stored.split(":")
        return hashlib.sha256((password + salt).encode()).hexdigest() == hashed
    except:
        return False


def init_users_table():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            ALTER TABLE pitches ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Users table ready")
    except Exception as e:
        print(f"Users table init failed: {e}")


def create_user(username, email, password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (username, email, hash_password(password)),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return user_id
    except Exception as e:
        print(f"create_user failed: {e}")
        return None


def get_user_by_email(email):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_user failed: {e}")
        return None


def get_user_by_id(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, email, created_at FROM users WHERE id=%s", (user_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        return None


def get_user_pitches(user_id, limit=50):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, title, style, grading, created_at FROM pitches WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        return []


def get_user_stats(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT 
                COUNT(*) as total_pitches,
                COUNT(DISTINCT style) as styles_used,
                MAX(created_at) as last_pitch,
                MIN(created_at) as first_pitch
            FROM pitches WHERE user_id=%s
        """,
            (user_id,),
        )
        row = dict(cur.fetchone())
        cur.execute(
            """
            SELECT style, COUNT(*) as count 
            FROM pitches WHERE user_id=%s 
            GROUP BY style ORDER BY count DESC
        """,
            (user_id,),
        )
        row["style_breakdown"] = [dict(r) for r in cur.fetchall()]
        for k in ["last_pitch", "first_pitch"]:
            if row.get(k):
                row[k] = row[k].isoformat()
        cur.close()
        conn.close()
        return row
    except Exception as e:
        return {}
