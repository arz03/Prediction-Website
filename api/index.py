# app.py
from flask import Flask, render_template, request, redirect, url_for
import tempfile

app = Flask(__name__)

# Hardcoded password for setting the correct answer (replace with a secure method in production)
password_for_answer = "jaiyashbala"

# Set the upcoming event (e.g., what the streamer will wear)
upcoming_event = "Guess the outfit"

# Global variables for predictions, leaderboard, and correct answer
predictions_file = tempfile.NamedTemporaryFile(delete=False, mode='a+')
leaderboard_file = tempfile.NamedTemporaryFile(delete=False, mode='w+')
correct_answer = ""

@app.route('/')
def home():
    return render_template('index.html', upcoming_event=upcoming_event)

@app.route('/submit_prediction', methods=['POST'])
def submit_prediction():
    global predictions
    username = request.form.get('username')
    user_prediction = request.form.get('prediction')

    # Store user predictions in the temporary file for later reference
    predictions_file.write(f"{username}, {user_prediction}\n")
    predictions_file.seek(0)

    return render_template('index.html', upcoming_event=upcoming_event)

@app.route('/submit_answer')
def show_submit_answer():
    return render_template('submit_answer.html')

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    global correct_answer

    # Check if correct_answer is not set, i.e., predictions are still being accepted
    if not correct_answer:
        entered_password = request.form.get('password')

        if entered_password == password_for_answer:
            correct_answer = request.form.get('correct_answer')
            return render_template('submit_answer.html', upcoming_event=upcoming_event, correct_answer_submitted=True, correct_answer_set=True, password_verified=True)
        else:
            return redirect(url_for('home'))

    return redirect(url_for('home'))

@app.route('/reveal_answer')
def reveal_answer():
    global correct_answer
    global leaderboard

    # Read predictions from the temporary file and update leaderboard
    predictions = [line.strip().split(", ") for line in predictions_file]

    # Calculate leaderboard
    points = {}
    for username, user_prediction in predictions:
        if user_prediction == correct_answer:
            points[username] = points.get(username, 0) + 1

    # Update leaderboard in the temporary file
    leaderboard_file.seek(0)
    leaderboard_file.truncate()
    for username, score in sorted(points.items(), key=lambda x: x[1], reverse=True):
        leaderboard_file.write(f"{username}, {score}\n")
    
    leaderboard_file.seek(0)
    leaderboard = [line.strip().split(", ") for line in leaderboard_file]

    return render_template('revealed_answer.html', predictions=predictions, upcoming_event=upcoming_event, revealed_answer=correct_answer, correct_answer_set=True, password_verified=True, leaderboard=leaderboard)

if __name__ == '__main__':
    app.run(debug=True)
