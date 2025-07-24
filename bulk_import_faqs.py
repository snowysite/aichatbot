import sqlite3, re

# ✅ Same DB path as your app
DB_FILE = "chatbot.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def normalize_text(txt):
    """Lowercase, remove punctuation for better matching."""
    txt = txt.lower().strip()
    txt = re.sub(r"[^\w\s]", "", txt)  # remove punctuation
    return txt

def save_knowledge(question, answer):
    """Normalize question before saving to DB"""
    question = normalize_text(question)
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_knowledge(question, answer) VALUES (?, ?)", (question, answer))
    conn.commit()
    conn.close()
    print(f"✅ Saved: {question} -> {answer}")

def bulk_import(filename="faq_bulk.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line.startswith("teach:"):
            try:
                parts = line.replace("teach:", "").split("->")
                question = parts[0].strip()
                answer = parts[1].strip()
                save_knowledge(question, answer)
            except IndexError:
                print(f"⚠️ Skipping malformed line: {line}")

if __name__ == "__main__":
    bulk_import("faq_bulk.txt")
    print("\n✅ All FAQs imported successfully!")
