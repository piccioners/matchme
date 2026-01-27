from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_conn, init_db
import json

app = Flask(__name__)
CORS(app)

# ---------- LOGICA MATCH ----------

def is_compatible(me, other):
    # niente se stesso: stessa coppia nome+tavolo
    if str(me["name"]) == str(other["name"]) and str(me["table"]) == str(other["table"]):
        return False

    i_ok = (me["like"] == "entrambi") or (other["gender"] == me["like"])
    o_ok = (other["like"] == "entrambi") or (me["gender"] == other["like"])

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
        conn.execute(
            """
            INSERT INTO users (event_id, name, table_number, gender, like, interests_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                data["name"],
                data["table"],
                data["gender"],
                data["like"],
                json.dumps(data["interests"])
            )
        )
        conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE event_id = ?",
            (event_id,)
        ).fetchone()["c"]

    return jsonify({"status": "ok", "count": count})

@app.route("/users")
def users():
    event_id = request.args.get("event_id") or "DEFAULT"

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, table_number, gender, like, interests_json FROM users WHERE event_id = ?",
            (event_id,)
        ).fetchall()

    out = []
    for r in rows:
        out.append({
            "name": r["name"],
            "table": r["table_number"],
            "gender": r["gender"],
            "like": r["like"],
            "interests": json.loads(r["interests_json"])
        })

    return jsonify(out)

@app.route("/matches", methods=["POST"])
def matches():
    me = request.json
    event_id = me.get("event_id") or "DEFAULT"

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, table_number, gender, like, interests_json FROM users WHERE event_id = ?",
            (event_id,)
        ).fetchall()

    candidates = []

    for r in rows:
        other = {
            "name": r["name"],
            "table": r["table_number"],
            "gender": r["gender"],
            "like": r["like"],
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
        conn.execute(
            "DELETE FROM users WHERE event_id = ?",
            (event_id,)
        )
        conn.commit()

    return jsonify({"status": "ok", "reset": event_id})

# ---------- STARTUP ----------

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

