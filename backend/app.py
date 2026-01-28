from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_conn, init_db
import json

app = Flask(__name__)
CORS(app)

# ---------- LOGICA MATCH ----------

def is_compatible(me, other):
    # niente se stesso
    if str(me["name"]) == str(other["name"]) and str(me["table"]) == str(other["table"]):
        return False

    i_ok = (me["looking_for"] == "entrambi") or (other["gender"] == me["looking_for"])
    o_ok = (other["looking_for"] == "entrambi") or (me["gender"] == other["looking_for"])

    return i_ok and o_ok

def interest_score(me, other):
    keys = ["musica","sport","viaggi","cinema","tech","nightlife"]
    diffs = []
    for k in keys:
        a = int(me["interests"][k])
        b = int(other["interests"][k])
        diffs.append(abs(a - b))
    avg = sum(diffs) / len(diffs)
    score = round((1 - (avg / 4)) * 100)
    return max(0, min(100, score))

# ---------- ROUTES ----------

@app.route("/")
def home():
    return "Backend Match Me attivo"

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    event_id = data.get("event_id") or "DEFAULT"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users
                (event_id, name, table_number, gender, looking_for, interests_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    data["name"],
                    data["table"],
                    data["gender"],
                    data["looking_for"],
                    json.dumps(data["interests"])
                )
            )
        conn.commit()

    return jsonify({"status": "ok"})

@app.route("/users")
def users():
    event_id = request.args.get("event_id") or "DEFAULT"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, table_number, gender, looking_for, interests_json
                FROM users
                WHERE event_id = %s
                """,
                (event_id,)
            )
            rows = cur.fetchall()

    out = []
    for r in rows:
        out.append({
            "name": r["name"],
            "table": r["table_number"],
            "gender": r["gender"],
            "looking_for": r["looking_for"],
            "interests": json.loads(r["interests_json"])
        })

    return jsonify(out)

@app.route("/matches", methods=["POST"])
def matches():
    me = request.json
    event_id = me.get("event_id") or "DEFAULT"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, table_number, gender, looking_for, interests_json
                FROM users
                WHERE event_id = %s
                """,
                (event_id,)
            )
            rows = cur.fetchall()

    candidates = []

    for r in rows:
        other = {
            "name": r["name"],
            "table": r["table_number"],
            "gender": r["gender"],
            "looking_for": r["looking_for"],
            "interests": json.loads(r["interests_json"])
        }

        if not is_compatible(me, other):
            continue

        candidates.append({
            "name": other["name"],
            "table": other["table"],
            "gender": other["gender"],
            "score": interest_score(me, other)
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    return jsonify({
        "status": "ok",
        "matches": candidates[:5]
    })

@app.route("/reset", methods=["POST"])
def reset():
    data = request.json or {}
    event_id = data.get("event_id") or "DEFAULT"

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM users WHERE event_id = %s",
                (event_id,)
            )
        conn.commit()

    return jsonify({"status": "ok", "reset": event_id})

# ---------- STARTUP ----------

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
