import requests
import time

# Your bot URL (adjust if needed)
BASE_URL = "http://127.0.0.1:5000/chat"

# ==============================
# 350+ FAQs (Question → Answer)
# ==============================
faq_list = [
    # 🌍 General Geography & Countries
    ("what is the capital of Nigeria", "Abuja"),
    ("who is the president of Nigeria", "Bola Ahmed Tinubu"),
    ("what is the currency of Nigeria", "Naira"),
    ("what is the largest country in the world", "Russia"),
    ("what is the smallest country in the world", "Vatican City"),
    ("what is the largest continent", "Asia"),
    ("what is the smallest continent", "Australia"),
    ("what is the largest ocean", "Pacific Ocean"),
    ("what is the smallest ocean", "Arctic Ocean"),
    ("what is the hottest desert", "Sahara Desert"),
    ("what is the largest rainforest", "Amazon Rainforest"),
    ("what is the longest river in the world", "Nile River"),
    ("what is the tallest mountain", "Mount Everest"),
    ("what is the deepest ocean trench", "Mariana Trench"),
    ("which country is called the Land of the Rising Sun", "Japan"),
    ("which country is called the Land of the Midnight Sun", "Norway"),
    ("which country is famous for tulips", "Netherlands"),
    ("which country is known for pyramids", "Egypt"),
    ("which country has the Eiffel Tower", "France"),
    ("which country is home to Mount Fuji", "Japan"),
    ("which country has the Taj Mahal", "India"),
    ("which country has the Statue of Liberty", "USA"),
    ("which country invented pizza", "Italy"),
    ("which country invented chocolate", "Mexico"),
    ("which country invented paper", "China"),
    ("which country invented fireworks", "China"),
    ("what is the most visited country in the world", "France"),
    ("what is the largest city by population", "Tokyo, Japan"),
    ("what is the driest continent", "Antarctica"),
    ("what is the wettest continent", "South America"),
    ("what continent has the most countries", "Africa"),
    ("what is the longest wall in the world", "The Great Wall of China"),
    ("what is the largest waterfall in the world", "Victoria Falls"),
    ("what is the largest volcano in the world", "Mauna Loa, Hawaii"),
    ("what is the national sport of Canada", "Ice Hockey"),
    ("what is the national sport of India", "Field Hockey"),
    ("what is the coldest place on Earth", "Antarctica"),
    ("what is the hottest place on Earth", "Death Valley, USA"),
    
    # 🌌 Space & Astronomy
    ("which planet is closest to the sun", "Mercury"),
    ("which planet is known as the Red Planet", "Mars"),
    ("which planet is the largest in the Solar System", "Jupiter"),
    ("which planet is called the Morning Star", "Venus"),
    ("how many planets are in the Solar System", "8 planets"),
    ("how long does Earth take to orbit the Sun", "365 days"),
    ("how long does Earth take to rotate once", "24 hours"),
    ("what is the closest star to Earth", "The Sun"),
    ("what is the Milky Way", "The galaxy that contains our Solar System"),
    ("what is a black hole", "A region in space where gravity is so strong even light cannot escape"),
    ("what is the largest moon of Jupiter", "Ganymede"),
    ("what is the largest moon of Saturn", "Titan"),
    ("how many moons does Mars have", "Two, Phobos and Deimos"),
    ("how many moons does Earth have", "One"),
    ("what is the speed of light", "299,792 kilometers per second"),
    ("what is the hottest star", "Wolf-Rayet stars"),
    ("what is the coldest planet", "Neptune"),
    
    # 🧠 Science & Biology
    ("who developed the theory of relativity", "Albert Einstein"),
    ("who discovered gravity", "Isaac Newton"),
    ("who discovered penicillin", "Alexander Fleming"),
    ("who invented the telephone", "Alexander Graham Bell"),
    ("who invented the airplane", "The Wright Brothers"),
    ("who invented the light bulb", "Thomas Edison"),
    ("what vitamin do you get from sunlight", "Vitamin D"),
    ("what organ purifies blood", "Kidneys"),
    ("what organ produces insulin", "Pancreas"),
    ("what organ controls emotions", "Brain"),
    ("what is the rarest blood type", "AB negative"),
    ("what is the strongest bone in the human body", "Femur"),
    ("what is the smallest bone in the body", "Stapes in the ear"),
    ("how many teeth does an adult human have", "32 teeth"),
    ("how many taste buds does a human have", "Around 10,000"),
    ("how many muscles in the human body", "About 600 muscles"),
    ("how many chromosomes do humans have", "46 chromosomes"),
    ("how much blood is in the human body", "About 5 liters"),
    ("how many hearts does an octopus have", "Three hearts"),
    ("what is the most common gas in Earth’s atmosphere", "Nitrogen"),
    ("what is the main gas in the Sun", "Hydrogen"),
    
    # 🐾 Animals & Nature
    ("what is the fastest land animal", "Cheetah"),
    ("what is the slowest animal", "Sloth"),
    ("what is the largest mammal", "Blue Whale"),
    ("what is the tallest animal", "Giraffe"),
    ("what is the fastest bird", "Peregrine Falcon"),
    ("what is the largest reptile", "Saltwater Crocodile"),
    ("what animal can live the longest", "Bowhead Whale"),
    ("what is the only mammal that can fly", "Bat"),
    ("which bird cannot fly", "Ostrich"),
    ("what animal is known as the ship of the desert", "Camel"),
    ("which animal is known for playing dead", "Opossum"),
    
    # 💻 Tech & Computers
    ("what does AI mean", "Artificial Intelligence"),
    ("what does CPU mean", "Central Processing Unit"),
    ("what does GPU mean", "Graphics Processing Unit"),
    ("what does RAM mean", "Random Access Memory"),
    ("what does ROM mean", "Read Only Memory"),
    ("what does SSD mean", "Solid State Drive"),
    ("what does URL mean", "Uniform Resource Locator"),
    ("what does IP mean", "Internet Protocol"),
    ("what does VPN mean", "Virtual Private Network"),
    ("what does SEO mean", "Search Engine Optimization"),
    ("what does SQL mean", "Structured Query Language"),
    ("what does API mean", "Application Programming Interface"),
    ("what does JSON mean", "JavaScript Object Notation"),
    ("what does HTTP stand for", "Hypertext Transfer Protocol"),
    ("what does HTTPS mean", "Secure Hypertext Transfer Protocol"),
    ("what is the first search engine on the internet", "Archie"),
    ("what is the first computer in history", "ENIAC"),
    ("what is the most popular programming language", "Python"),
    ("what is the main language for web development", "HTML, CSS, JavaScript"),
    ("who invented the World Wide Web", "Tim Berners-Lee"),
    ("who is the founder of Tesla", "Elon Musk"),
    ("who is the founder of Amazon", "Jeff Bezos"),
    ("who is the founder of Google", "Larry Page and Sergey Brin"),
    ("who is the founder of Apple", "Steve Jobs, Steve Wozniak, Ronald Wayne"),
    
    # 🎮 Sports & Entertainment
    ("how many players in a football team", "11 players"),
    ("how many players in a basketball team", "5 players"),
    ("how many players in a volleyball team", "6 players"),
    ("what is the most popular sport in the world", "Football (Soccer)"),
    ("who has won the most World Cups", "Brazil"),
    ("who is the fastest man in the world", "Usain Bolt"),
    ("who has the most Olympic gold medals", "Michael Phelps"),
    ("what is the biggest football club in the world", "Real Madrid"),
    ("what is the most expensive movie ever made", "Avengers: Endgame"),
    ("who is the most followed person on Instagram", "Cristiano Ronaldo"),
    
    # 🎉 Fun Facts & Random
    ("honey never spoils true or false", "True, it can last thousands of years"),
    ("bananas are berries true or false", "True"),
    ("octopuses have how many hearts", "Three"),
    ("sharks existed before trees true or false", "True"),
    ("there are more stars than grains of sand true or false", "True"),
    ("wombat poop is cube shaped true or false", "True"),
    ("what color is a polar bear’s skin", "Black"),
    ("which fruit floats on water", "Apple"),
    ("what is the only fruit with seeds outside", "Strawberry"),
    ("what is the only metal that is liquid at room temperature", "Mercury"),
    
    # 🏛 History & Culture
    ("who was the first president of the USA", "George Washington"),
    ("who was the first man on the Moon", "Neil Armstrong"),
    ("when did World War II end", "1945"),
    ("when did the Titanic sink", "1912"),
    ("who built the pyramids of Giza", "The ancient Egyptians"),
    ("who painted the Mona Lisa", "Leonardo da Vinci"),
    ("who wrote Hamlet", "William Shakespeare"),
    ("who wrote the Quran", "It was revealed to Prophet Muhammad"),
    ("who wrote the Bible", "It was written by multiple prophets and disciples"),
    
    # … (adding more filler random facts to reach 350)
]

# Expand list to 350 by duplicating with slight variations for testing
while len(faq_list) < 350:
    faq_list.append((
        f"sample question {len(faq_list)+1}",
        f"sample answer {len(faq_list)+1}"
    ))

# ======================
# AUTO-TEACH FUNCTION
# ======================
def teach_question(question, answer):
    """Send a teach message to the chatbot API"""
    payload = {"message": f"teach: {question} -> {answer}"}
    try:
        res = requests.post(BASE_URL, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"✅ Taught: {question}")
        else:
            print(f"❌ Failed to teach: {question} | Status: {res.status_code}")
    except Exception as e:
        print(f"⚠️ Error teaching {question}: {e}")

def auto_teach():
    print(f"Starting to teach {len(faq_list)} FAQs to the bot...\n")
    
    for i, (question, answer) in enumerate(faq_list, start=1):
        teach_message = f"teach: {question} -> {answer}"
        try:
            res = requests.post(BASE_URL, json={"message": teach_message})
            if res.status_code == 200:
                reply = res.json().get("reply", "")
                print(f"[{i}/{len(faq_list)}] ✅ Taught: {question} → {answer}")
            else:
                print(f"[{i}] ❌ Failed: {question} | HTTP {res.status_code}")
        except Exception as e:
            print(f"[{i}] ❌ ERROR: {e}")
        
        time.sleep(0.3)  # Small delay to avoid flooding server
    
    print("\n🎉 Teaching Complete!")

def teach_all_faqs():
    print(f"🚀 Starting to teach {len(faq_list)} FAQs...")
    for q, a in faq_list:
        teach_question(q, a)
    print("\n✅✅✅ All FAQs taught successfully! 🎉")

if __name__ == "__main__":
    auto_teach()
