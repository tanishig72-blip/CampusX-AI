from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3, os, re
from datetime import datetime

app = Flask(__name__)
app.secret_key = "campusx-demo-secret"
DB = "campusx.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'student',
        attendance INTEGER DEFAULT 82, gpa REAL DEFAULT 8.4
    );
    CREATE TABLE IF NOT EXISTS grievances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, text TEXT, category TEXT, department TEXT,
        priority TEXT, status TEXT DEFAULT 'Pending', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, skill TEXT, level TEXT, evidence TEXT
    );
    CREATE TABLE IF NOT EXISTS lost_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, title TEXT, description TEXT, location TEXT,
        item_type TEXT, status TEXT DEFAULT 'Lost', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, author TEXT, category TEXT, available INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT, time TEXT, subject TEXT, room TEXT, faculty TEXT
    );
    """)
    # Seed demo users
    try:
        cur.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?,?)",
                    ("Demo Student","student@campusx.ai","1234","student"))
    except sqlite3.IntegrityError:
        pass
    try:
        cur.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?,?)",
                    ("Campus Admin","admin@campusx.ai","admin123","admin"))
    except sqlite3.IntegrityError:
        pass

    if cur.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        cur.executemany("INSERT INTO books(title,author,category,available) VALUES(?,?,?,?)", [
            ("Artificial Intelligence: A Modern Approach","Russell & Norvig","AI",1),
            ("Hands-On Machine Learning","Aurélien Géron","Machine Learning",1),
            ("Python Crash Course","Eric Matthes","Programming",1),
            ("Computer Networks","Andrew S. Tanenbaum","Networking",0),
            ("Database System Concepts","Korth","DBMS",1),
            ("Deep Learning","Goodfellow, Bengio & Courville","AI",1),
        ])
    if cur.execute("SELECT COUNT(*) FROM timetable").fetchone()[0] == 0:
        cur.executemany("INSERT INTO timetable(day,time,subject,room,faculty) VALUES(?,?,?,?,?)", [
            ("Monday","09:00 - 10:00","Artificial Intelligence","Room 201","Dr. Sharma"),
            ("Monday","10:15 - 11:15","DBMS","Room 204","Prof. Mehta"),
            ("Monday","12:00 - 13:00","Operating Systems","Lab 2","Dr. Khan"),
            ("Tuesday","09:00 - 10:00","Computer Networks","Room 203","Prof. Rao"),
            ("Tuesday","10:15 - 11:15","Python","Lab 1","Ms. Singh"),
            ("Wednesday","11:00 - 12:00","Machine Learning","Room 202","Dr. Sharma"),
            ("Thursday","10:15 - 11:15","Web Development","Lab 3","Mr. Verma"),
            ("Friday","09:00 - 10:00","Project Lab","Lab 4","Dr. Khan"),
        ])
    conn.commit()
    conn.close()

def classify_grievance(text):
    t = text.lower()
    rules = [
        (["projector","computer","wifi","internet","software","network"],"IT / Technology","IT Cell","Medium"),
        (["ac","fan","light","electricity","water","toilet","bench","classroom","chair"],"Infrastructure","Maintenance","High"),
        (["library","book","issue","librarian"],"Library","Library Department","Low"),
        (["teacher","faculty","class","lecture","attendance","marks","exam"],"Academic","Academic Office","Medium"),
        (["security","harassment","unsafe","emergency","fight"],"Safety","Security Office","High"),
    ]
    for words, cat, dept, pri in rules:
        if any(w in t for w in words):
            return cat, dept, pri
    return "General", "Student Affairs", "Medium"

def assistant_answer(q):
    t=q.lower()
    if "attendance" in t:
        return "Your demo attendance is 82%. Keep each subject above the university's required threshold."
    if "library" in t or "book" in t:
        return "The Smart Library has 6 demo books. Try searching for AI, Python, DBMS, networking, or machine learning."
    if "timetable" in t or "class" in t:
        return "Your next demo classes are shown under Smart Timetable. You can filter the timetable by day."
    if "grievance" in t or "complaint" in t:
        return "Use AI Grievance to submit a complaint. CampusX automatically classifies it, assigns a department and priority."
    if "skill" in t or "portfolio" in t:
        return "Open Skill Passport to add projects, certifications and skills. Your profile can be shared as a digital portfolio."
    if "lost" in t or "found" in t:
        return "Open Lost & Found to report an item. The system can suggest matches using keywords from the item description."
    return "I can help with attendance, timetable, library, grievances, skills, or lost & found. Try asking: 'Show my attendance'."

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    email=request.form.get("email","").strip()
    password=request.form.get("password","")
    conn=get_db()
    user=conn.execute("SELECT * FROM users WHERE email=? AND password=?",(email,password)).fetchone()
    conn.close()
    if user:
        session["user_id"]=user["id"]; session["role"]=user["role"]
        return redirect(url_for("dashboard"))
    flash("Invalid login. Try student@campusx.ai / 1234 or admin@campusx.ai / admin123")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

def current_user():
    if "user_id" not in session: return None
    conn=get_db()
    u=conn.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
    conn.close()
    return u

@app.route("/dashboard")
def dashboard():
    u=current_user()
    if not u: return redirect(url_for("home"))
    conn=get_db()
    grievances=conn.execute("SELECT * FROM grievances WHERE user_id=? ORDER BY id DESC LIMIT 5",(u["id"],)).fetchall()
    skills=conn.execute("SELECT * FROM skills WHERE user_id=?",(u["id"],)).fetchall()
    lost=conn.execute("SELECT * FROM lost_items WHERE user_id=? ORDER BY id DESC LIMIT 5",(u["id"],)).fetchall()
    counts={
        "grievances":conn.execute("SELECT COUNT(*) FROM grievances").fetchone()[0],
        "pending":conn.execute("SELECT COUNT(*) FROM grievances WHERE status!='Resolved'").fetchone()[0],
        "books":conn.execute("SELECT COUNT(*) FROM books WHERE available=1").fetchone()[0],
        "lost":conn.execute("SELECT COUNT(*) FROM lost_items WHERE status='Lost'").fetchone()[0],
    }
    conn.close()
    return render_template("dashboard.html",user=u,grievances=grievances,skills=skills,lost=lost,counts=counts)

@app.route("/grievances", methods=["GET","POST"])
def grievances():
    u=current_user()
    if not u: return redirect(url_for("home"))
    if request.method=="POST":
        text=request.form.get("text","").strip()
        cat,dept,pri=classify_grievance(text)
        conn=get_db()
        conn.execute("INSERT INTO grievances(user_id,text,category,department,priority,created_at) VALUES(?,?,?,?,?,?)",
                     (u["id"],text,cat,dept,pri,datetime.now().strftime("%d %b %Y %H:%M")))
        conn.commit(); conn.close()
        flash(f"AI classified your grievance as {cat} → {dept} ({pri} priority).")
        return redirect(url_for("grievances"))
    conn=get_db()
    rows=conn.execute("SELECT g.*,u.name FROM grievances g JOIN users u ON u.id=g.user_id ORDER BY g.id DESC").fetchall()
    conn.close()
    return render_template("grievances.html",rows=rows,user=u)

@app.route("/grievances/<int:gid>/resolve", methods=["POST"])
def resolve(gid):
    if session.get("role")!="admin": return redirect(url_for("grievances"))
    conn=get_db(); conn.execute("UPDATE grievances SET status='Resolved' WHERE id=?",(gid,)); conn.commit(); conn.close()
    return redirect(url_for("grievances"))

@app.route("/timetable")
def timetable():
    u=current_user()
    if not u: return redirect(url_for("home"))
    conn=get_db()
    rows=conn.execute("SELECT * FROM timetable ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 ELSE 6 END,time").fetchall()
    conn.close()
    return render_template("timetable.html",rows=rows,user=u)

@app.route("/skills", methods=["GET","POST"])
def skills():
    u=current_user()
    if not u: return redirect(url_for("home"))
    if request.method=="POST":
        skill=request.form.get("skill","").strip()
        level=request.form.get("level","Intermediate")
        evidence=request.form.get("evidence","").strip()
        if skill:
            conn=get_db(); conn.execute("INSERT INTO skills(user_id,skill,level,evidence) VALUES(?,?,?,?)",(u["id"],skill,level,evidence)); conn.commit(); conn.close()
        return redirect(url_for("skills"))
    conn=get_db(); rows=conn.execute("SELECT * FROM skills WHERE user_id=?",(u["id"],)).fetchall(); conn.close()
    return render_template("skills.html",rows=rows,user=u)

@app.route("/library")
def library():
    u=current_user()
    if not u: return redirect(url_for("home"))
    q=request.args.get("q","").strip()
    conn=get_db()
    if q:
        rows=conn.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR category LIKE ?",(f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    else: rows=conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return render_template("library.html",rows=rows,user=u,q=q)

@app.route("/library/<int:bid>/toggle", methods=["POST"])
def toggle_book(bid):
    conn=get_db()
    row=conn.execute("SELECT available FROM books WHERE id=?",(bid,)).fetchone()
    if row:
        conn.execute("UPDATE books SET available=? WHERE id=?",(0 if row["available"] else 1,bid)); conn.commit()
    conn.close()
    return redirect(url_for("library"))

@app.route("/lost-found", methods=["GET","POST"])
def lost_found():
    u=current_user()
    if not u: return redirect(url_for("home"))
    if request.method=="POST":
        title=request.form.get("title","").strip()
        desc=request.form.get("description","").strip()
        loc=request.form.get("location","").strip()
        typ=request.form.get("item_type","Other")
        conn=get_db()
        conn.execute("INSERT INTO lost_items(user_id,title,description,location,item_type,created_at) VALUES(?,?,?,?,?,?)",
                     (u["id"],title,desc,loc,typ,datetime.now().strftime("%d %b %Y %H:%M")))
        conn.commit(); conn.close()
        flash("Item reported. CampusX will look for matching descriptions.")
        return redirect(url_for("lost_found"))
    conn=get_db()
    rows=conn.execute("SELECT l.*,u.name FROM lost_items l JOIN users u ON u.id=l.user_id ORDER BY l.id DESC").fetchall()
    conn.close()
    # simple keyword match suggestions
    matches=[]
    for a in rows:
        for b in rows:
            if a["id"]>=b["id"] or a["status"]==b["status"]: continue
            words=set(re.findall(r"[a-zA-Z]{4,}",(a["title"]+" "+a["description"]).lower()))
            words2=set(re.findall(r"[a-zA-Z]{4,}",(b["title"]+" "+b["description"]).lower()))
            overlap=words & words2
            if overlap:
                matches.append((a["id"],b["id"],", ".join(list(overlap)[:5])))
    return render_template("lost_found.html",rows=rows,matches=matches,user=u)

@app.route("/api/assistant", methods=["POST"])
def api_assistant():
    q=request.json.get("message","")
    return jsonify({"answer":assistant_answer(q)})

@app.route("/admin")
def admin():
    if session.get("role")!="admin": return redirect(url_for("dashboard"))
    conn=get_db()
    stats=[
        ("Students",conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]),
        ("Grievances",conn.execute("SELECT COUNT(*) FROM grievances").fetchone()[0]),
        ("Pending",conn.execute("SELECT COUNT(*) FROM grievances WHERE status!='Resolved'").fetchone()[0]),
        ("Available Books",conn.execute("SELECT COUNT(*) FROM books WHERE available=1").fetchone()[0]),
        ("Lost Items",conn.execute("SELECT COUNT(*) FROM lost_items WHERE status='Lost'").fetchone()[0]),
    ]
    conn.close()
    return render_template("admin.html",stats=stats,user=current_user())

init_db()

if __name__=="__main__":
    app.run(debug=True)
