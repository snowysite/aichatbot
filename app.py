import os, sqlite3, random, time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from dotenv import load_dotenv
import redis 
import re

# ✅ Load env
load_dotenv()

# ✅ Database file path (must be defined BEFORE init_db)
DB_FILE = "chatbot.db"

# ✅ Init Flask + SocketIO
app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app, cors_allowed_origins="*")

# ✅ Redis cache (optional)
try:
    cache = redis.Redis(host="localhost", port=6379, db=0)
    cache.ping()  # test connection
except:
    print("⚠ Redis not running, caching disabled!")
    cache = None

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS auth_users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT,
            last_greeting_date TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_knowledge(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE,
            answer TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reset_otps(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            otp TEXT,
            created_at TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized (all tables ensured).")

# ✅ Database helpers
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

init_db()

def normalize_text(txt: str) -> str:
    """Lowercase and remove punctuation for better matching"""
    return re.sub(r"[^a-z0-9 ]+", "", txt.lower()).strip()

# ✅ Fun facts & jokes
fun_facts = [
    "Honey never spoils. Archaeologists have eaten 3000-year-old honey!",
    "Bananas are berries, but strawberries are not.",
    "Octopuses have three hearts and blue blood!",
    "Sharks existed before trees 🌊",
    "There are more stars in the universe than grains of sand on Earth.",
    "Wombat poop is cube-shaped! 🐾"
]
jokes = [
    "Why don’t skeletons fight each other? They don’t have the guts! 💀",
    "I told my computer I needed a break… it said 'No problem, I’ll go to sleep.' 🖥",
    "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾",
    "Parallel lines have so much in common… it’s a shame they’ll never meet.",
    "Why don’t programmers like nature? It has too many bugs. 🐛"
]

# ✅ Plugin System
class QuizPlugin:
    name = "QuizPlugin"
    def _init_(self):
        self.questions = {
            "What is 2 + 2?": "4",
            "Capital of France?": "paris",
            "Who wrote Hamlet?": "shakespeare"
        }
    def can_handle(self, msg):
        return "quiz" in msg.lower()
    def handle(self, username, msg):
        q, a = random.choice(list(self.questions.items()))
        return f"🎯 Quiz time! {q} (Answer: {a})"

class GuessWordPlugin:
    name = "GuessWordPlugin"
    def _init_(self):
        self.words = ["apple", "mango", "grape", "lemon"]
    def can_handle(self, msg):
        return "guess" in msg.lower()
    def handle(self, username, msg):
        word = random.choice(self.words)
        return f"🤔 Guess the word! Hint: It’s a {len(word)}-letter fruit starting with {word[0].upper()}"

PLUGINS = [QuizPlugin(), GuessWordPlugin()]

# ✅ DB helpers
# ✅ Helpers
def normalize_text(txt):
    return re.sub(r"[^a-z0-9 ]+", "", txt.lower()).strip()

def save_chat(username, role, content):
    conn = get_db()
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chat_history(username, role, content, timestamp) VALUES (?,?,?,?)",
              (username, role, content, ts))
    conn.commit()
    conn.close()

def get_knowledge_answer(question):
    norm_q = normalize_text(question)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT answer FROM bot_knowledge WHERE question=?", (norm_q,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_knowledge(question, answer):
    q = normalize_text(question)
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_knowledge(question, answer) VALUES (?,?)", (q, answer))
    conn.commit()
    conn.close()

def remember_fact(username, key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_memory(username, key, value) VALUES (?,?,?)", (username, key, value))
    conn.commit()
    conn.close()

def recall_fact(username, key):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM user_memory WHERE username=? AND key=?", (username, key))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ✅ Mini Games
def play_rps(choice):
    options = ["rock", "paper", "scissors"]
    bot_choice = random.choice(options)
    if choice == bot_choice:
        return f"I chose {bot_choice}! It’s a draw. 🤝"
    if (choice == "rock" and bot_choice == "scissors") or \
       (choice == "paper" and bot_choice == "rock") or \
       (choice == "scissors" and bot_choice == "paper"):
        return f"I chose {bot_choice}! You win! 🎉"
    return f"I chose {bot_choice}! I win! 😎"

secret_facts = [
    "The CIA once tried to use cats as spy devices (Acoustic Kitty program).",
    "The KGB had hidden cyanide capsules in fountain pens.",
    "Modern drones can identify targets using AI facial recognition.",
    "AI-controlled swarms are the future of warfare.",
    "Satellite hacking has been tested in cyber warfare drills."
]

# ✅ User management helpers
def get_user(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM auth_users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row

def create_user(username, email, password):
    conn = get_db()
    c = conn.cursor()
    hashed = generate_password_hash(password)
    try:
        c.execute("INSERT INTO auth_users(username, email, password, last_greeting_date) VALUES (?,?,?,?)",
                  (username, email, hashed, ""))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_last_greeting(username):
    today = date.today().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE auth_users SET last_greeting_date=? WHERE username=?", (today, username))
    conn.commit()
    conn.close()

def reset_password(username, new_pw):
    conn = get_db()
    c = conn.cursor()
    hashed = generate_password_hash(new_pw)
    c.execute("UPDATE auth_users SET password=? WHERE username=?", (hashed, username))
    conn.commit()
    conn.close()

# ✅ OTP helpers
def create_otp(username, email):
    otp = str(random.randint(100000, 999999))
    now = datetime.now().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO reset_otps(username, otp, created_at) VALUES (?,?,?)",
              (username, otp, now))
    conn.commit()
    conn.close()
    print(f"📩 OTP for {username} ({email}) = {otp}")  # Simulate email sending

def verify_otp(username, otp_input):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT otp, created_at FROM reset_otps WHERE username=? ORDER BY id DESC LIMIT 1", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False, "No OTP found. Request again."
    otp, created = row
    if otp_input != otp:
        return False, "Invalid OTP"
    # Optional: check time validity (e.g. 5 min)
    return True, "OTP verified"

# ✅ Core chatbot logic
def chatbot_reply(username, message):
    save_chat(username, "user", message)
    msg = message.lower()

    cache_key = f"reply:{msg}"

    # ✅ Only try cache if available
    if cache:
        cached = cache.get(cache_key)
        if cached:
            reply = cached.decode('utf-8') + " (cached)"
            save_chat(username, "bot", reply)
            return reply


    # ✅ ALWAYS respond to "what is your name" or similar
    if "your name" in msg or "who are you" in msg:
        reply = "My name is SJ 🤖"
        save_chat(username, "bot", reply)
        return reply
    # ✅ Greeting keywords
    greetings = [
        "hi", "hey", "hello", "yo", "sup", "whats up",
        "what's up", "howdy", "hola", "heyy", "hiya",
        "good morning", "good afternoon", "good evening",
        "how are you", "how r u", "how are u", "how you doing"
    ]

    # ✅ Detect greetings (loose match)
    if any(word in msg for word in greetings):
        reply = random.choice([
            f"Hey {username}! 👋 How’s your day going?",
            f"Hello {username}! 😊 What can I help you with?",
            f"Hi {username}! 👀 Want to hear a joke or a fun fact?",
            f"Hey there! 🚀 I’m here for you."
        ])
        if cache:
            cache.setex(cache_key, 3600, reply)
        save_chat(username, "bot", reply)
        return reply

    # 🆕 Help for teaching
    if "how do i teach" in msg or ("teach" in msg and "->" not in msg):
        reply = (
            "📚 To teach me something new, use this format:\n\n"
            "teach: <question> -> <answer>\n\n"
            "✅ Example:\n"
            "teach: who is the president of Nigeria -> Bola Ahmed Tinubu\n"
            "After that, if you ask who is the president of Nigeria, I’ll reply correctly!"
        )
        save_chat(username, "bot", reply)
        return reply

    # 2️⃣ Plugins
    for plugin in PLUGINS:
        if plugin.can_handle(msg):
            reply = plugin.handle(username, msg)
            if cache:
                cache.setex(cache_key, 3600, reply)
            save_chat(username, "bot", reply)
            return reply

    # 3️⃣ Learned knowledge
    known_answer = get_knowledge_answer(msg)
    if known_answer:
        reply = known_answer
        if cache:
            cache.setex(cache_key, 3600, reply)
        save_chat(username, "bot", reply)
        return reply

    # 4️⃣ Teach mode
    if msg.startswith("teach:"):
        try:
            parts = message.split("->")
            q_part = parts[0].replace("teach:", "").strip()
            a_part = parts[1].strip()
            save_knowledge(q_part, a_part)
            reply = f"✅ Learned: '{q_part}' → '{a_part}'"
        except:
            reply = "To teach me: teach: question -> answer"
        save_chat(username, "bot", reply)
        return reply

    # 5️⃣ Normal responses
    if "hello" in msg or "hi" in msg:
        reply = f"Hello {username}! 👋 Want a joke or a fun fact?"
    elif "joke" in msg:
        reply = random.choice(jokes)
    elif "fact" in msg:
        reply = random.choice(fun_facts)
    else:
        reply = "🤔 I’m not sure. You can teach me: teach: question -> answer"

    # 6️⃣ Cache & return
    if cache:
        cache.setex(cache_key, 3600, reply)
    save_chat(username, "bot", reply)
    return reply

## ---------------- ROUTES ---------------- #
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    user_data = get_user(session["user"])
    last_date = user_data[4] if user_data else ""
    today = date.today().isoformat()
    daily_greet = None
    if last_date != today:
        daily_greet = random.choice(fun_facts + jokes)
        update_last_greeting(session["user"])

    return render_template("index.html", username=session["user"], daily_greet=daily_greet)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_user(username)

        if not user:
            return render_template("login.html", error="User not found!")

        _, uname, email, hashed_pw, _ = user
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

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    chats = get_chat_history(username)
    return render_template("history.html", username=username, chats=chats)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'user' not in session:
        return redirect(url_for('login'))
    username = session['user']
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return redirect(url_for('history'))

# ✅ WebSocket handlers
@socketio.on('connect')
def ws_connect():
    print("✅ Client connected!")
    emit("bot_reply", "🤖 SJ is online ! Say hi 👋")

@socketio.on('user_message')
def ws_user_message(msg):
    print(f"📩 WS message: {msg}")
    username = session.get("user", "guest")
    reply = chatbot_reply(username, msg)
    emit('bot_reply', reply)

@socketio.on('disconnect')
def ws_disconnect():
    print("❌ Client disconnected!")

# ✅ Run server
if __name__ == "__main__":
    socketio.run(app, debug=True)