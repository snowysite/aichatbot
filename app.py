import os, sqlite3, smtplib, ssl, random, time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from openai import OpenAI  # ✅ new SDK

from dotenv import load_dotenv
import os

# ✅ Load .env file
load_dotenv()

# ✅ Get the key from environment
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

from openai import OpenAI
client = OpenAI(api_key=OPENAI_KEY)


# ✅ CONFIG
app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_FILE = "chatbot.db"

# ✅ OpenAI new SDK client
client = OpenAI()  # uses OPENAI_API_KEY from env
client = OpenAI(api_key="")


# ✅ Email (replace with real)
EMAIL_USER = "sitesnow77@gmail.com"
EMAIL_PASS = "ofwt toiz qdou cppf"

# ✅ --- DB Helper ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS auth_users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT
    )''')
    # Chat memory
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        role TEXT,
        content TEXT,
        timestamp TEXT
    )''')
    # OTP table
    c.execute('''CREATE TABLE IF NOT EXISTS otp_codes(
        username TEXT,
        otp TEXT,
        expires INTEGER
    )''')
    conn.commit()
    conn.close()

init_db()

# ✅ --- EMAIL SENDER ---
def send_otp_email(to_email, username, otp):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your OTP Reset Code"
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    html = f"""
    <html>
    <body style="font-family:Arial; background:#f7f7f7; padding:20px;">
      <div style="background:#fff; padding:20px; border-radius:10px;">
        <h2>🔐 Password Reset Request</h2>
        <p>Hello <b>{username}</b>,</p>
        <p>Your OTP code is:</p>
        <h3 style="color:blue;">{otp}</h3>
        <p>It will expire in <b>10 minutes</b>.</p>
        <p>If you didn’t request this, ignore this email.</p>
        <hr>
        <p>🤖 Chatbot Team</p>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())

# ✅ --- USER MANAGEMENT ---
def create_user(username, email, password):
    conn = get_db()
    c = conn.cursor()
    hashed = generate_password_hash(password)
    try:
        c.execute("INSERT INTO auth_users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, hashed))
        conn.commit()
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
    return True

def get_user(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, email, password FROM auth_users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user  # Either None or 4-tuple

# ✅ --- OTP MANAGEMENT ---
def create_otp(username, email):
    otp = str(random.randint(100000, 999999))
    expires = int(time.time()) + 600  # 10 min expiry
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM otp_codes WHERE username=?", (username,))
    c.execute("INSERT INTO otp_codes(username, otp, expires) VALUES(?,?,?)", (username, otp, expires))
    conn.commit()
    conn.close()
    send_otp_email(email, username, otp)

def verify_otp(username, otp_input):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT otp, expires FROM otp_codes WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    if not data:
        return False, "No OTP found. Request again."
    otp, expires = data
    now = int(time.time())
    if now > expires:
        return False, "OTP expired. Please resend."
    if otp != otp_input:
        return False, "Invalid OTP."
    return True, "OK"

def reset_password(username, new_password):
    conn = get_db()
    c = conn.cursor()
    hashed = generate_password_hash(new_password)
    c.execute("UPDATE auth_users SET password=? WHERE username=?", (hashed, username))
    conn.commit()
    conn.close()

# ✅ --- CHATBOT LOGIC ---
def chatbot_reply(username, message):
    jokes = [
        "Why don’t skeletons fight each other? They don’t have the guts!",
        "I told my computer I needed a break… it said 'No problem, I’ll go to sleep.'",
    ]
    fun_facts = [
        "Honey never spoils. Archaeologists have eaten 3000-year-old honey!",
        "Bananas are berries, but strawberries are not.",
        "Did you know? Octopuses have three hearts!"
    ]

    save_chat(username, "user", message)
    low = message.lower()

    # Offline quick replies
    if "joke" in low:
        reply = random.choice(jokes)
    elif "fact" in low:
        reply = random.choice(fun_facts)
    elif "hello" in low or "hi" in low:
        reply = f"Hello {username}! I’m here to help. Want a joke or a fun fact?"
    else:
        # ✅ Try GPT first
        try:
            reply = gpt_response(username, message)
        except Exception as e:
            print("GPT Error:", e)
            reply = "I’m in offline mode (no GPT). Ask me for a joke or a fun fact! 🤖"

    save_chat(username, "bot", reply)
    return reply



def gpt_response(username, message):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE username=? ORDER BY id DESC LIMIT 5", (username,))
    history = c.fetchall()
    conn.close()

    messages = [{"role": "system", "content": "You are a friendly chatbot."}]
    for role, content in reversed(history):
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("GPT Error:", e)
        return "Hmm, I’m having trouble thinking right now."

def save_chat(username, role, content):
    conn = get_db()
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chat_history(username, role, content, timestamp) VALUES (?,?,?,?)",
              (username, role, content, timestamp))
    conn.commit()
    conn.close()

def get_chat_history(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM chat_history WHERE username=? ORDER BY id ASC", (username,))
    chats = c.fetchall()
    conn.close()
    return chats

# ✅ --- ROUTES ---
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", username=session["user"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_user(username)

        if not user:
            return render_template("login.html", error="User not found!")
        
        _, uname, email, hashed_pw = user
        if check_password_hash(hashed_pw, password):
            session["user"] = username
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Wrong password!")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        if not create_user(username, email, password):
            return render_template("signup.html", error="Username already exists!")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        user = get_user(username)
        if user and user[2] == email:
            create_otp(username, email)
            session["reset_user"] = username
            return redirect(url_for("verify_otp_page"))
        else:
            return render_template("forgot.html", error="Invalid username/email")
    return render_template("forgot.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp_page():
    if "reset_user" not in session:
        return redirect(url_for("forgot_password"))
    username = session["reset_user"]

    if request.method == "POST":
        otp_input = request.form["otp"]
        ok, msg = verify_otp(username, otp_input)
        if ok:
            return redirect(url_for("reset_password_page"))
        else:
            return render_template("verify_otp.html", error=msg)
    return render_template("verify_otp.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password_page():
    if "reset_user" not in session:
        return redirect(url_for("forgot_password"))
    username = session["reset_user"]

    if request.method == "POST":
        new_password = request.form["new_password"]
        reset_password(username, new_password)
        session.pop("reset_user", None)
        return redirect(url_for("login"))
    return render_template("reset_password.html")

@app.route("/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"reply": "Session expired, please log in."})
    message = request.json["message"]
    reply = chatbot_reply(session["user"], message)
    return jsonify({"reply": reply})

@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))
    chats = get_chat_history(session["user"])
    return render_template("history.html", chats=chats, username=session["user"])

# ✅ START
if __name__ == "__main__":
    app.run(debug=True)
