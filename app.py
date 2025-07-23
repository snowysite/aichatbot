import os, sqlite3, smtplib, ssl, random, time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

# ✅ Load environment vars
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Flask config
app = Flask(__name__)
app.secret_key = "supersecretkey"
app.permanent_session_lifetime = timedelta(days=7)
DB_FILE = "chatbot.db"

# ✅ OpenAI client (only used if key is available)
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# ✅ Email config
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
    c.execute('''CREATE TABLE IF NOT EXISTS auth_users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        role TEXT,
        content TEXT,
        timestamp TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS otp_codes(
        username TEXT,
        otp TEXT,
        expires INTEGER
    )''')
    # ✅ knowledge base for learning offline
    c.execute('''CREATE TABLE IF NOT EXISTS learned_knowledge(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ✅ --- EMAIL ---
def send_otp_email(to_email, username, otp):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your OTP Reset Code"
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    html = f"""
    <html><body>
    <h2>🔐 Password Reset</h2>
    <p>Hello <b>{username}</b>,</p>
    <p>Your OTP code is: <b>{otp}</b></p>
    <p>It expires in 10 minutes.</p>
    </body></html>
    """
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())

# ✅ USER MANAGEMENT
def create_user(username, email, password):
    conn = get_db()
    c = conn.cursor()
    hashed = generate_password_hash(password)
    try:
        c.execute("INSERT INTO auth_users (username, email, password) VALUES (?,?,?)",(username,email,hashed))
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
    return user

# ✅ OTP MGMT
def create_otp(username,email):
    otp=str(random.randint(100000,999999))
    expires=int(time.time())+600
    conn=get_db()
    c=conn.cursor()
    c.execute("DELETE FROM otp_codes WHERE username=?",(username,))
    c.execute("INSERT INTO otp_codes(username,otp,expires) VALUES(?,?,?)",(username,otp,expires))
    conn.commit();conn.close()
    send_otp_email(email,username,otp)

def verify_otp(username,otp_input):
    conn=get_db();c=conn.cursor()
    c.execute("SELECT otp,expires FROM otp_codes WHERE username=?",(username,))
    data=c.fetchone();conn.close()
    if not data:return False,"No OTP found"
    otp,exp=data
    if time.time()>exp:return False,"Expired"
    if otp!=otp_input:return False,"Invalid OTP"
    return True,"OK"

def reset_password(username,new_password):
    conn=get_db();c=conn.cursor()
    hashed=generate_password_hash(new_password)
    c.execute("UPDATE auth_users SET password=? WHERE username=?",(hashed,username))
    conn.commit();conn.close()

# ✅ CHAT SAVE/LOAD
def save_chat(username,role,content):
    conn=get_db();c=conn.cursor()
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chat_history(username,role,content,timestamp) VALUES(?,?,?,?)",
              (username,role,content,ts))
    conn.commit();conn.close()

def get_chat_history(username):
    conn=get_db();c=conn.cursor()
    c.execute("SELECT role,content,timestamp FROM chat_history WHERE username=? ORDER BY id ASC",(username,))
    chats=c.fetchall();conn.close()
    return chats

# ✅ LEARNING MODE (Offline memory)
def find_learned_answer(question):
    conn=get_db();c=conn.cursor()
    c.execute("SELECT answer FROM learned_knowledge WHERE question LIKE ?",("%"+question+"%",))
    ans=c.fetchone();conn.close()
    return ans[0] if ans else None

def learn_answer(question,answer):
    conn=get_db();c=conn.cursor()
    c.execute("INSERT INTO learned_knowledge(question,answer) VALUES(?,?)",(question.lower(),answer))
    conn.commit();conn.close()

# ✅ SMART OFFLINE RESPONSE
base_knowledge={
    "hello":"Hey there! How can I help?",
    "hi":"Hello! 😊",
    "how are you":"I’m doing great!",
    "your name":"I’m Nexora, your chatbot assistant!",
    "bye":"Goodbye! See you soon."
}

def smart_offline_reply(message):
    msg=message.lower()
    # check learned memory
    learned=find_learned_answer(msg)
    if learned:return learned
    # check base knowledge
    for k,v in base_knowledge.items():
        if k in msg:return v
    # fallback: ask user to teach
    return "Hmm, I don’t know that yet. Want to teach me? Reply like: teach:answer"

# ✅ GPT RESPONSE
def gpt_response(username,message):
    conn=get_db();c=conn.cursor()
    c.execute("SELECT role,content FROM chat_history WHERE username=? ORDER BY id DESC LIMIT 5",(username,))
    hist=c.fetchall();conn.close()
    msgs=[{"role":"system","content":"You are a friendly chatbot."}]
    for role,content in reversed(hist):
        msgs.append({"role":role,"content":content})
    msgs.append({"role":"user","content":message})
    res=client.chat.completions.create(model="gpt-3.5-turbo",messages=msgs)
    return res.choices[0].message.content.strip()

# ✅ MAIN BOT LOGIC
def chatbot_reply(username,message):
    save_chat(username,"user",message)
    msg=message.lower()

    # handle learning mode
    if msg.startswith("teach:"):
        new_answer=message.split("teach:",1)[1].strip()
        prev_q=get_last_user_question(username)
        if prev_q:
            learn_answer(prev_q,new_answer)
            reply="Got it! I’ll remember that for next time."
        else:
            reply="I don’t know what to link this answer to 🤔"
        save_chat(username,"bot",reply)
        return reply

    # jokes/facts quick
    if "joke" in msg:
        reply=random.choice([
            "Why don’t skeletons fight? They don’t have the guts!",
            "Why was the math book sad? Too many problems!"
        ])
    elif "fact" in msg:
        reply=random.choice([
            "Did you know? Octopuses have 3 hearts!",
            "Bananas are berries but strawberries aren’t."
        ])
    else:
        # Try GPT if available
        if client:
            try:
                reply=gpt_response(username,message)
            except: reply=smart_offline_reply(message)
        else:
            reply=smart_offline_reply(message)

    save_chat(username,"bot",reply)
    return reply

def get_last_user_question(username):
    conn=get_db();c=conn.cursor()
    c.execute("SELECT content FROM chat_history WHERE username=? AND role='user' ORDER BY id DESC LIMIT 1",(username,))
    q=c.fetchone();conn.close()
    return q[0] if q else None

def chatbot_reply(username, message):
    """Fast bot reply: learned → keyword → GPT (fallback)"""
    save_chat(username, "user", message)  # still log user input
    
    msg = message.lower().strip()

    # ✅ Instant learned response
    learned = find_learned_answer(msg)
    if learned:
        save_chat(username, "bot", learned)
        return learned

    # ✅ Quick keyword replies
    for key, val in base_knowledge.items():
        if key in msg:
            save_chat(username, "bot", val)
            return val

    if "joke" in msg:
        reply = random.choice([
            "Why don’t skeletons fight? They don’t have the guts!",
            "Why was the math book sad? Too many problems!"
        ])
        save_chat(username, "bot", reply)
        return reply

    if "fact" in msg:
        reply = random.choice([
            "Did you know? Octopuses have 3 hearts!",
            "Bananas are berries but strawberries aren’t."
        ])
        save_chat(username, "bot", reply)
        return reply

    # ✅ Instant fallback when GPT is off
    if not client:
        reply = "Hmm, I’m not sure yet. Want to teach me? Reply like: teach:answer"
        save_chat(username, "bot", reply)
        return reply

    # ✅ GPT as LAST RESORT
    try:
        reply = gpt_response(username, message)
    except Exception as e:
        print("GPT slow/fail:", e)
        reply = "I’m thinking offline now. Want a joke or a fact?"
    
    save_chat(username, "bot", reply)
    return reply


# ✅ ROUTES
@app.route("/")
def home():
    if "user" not in session:return redirect(url_for("login"))
    return render_template("index.html",username=session["user"])

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["username"];pw=request.form["password"]
        user=get_user(u)
        if not user:return render_template("login.html",error="User not found!")
        _,uname,email,hashed=user
        if check_password_hash(hashed,pw):
            session["user"]=u
            return redirect(url_for("home"))
        return render_template("login.html",error="Wrong password!")
    return render_template("login.html")

@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        u=request.form["username"];e=request.form["email"];pw=request.form["password"]
        if not create_user(u,e,pw):return render_template("signup.html",error="Username exists!")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear();return redirect(url_for("login"))

@app.route("/forgot",methods=["GET","POST"])
def forgot_password():
    if request.method=="POST":
        u=request.form["username"];e=request.form["email"]
        user=get_user(u)
        if user and user[2]==e:
            create_otp(u,e);session["reset_user"]=u
            return redirect(url_for("verify_otp_page"))
        return render_template("forgot.html",error="Invalid details")
    return render_template("forgot.html")

@app.route("/verify-otp",methods=["GET","POST"])
def verify_otp_page():
    if "reset_user" not in session:return redirect(url_for("forgot_password"))
    u=session["reset_user"]
    if request.method=="POST":
        ok,msg=verify_otp(u,request.form["otp"])
        if ok:return redirect(url_for("reset_password_page"))
        return render_template("verify_otp.html",error=msg)
    return render_template("verify_otp.html")

@app.route("/reset-password",methods=["GET","POST"])
def reset_password_page():
    if "reset_user" not in session:return redirect(url_for("forgot_password"))
    u=session["reset_user"]
    if request.method=="POST":
        reset_password(u,request.form["new_password"])
        session.pop("reset_user",None)
        return redirect(url_for("login"))
    return render_template("reset_password.html")

@app.route("/chat",methods=["POST"])
def chat():
    if "user" not in session:return jsonify({"reply":"Session expired"})
    m=request.json["message"]
    r=chatbot_reply(session["user"],m)
    return jsonify({"reply":r})

@app.route("/history")
def history():
    if "user" not in session:return redirect(url_for("login"))
    chats=get_chat_history(session["user"])
    return render_template("history.html",username=session["user"],chats=chats)

@app.route("/clear_history",methods=["POST"])
def clear_history():
    if "user" not in session:return redirect(url_for("login"))
    conn=get_db();c=conn.cursor()
    c.execute("DELETE FROM chat_history WHERE username=?",(session["user"],))
    conn.commit();conn.close()
    return redirect(url_for("history"))

if __name__=="__main__":
    app.run(debug=True)
