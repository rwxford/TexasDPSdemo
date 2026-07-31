#!/usr/bin/env python3
"""Statewide Criminal Activity Tracking System (CATS) — Texas DPS demo.

Zero-dependency web application built on the Python standard library:
  * http.server for the HTTP + JSON API and static file serving
  * sqlite3 for storage (auto-created and seeded on first run)

Every record produced here is SYNTHETIC and for demonstration only.
Run with:  python3 app.py   then open http://localhost:8000
"""

import json
import os
import random
import sqlite3
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cats.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
PORT = int(os.environ.get("PORT", "8000"))

# --------------------------------------------------------------------------
# Reference data — NIBRS offense taxonomy used by Texas UCR reporting.
# Each offense: code, description, NIBRS category, Group (A or B).
# --------------------------------------------------------------------------
OFFENSES = [
    # Crimes Against Persons
    ("09A", "Murder & Nonnegligent Manslaughter", "Crimes Against Persons", "A"),
    ("09B", "Negligent Manslaughter", "Crimes Against Persons", "A"),
    ("13A", "Aggravated Assault", "Crimes Against Persons", "A"),
    ("13B", "Simple Assault", "Crimes Against Persons", "A"),
    ("100", "Kidnapping/Abduction", "Crimes Against Persons", "A"),
    ("11A", "Rape", "Crimes Against Persons", "A"),
    ("64A", "Human Trafficking, Commercial Sex Acts", "Crimes Against Persons", "A"),
    # Crimes Against Property
    ("120", "Robbery", "Crimes Against Property", "A"),
    ("220", "Burglary/Breaking & Entering", "Crimes Against Property", "A"),
    ("23F", "Theft From Motor Vehicle", "Crimes Against Property", "A"),
    ("240", "Motor Vehicle Theft", "Crimes Against Property", "A"),
    ("200", "Arson", "Crimes Against Property", "A"),
    ("250", "Counterfeiting/Forgery", "Crimes Against Property", "A"),
    ("26A", "False Pretenses/Swindle/Confidence Game (Fraud)", "Crimes Against Property", "A"),
    # Crimes Against Society
    ("35A", "Drug/Narcotic Violations", "Crimes Against Society", "A"),
    ("35B", "Drug Equipment Violations", "Crimes Against Society", "A"),
    ("39A", "Betting/Wagering (Gambling)", "Crimes Against Society", "A"),
    ("520", "Weapon Law Violations", "Crimes Against Society", "A"),
    ("40A", "Prostitution", "Crimes Against Society", "A"),
    ("90D", "Driving Under the Influence", "Crimes Against Society", "B"),
    ("90C", "Disorderly Conduct", "Crimes Against Society", "B"),
]

DIVISIONS = [
    "Texas Rangers",
    "Texas Highway Patrol",
    "Criminal Investigations Division",
    "CID — Narcotics",
    "Intelligence & Counterterrorism Division",
    "Crime Laboratory Division",
]

STATUSES = ["Reported", "Under Investigation", "Cleared by Arrest", "Exceptionally Cleared", "Closed"]

# County -> primary city, used to keep synthetic locations plausible.
COUNTIES = {
    "Travis": "Austin",
    "Harris": "Houston",
    "Dallas": "Dallas",
    "Bexar": "San Antonio",
    "Tarrant": "Fort Worth",
    "El Paso": "El Paso",
    "Hidalgo": "McAllen",
    "Webb": "Laredo",
    "Cameron": "Brownsville",
    "Nueces": "Corpus Christi",
    "Lubbock": "Lubbock",
    "Bell": "Killeen",
    "Midland": "Midland",
    "Potter": "Amarillo",
}

ARREST_TYPES = ["On-View Arrest", "Summoned/Cited", "Taken Into Custody"]

FIRST_NAMES = ["James", "Maria", "Robert", "Ashley", "Michael", "Jessica", "David", "Ana",
               "Carlos", "Linda", "Juan", "Sarah", "Kevin", "Diana", "Brandon", "Patricia"]
LAST_NAMES = ["Garcia", "Smith", "Johnson", "Martinez", "Williams", "Rodriguez", "Brown",
              "Davis", "Hernandez", "Lopez", "Wilson", "Anderson", "Flores", "Nguyen"]
SEXES = ["M", "F"]
RACES = ["W", "B", "A", "I", "U"]
OFFENDER_STATUSES = ["At Large", "In Custody", "Charged", "Released"]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the schema and seed synthetic data if the DB does not yet exist."""
    fresh = not os.path.exists(DB_PATH)
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    if fresh:
        seed(conn)
    conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS offenses (
    code        TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    category    TEXT NOT NULL,
    grp         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_number TEXT UNIQUE NOT NULL,
    offense_code   TEXT NOT NULL REFERENCES offenses(code),
    status         TEXT NOT NULL,
    reported_date  TEXT NOT NULL,
    occurred_date  TEXT NOT NULL,
    county         TEXT NOT NULL,
    city           TEXT NOT NULL,
    agency         TEXT NOT NULL,
    division       TEXT NOT NULL,
    narrative      TEXT
);

CREATE TABLE IF NOT EXISTS offenders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    dob         TEXT,
    sex         TEXT,
    race        TEXT,
    sid         TEXT,
    status      TEXT
);

CREATE TABLE IF NOT EXISTS arrests (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id      INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    offender_id      INTEGER NOT NULL REFERENCES offenders(id) ON DELETE CASCADE,
    arrest_date      TEXT NOT NULL,
    arrest_type      TEXT NOT NULL,
    arresting_agency TEXT NOT NULL
);
"""


def _rand_date(start_days_ago, end_days_ago=0):
    delta = random.randint(end_days_ago, start_days_ago)
    return (dt.date.today() - dt.timedelta(days=delta)).isoformat()


def seed(conn):
    random.seed(1935)  # DPS founded 1935 — deterministic demo data
    conn.executemany(
        "INSERT INTO offenses(code, description, category, grp) VALUES (?,?,?,?)",
        OFFENSES,
    )

    codes = [o[0] for o in OFFENSES]
    counties = list(COUNTIES.items())
    for i in range(1, 41):
        code = random.choice(codes)
        county, city = random.choice(counties)
        division = random.choice(DIVISIONS)
        status = random.choice(STATUSES)
        occurred = _rand_date(540, 10)
        reported = occurred  # reported on or just after occurrence
        year = occurred[:4]
        incident_number = f"TX-{year}-{i:05d}"
        agency = f"DPS {county} County District Office"
        narrative = (
            f"Synthetic demo incident reported in {city}, {county} County. "
            f"Assigned to {division} for handling."
        )
        cur = conn.execute(
            """INSERT INTO incidents
               (incident_number, offense_code, status, reported_date, occurred_date,
                county, city, agency, division, narrative)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (incident_number, code, status, reported, occurred, county, city,
             agency, division, narrative),
        )
        incident_id = cur.lastrowid

        for _ in range(random.randint(1, 3)):
            off_status = random.choice(OFFENDER_STATUSES)
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            dob = _rand_date(365 * 55, 365 * 18)
            sid = f"TX{random.randint(1000000, 9999999)}"
            ocur = conn.execute(
                """INSERT INTO offenders
                   (incident_id, first_name, last_name, dob, sex, race, sid, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (incident_id, fn, ln, dob, random.choice(SEXES),
                 random.choice(RACES), sid, off_status),
            )
            offender_id = ocur.lastrowid
            if status in ("Cleared by Arrest",) or off_status in ("In Custody", "Charged"):
                conn.execute(
                    """INSERT INTO arrests
                       (incident_id, offender_id, arrest_date, arrest_type, arresting_agency)
                       VALUES (?,?,?,?,?)""",
                    (incident_id, offender_id, _rand_date(500, 5),
                     random.choice(ARREST_TYPES), agency),
                )
    conn.commit()


# --------------------------------------------------------------------------
# Query helpers
# --------------------------------------------------------------------------
def reference_data(conn):
    offenses = [dict(r) for r in conn.execute(
        "SELECT code, description, category, grp FROM offenses ORDER BY category, code")]
    return {
        "offenses": offenses,
        "divisions": DIVISIONS,
        "statuses": STATUSES,
        "counties": [{"county": c, "city": city} for c, city in COUNTIES.items()],
    }


def stats(conn):
    def group(sql):
        return {r[0]: r[1] for r in conn.execute(sql)}

    total = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    open_count = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE status IN ('Reported','Under Investigation')"
    ).fetchone()[0]
    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "total_offenders": conn.execute("SELECT COUNT(*) FROM offenders").fetchone()[0],
        "total_arrests": conn.execute("SELECT COUNT(*) FROM arrests").fetchone()[0],
        "by_category": group(
            """SELECT o.category, COUNT(*) FROM incidents i
               JOIN offenses o ON o.code = i.offense_code
               GROUP BY o.category ORDER BY o.category"""),
        "by_status": group("SELECT status, COUNT(*) FROM incidents GROUP BY status"),
        "by_division": group(
            "SELECT division, COUNT(*) FROM incidents GROUP BY division ORDER BY division"),
    }


def list_incidents(conn, filters):
    sql = [
        """SELECT i.id, i.incident_number, i.offense_code, o.description AS offense,
                  o.category, o.grp, i.status, i.reported_date, i.occurred_date,
                  i.county, i.city, i.division
           FROM incidents i JOIN offenses o ON o.code = i.offense_code WHERE 1=1"""
    ]
    params = []
    if filters.get("category"):
        sql.append("AND o.category = ?"); params.append(filters["category"])
    if filters.get("status"):
        sql.append("AND i.status = ?"); params.append(filters["status"])
    if filters.get("division"):
        sql.append("AND i.division = ?"); params.append(filters["division"])
    if filters.get("county"):
        sql.append("AND i.county = ?"); params.append(filters["county"])
    if filters.get("q"):
        like = f"%{filters['q']}%"
        sql.append("AND (i.incident_number LIKE ? OR o.description LIKE ? OR i.city LIKE ?)")
        params += [like, like, like]
    sql.append("ORDER BY i.reported_date DESC, i.id DESC")
    return [dict(r) for r in conn.execute(" ".join(sql), params)]


def get_incident(conn, incident_id):
    row = conn.execute(
        """SELECT i.*, o.description AS offense, o.category, o.grp
           FROM incidents i JOIN offenses o ON o.code = i.offense_code
           WHERE i.id = ?""", (incident_id,)).fetchone()
    if not row:
        return None
    incident = dict(row)
    incident["offenders"] = [dict(r) for r in conn.execute(
        "SELECT * FROM offenders WHERE incident_id = ? ORDER BY id", (incident_id,))]
    incident["arrests"] = [dict(r) for r in conn.execute(
        "SELECT * FROM arrests WHERE incident_id = ? ORDER BY arrest_date", (incident_id,))]
    return incident


def create_incident(conn, data):
    required = ["offense_code", "county", "division", "occurred_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    off = conn.execute("SELECT code FROM offenses WHERE code = ?",
                       (data["offense_code"],)).fetchone()
    if not off:
        raise ValueError(f"Unknown offense code: {data['offense_code']}")

    county = data["county"]
    city = data.get("city") or COUNTIES.get(county, "Unknown")
    status = data.get("status") or "Reported"
    reported = data.get("reported_date") or dt.date.today().isoformat()
    year = data["occurred_date"][:4]
    seq = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] + 1
    incident_number = f"TX-{year}-{seq:05d}"
    agency = data.get("agency") or f"DPS {county} County District Office"

    cur = conn.execute(
        """INSERT INTO incidents
           (incident_number, offense_code, status, reported_date, occurred_date,
            county, city, agency, division, narrative)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (incident_number, data["offense_code"], status, reported, data["occurred_date"],
         county, city, agency, data["division"], data.get("narrative", "")),
    )
    conn.commit()
    return get_incident(conn, cur.lastrowid)


# --------------------------------------------------------------------------
# HTTP handler
# --------------------------------------------------------------------------
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "CATS-Demo/1.0"

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        if not os.path.isfile(path):
            self.send_error(404, "Not found")
            return
        ext = os.path.splitext(path)[1]
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            return self._handle_api_get(path, parse_qs(parsed.query))
        if path == "/" or path == "":
            return self._send_file(os.path.join(STATIC_DIR, "index.html"))
        # Prevent path traversal; serve only from STATIC_DIR.
        safe = os.path.normpath(path).lstrip("/")
        return self._send_file(os.path.join(STATIC_DIR, safe))

    def _handle_api_get(self, path, query):
        conn = connect()
        try:
            if path == "/api/stats":
                return self._send_json(stats(conn))
            if path == "/api/reference":
                return self._send_json(reference_data(conn))
            if path == "/api/incidents":
                filters = {k: v[0] for k, v in query.items()}
                return self._send_json(list_incidents(conn, filters))
            if path.startswith("/api/incidents/"):
                try:
                    incident_id = int(path.rsplit("/", 1)[1])
                except ValueError:
                    return self._send_json({"error": "invalid id"}, 400)
                incident = get_incident(conn, incident_id)
                if incident is None:
                    return self._send_json({"error": "not found"}, 404)
                return self._send_json(incident)
            return self._send_json({"error": "unknown endpoint"}, 404)
        finally:
            conn.close()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/incidents":
            return self._send_json({"error": "unknown endpoint"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send_json({"error": "invalid JSON"}, 400)
        conn = connect()
        try:
            incident = create_incident(conn, data)
            return self._send_json(incident, 201)
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, 400)
        finally:
            conn.close()

    def log_message(self, fmt, *args):  # keep demo console tidy
        return


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"CATS demo running at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
