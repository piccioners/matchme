import os
import uuid
import json
import random
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras

APP_NAME = "meety-api"
TABLE_NAME = "meety_users"

def now_utc():
    return datetime.now(timezone.utc)

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL missing (Railway Postgres not connected).")
    return psycopg2.connect(db_url)

def init_db():
    conn = get_db()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
              id UUID PRIMARY KEY,
              event_id TEXT NOT NULL,
              session_token TEXT UNIQUE NOT NULL,
              created_at TIMESTAMPTZ NOT NULL,

              name TEXT NOT NULL,
              table_no TEXT NOT NULL,

              gender_me TEXT,
              gender_seek TEXT,
              status TEXT,
              purpose TEXT,
              zodiac TEXT,
              drink TEXT,
              music TEXT,

              answers JSONB
            );
            """)
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_event_id ON {TABLE_NAME}(event_id);")
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_session_token ON {TABLE_NAME}(session_token);")
    finally:
        conn.close()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "name": APP_NAME})

@app.get("/")
def root():
    return "ok", 200

def auth_user():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        return None, jsonify({"error": "missing_token"}), 401

    conn = get_db()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE session_token=%s", (token,))
            row = cur.fetchone()
            if not row:
                return None, jsonify({"error": "invalid_token"}), 401
            return row, None, None
    finally:
        conn.close()

def require_admin():
    expected = (os.environ.get("ADMIN_KEY") or "").strip()
    if not expected:
        return False, jsonify({"error": "admin_not_configured"}), 500

    got = (request.headers.get("X-Admin-Key") or "").strip()
    if not got or got != expected:
        return False, jsonify({"error": "forbidden"}), 403

    return True, None, None

@app.post("/api/admin/clear_event")
def admin_clear_event():
    ok, err, code = require_admin()
    if not ok:
        return err, code

    data = request.get_json(force=True, silent=True) or {}
    event_id = (data.get("event_id") or "").strip()
    if not event_id:
        return jsonify({"error": "missing_event_id"}), 400

    conn = get_db()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(f"DELETE FROM {TABLE_NAME} WHERE event_id=%s", (event_id,))
            deleted = cur.rowcount
        return jsonify({"ok": True, "event_id": event_id, "deleted": deleted})
    finally:
        conn.close()

@app.post("/api/admin/seed_demo")
def admin_seed_demo():
    ok, err, code = require_admin()
    if not ok:
        return err, code

    data = request.get_json(force=True, silent=True) or {}
    event_id = (data.get("event_id") or "").strip()
    count = data.get("count", 10)

    try:
        count = int(count)
    except Exception:
        count = 10

    if not event_id:
        return jsonify({"error": "missing_event_id"}), 400

    if count < 1:
        return jsonify({"error": "count_too_small"}), 400
    if count > 50:
        return jsonify({"error": "count_too_large"}), 400

    names_pool = [
        "Anna","Giulia","Martina","Sara","Elena","Chiara","Francesca","Valeria",
        "Luca","Marco","Matteo","Andrea","Davide","Gabriele","Simone","Federico",
        "Alex","Sam","Nico","Vale"
    ]
    zodiacs = ["Ariete","Toro","Gemelli","Cancro","Leone","Vergine","Bilancia","Scorpione","Sagittario","Capricorno","Acquario","Pesci"]
    drinks = ["Spritz / Aperitivo","Gin Tonic","Birra","Vino","Cocktail dolce","Cocktail amaro","Analcolico","Mi va tutto"]
    musics = ["Pop","Rap / Trap","House","Techno / EDM","Reggaeton","Rock","Indie","Di tutto"]
    statuses = ["Single","Impegnato/a","Complicato","Preferisco non dirlo"]
    purposes = ["Flirt","Conoscere gente","Divertirmi","Vediamo che succede"]

    gender_me_options = ["Uomo","Donna","Altro","Preferisco non dirlo"]
    gender_seek_options = ["Uomo","Donna","Tutti","Indifferente"]

    tables_pool = ["1","2","3","4","5","6","7","8","9","10","20","21","22","23","60","61","62","63","64","65"]

    created = 0

    conn = get_db()
    try:
        with conn, conn.cursor() as cur:
            for i in range(count):
                user_id = uuid.uuid4()
                session_token = uuid.uuid4().hex + uuid.uuid4().hex

                name = random.choice(names_pool) + "Demo" + str(random.randint(1, 999))
                table_no = random.choice(tables_pool)

                gender_me = random.choice(gender_me_options)
                gender_seek = random.choice(gender_seek_options)

                status = random.choice(statuses)
                purpose = random.choice(purposes)
                zodiac = random.choice(zodiacs)
                drink = random.choice(drinks)
                music = random.choice(musics)

                answers = [random.randint(1, 5) for _ in range(10)]

                cur.execute(f"""
                  INSERT INTO {TABLE_NAME}(
                    id, event_id, session_token, created_at,
                    name, table_no,
                    gender_me, gender_seek, status, purpose, zodiac, drink, music,
                    answers
                  )
                  VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    str(user_id), event_id, session_token, now_utc(),
                    name, table_no,
                    gender_me, gender_seek, status, purpose, zodiac, drink, music,
                    json.dumps(answers)
                ))
                created += 1

        return jsonify({"ok": True, "event_id": event_id, "created": created})
    finally:
        conn.close()

@app.post("/api/register")
def register():
    data = request.get_json(force=True, silent=True) or {}

    event_id = (data.get("event_id") or "").strip()
    name = (data.get("name") or "").strip()
    table_no = str((data.get("table") or "")).strip()

    gender_me = (data.get("gender_me") or "").strip() or None
    gender_seek = (data.get("gender_seek") or "").strip() or None
    status = (data.get("status") or "").strip() or None
    purpose = (data.get("purpose") or "").strip() or None
    zodiac = (data.get("zodiac") or "").strip() or None
    drink = (data.get("drink") or "").strip() or None
    music = (data.get("music") or "").strip() or None

    if not event_id or not name or not table_no:
        return jsonify({"error": "missing_fields"}), 400

    user_id = uuid.uuid4()
    session_token = uuid.uuid4().hex + uuid.uuid4().hex

    conn = get_db()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(f"""
              INSERT INTO {TABLE_NAME}(
                id, event_id, session_token, created_at,
                name, table_no,
                gender_me, gender_seek, status, purpose, zodiac, drink, music,
                answers
              )
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                str(user_id), event_id, session_token, now_utc(),
                name, table_no,
                gender_me, gender_seek, status, purpose, zodiac, drink, music,
                None
            ))

        return jsonify({
            "ok": True,
            "session_token": session_token,
            "user_id": str(user_id),
            "event_id": event_id
        })
    finally:
        conn.close()

@app.get("/api/me")
def me():
    user, err, code = auth_user()
    if err:
        return err, code

    return jsonify({
        "ok": True,
        "event_id": user["event_id"],
        "name": user["name"],
        "table": user["table_no"],
        "profile": {
            "gender_me": user["gender_me"],
            "gender_seek": user["gender_seek"],
            "status": user["status"],
            "purpose": user["purpose"],
            "zodiac": user["zodiac"],
            "drink": user["drink"],
            "music": user["music"],
        },
        "has_answers": user["answers"] is not None
    })

@app.post("/api/answers")
def save_answers():
    user, err, code = auth_user()
    if err:
        return err, code

    data = request.get_json(force=True, silent=True) or {}
    answers = data.get("answers")

    if not isinstance(answers, list) or len(answers) != 10:
        return jsonify({"error": "answers_must_be_list_of_10"}), 400
    if any((not isinstance(x, int) or x < 1 or x > 5) for x in answers):
        return jsonify({"error": "answers_values_1_to_5"}), 400

    conn = get_db()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(f"""
              UPDATE {TABLE_NAME}
              SET answers=%s
              WHERE session_token=%s
            """, (json.dumps(answers), user["session_token"]))
        return jsonify({"ok": True})
    finally:
        conn.close()

@app.get("/api/participants")
def participants():
    user, err, code = auth_user()
    if err:
        return err, code

    event_id = user["event_id"]

    conn = get_db()
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
              SELECT
                name, table_no,
                gender_me, gender_seek,
                status, purpose, zodiac, drink, music,
                answers
              FROM {TABLE_NAME}
              WHERE event_id=%s AND session_token<>%s AND answers IS NOT NULL
            """, (event_id, user["session_token"]))
            rows = cur.fetchall()

        out = []
        for r in rows:
            out.append({
                "name": r["name"],
                "table": r["table_no"],
                "gender_me": r["gender_me"] or "",
                "gender_seek": r["gender_seek"] or "",
                "zodiac": r["zodiac"] or "",
                "drink": r["drink"] or "",
                "music": r["music"] or "",
                "answers": r["answers"]
            })
        return jsonify({"ok": True, "event_id": event_id, "participants": out})
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
