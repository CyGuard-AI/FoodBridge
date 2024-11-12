from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import requests
from datetime import datetime
import plotly.graph_objs as go
from plotly.utils import PlotlyJSONEncoder
import json
import time
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
db_config = {
    'user': 'admin',
    'password': 'StrongP@ssw0rd',
    'host': 'localhost',
    'database': 'foodbridge',
    'cursorclass': pymysql.cursors.DictCursor  # Use the DictCursor for better row handling
}

# Telegram bot configuration
TELEGRAM_BOT_TOKEN = '7991243142:AAGzuYMNNGyKxQPpwFKw330yzLq8GrzzzQE'
TELEGRAM_CHAT_ID = '-1002449780907'  # Your Telegram group chat ID

def send_telegram_message(donation):
    message = (
        f"🆕 **New Food Donation Received** 🆕\n\n"
        f"**Food Name:** {donation['food_name']}\n"
        f"**Meal Type:** {donation['meal_type']}\n"
        f"**Category:** {donation['category']}\n"
        f"**Quantity:** {donation['quantity']}\n\n"
        f"**Donor Details:**\n"
        f"Name: {donation['donor_name']}\n"
        f"Phone: {donation['phone_number']}\n"
        f"District: {donation['district']}\n"
        f"Address: {donation['address']}\n\n"
        "Please contact the donor to arrange collection!"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'})

@app.route('/')
@app.route('/home')
def home():
    username = session.get('username')
    email = session.get('email')
    return render_template('home.html', username=username, email=email)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    msg = ''
    if request.method == 'POST':
        food_name = request.form['food_name']
        meal_type = request.form['meal_type']
        category = request.form['category']
        quantity = request.form['quantity']
        donor_name = request.form['donor_name']
        phone_number = request.form['phone_number']
        district = request.form['district']
        address = request.form['address']

        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO food_donations (food_name, meal_type, category, quantity, donor_name, phone_number, district, address) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', 
            (food_name, meal_type, category, quantity, donor_name, phone_number, district, address)
        )
        conn.commit()

        cursor.execute('SELECT * FROM food_donations WHERE donor_name = %s ORDER BY created_at DESC LIMIT 1', (donor_name,))
        donation = cursor.fetchone()

        send_telegram_message(donation)
        conn.close()
        msg = 'Donation submitted successfully!'
        return render_template('fooddonate.html', msg=msg)

    return render_template('fooddonate.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
            msg = 'Password must be at least 8 characters long, contain both letters and numbers.'
            return render_template('signup.html', msg=msg)
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            conn = pymysql.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            if cursor.fetchone():
                msg = 'Email already registered. Use a different email or log in.'
            else:
                cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, hashed_password))
                conn.commit()
                msg = 'You have successfully registered! Please log in.'
                return redirect(url_for('login'))
        except pymysql.MySQLError as e:
            msg = 'An error occurred during registration. Please try again later.'
            print(f"Database error: {e}")
        finally:
            conn.close() if 'conn' in locals() else None

    return render_template('signup.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = pymysql.connect(**db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session.permanent = True
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                msg = 'Invalid email or password'
        except pymysql.MySQLError as e:
            msg = 'An error occurred during login. Please try again later.'
            print(f"Database error: {e}")
        finally:
            conn.close() if 'conn' in locals() else None

    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' in session:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()

        return render_template('profile.html', username=session['username'], email=user['email'])
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/dashboard-data')
def dashboard_data():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) AS total_donations FROM food_donations")
        total_donations = cursor.fetchone()['total_donations']

        cursor.execute("SELECT COALESCE(SUM(quantity), 0) AS total_meals FROM food_donations")
        total_meals = cursor.fetchone()['total_meals']

        cursor.execute("SELECT COUNT(DISTINCT donor_name) AS total_donors FROM food_donations")
        total_donors = cursor.fetchone()['total_donors']

        cursor.execute("SELECT COUNT(DISTINCT phone_number) AS total_people_helped FROM food_donations")
        total_people_helped = cursor.fetchone()['total_people_helped']

    finally:
        conn.close()

    data = {
        'total_donations': total_donations,
        'total_meals': total_meals,
        'total_donors': total_donors,
        'total_people_helped': total_people_helped
    }

    return jsonify(data)

# Define prompt-response pairs
prompts = [
    ["hi", "hey", "hello", "good morning", "good afternoon"],
    ["how are you", "how is life", "how are things"],
    ["what are you doing", "what is going on", "what is up"],
    ["how old are you"],
    ["who are you", "are you human", "are you bot", "are you human or bot"],
    ["who created you", "who made you"],
    ["your name please", "your name", "may i know your name", "what is your name"],
    ["i love you"],
    ["happy", "good", "fun", "wonderful", "fantastic", "cool"],
    ["bad", "bored", "tired"],
    ["help me", "tell me story", "tell me joke"],
    ["ah", "yes", "ok", "okay", "nice"],
    ["bye", "good bye", "goodbye", "see you later"],
    ["what should i eat today"],
    ["bro"],
    ["what", "why", "how", "where", "when"],
    ["no", "not sure", "maybe", "no thanks"],
    [""],
    ["haha", "ha", "lol", "hehe", "funny", "joke"],
    ["food donate", "project"],
    ["date"],
    ["time"],
    ["what can i donate", "donate"],
    ["trust in donation"]
]
responses = [
    ["Hello!", "Hi!", "Hey!", "Hi there!"],
    ["I’m doing well, thank you!", "Life is good!", "I’m great, thank you for asking!"],
    ["Just here to help you.", "Doing my thing!", "I’m here for you!"],
    ["I'm a timeless being!", "A bit ageless, actually."],
    ["I am a bot, created to assist you.", "Just your friendly assistant bot!"],
    ["I was created by a skilled developer.", "I'm a product of digital craftsmanship."],
    ["I'm called Food Bridge Assistant.", "I'm here to assist you!"],
    ["I appreciate that!"],
    ["I'm glad you're feeling good!", "That's great to hear!"],
    ["Sorry to hear that.", "Hope things get better soon."],
    ["I'm here to assist.", "Sure! What do you need?"],
    ["Indeed!", "Yes, absolutely!", "Of course!"],
    ["Goodbye!", "See you later!", "Take care!"],
    ["How about some delicious vegetarian dishes?", "Perhaps a nice warm meal?"],
    ["Bro!"],
    ["Can you clarify?"],
    ["Got it."],
    ["I'm here!"],
    ["Glad you find it funny!"],
    ["Let me know how I can assist with food donations."],
    ["Today's date is " + datetime.now().strftime("%Y-%m-%d")],
    ["The current time is " + datetime.now().strftime("%H:%M:%S")],
    ["We accept all types of food donations that are fresh and safe to eat."],
    ["Donations are secure and are for a good cause!"]
]

def chatbot_response(user_text):
    for prompt, response in zip(prompts, responses):
        if user_text.lower() in prompt:
            return response[0] if isinstance(response, list) else response
    return "I'm here to help with any queries related to food donations!"

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_text = request.json.get("message", "")
    response = chatbot_response(user_text)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
