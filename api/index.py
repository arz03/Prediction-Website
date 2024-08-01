from flask import Flask, render_template, request, redirect, url_for
import tempfile, os, re
from datetime import datetime

app = Flask(__name__)

# Load environment variables from .env file
password_for_answer = os.getenv("PASSWORD_FOR_ANSWER")

# Set the upcoming event description
upcoming_event = "Guess the time when jaiyash will start the stream."

# Variables to store predictions, user predictions, points, and leaderboard
predictions = []
user_predictions = {}
points = {}
correct_answer = ""
leaderboard = []

# Temporary file paths for storing predictions and leaderboard
with tempfile.NamedTemporaryFile(mode='w+', delete=False) as predictions_file, tempfile.NamedTemporaryFile(mode='w+', delete=False) as leaderboard_file:
    predictions_file_path = predictions_file.name
    leaderboard_file_path = leaderboard_file.name

@app.route('/')
def home():
    return render_template('index.html', upcoming_event=upcoming_event)

@app.route('/submit_prediction', methods=['POST'])
def submit_prediction():
    global predictions
    username = request.form.get('username')
    user_prediction = request.form.get('prediction')

    # Validate user prediction format
    try:
        user_prediction = datetime.strptime(user_prediction, "%H:%M").strftime("%H:%M")
    except ValueError:
        return render_template('index.html', upcoming_event=f"Invalid prediction format, {username}. Please use HH:MM.")

    # Store user predictions in a file for later reference
    with open(predictions_file_path, "a") as file:
        file.write(f"{username}, {user_prediction}\n")
        print(f"{username}, {user_prediction}\n")

    return render_template('index.html', upcoming_event=f"{username}, your prediction has been submitted. Results will be revealed once jaiyash starts the stream. Thank you!")

@app.route('/submit_answer')
def show_submit_answer():
    try:
        t_user_predictions = {}
        with open(predictions_file_path, "r") as file:
            for line in file:
                try:
                    username, user_prediction = line.strip().split(", ")
                    t_user_predictions[username] = user_prediction
                except ValueError:
                    print(f"Skipping malformed line: {line.strip()}")
                    continue
    except FileNotFoundError:
        print("No predictions found.")
        t_user_predictions = {}

    print(f"user predictions: {t_user_predictions}")
    print(f"leaderboard: {leaderboard}")
    return render_template('submit_answer.html')

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    global correct_answer
    global leaderboard
    global user_predictions

    if not correct_answer:
        entered_password = request.form.get('password')

        if entered_password == password_for_answer:
            correct_answer_input = request.form.get('correct_answer')
            try:
                correct_answer = datetime.strptime(correct_answer_input, "%H:%M").strftime("%H:%M")
            except ValueError:
                return render_template('submit_answer.html', upcoming_event=upcoming_event, correct_answer_submitted=False, correct_answer_set=False, password_verified=True, error="Invalid time format. Please use HH:MM.")

            correct_time = datetime.strptime(correct_answer, "%H:%M")

            try:
                with open(predictions_file_path, "r") as file:
                    for line in file:
                        try:
                            username, user_prediction = line.strip().split(", ")
                            user_prediction_time = datetime.strptime(user_prediction, "%H:%M")
                            user_predictions[username] = user_prediction_time

                            time_difference_seconds = abs((user_prediction_time - correct_time).total_seconds())
                            time_difference = time_difference_seconds / 60
                            points[username] = time_difference

                        except ValueError:
                            print(f"Skipping malformed line: {line.strip()}")
                            continue

                with open(leaderboard_file_path, "w") as file:
                    for username, score in sorted(points.items(), key=lambda x: x[1], reverse=True):
                        file.write(f"{username}, {score}, {user_predictions.get(username, 'N/A')}\n")

                leaderboard = sorted(points.items(), key=lambda x: x[1], reverse=False)
                print(f"Leaderboard list: {leaderboard}")

                return render_template('submit_answer.html', upcoming_event=upcoming_event, correct_answer_submitted=True, correct_answer_set=True, password_verified=True)

            except FileNotFoundError:
                print("No predictions file found.")
                return render_template('submit_answer.html', upcoming_event=upcoming_event, correct_answer_submitted=False, correct_answer_set=False, password_verified=True, error="No predictions found.")

        else:
            return redirect(url_for('home'))

    return redirect(url_for('home'))

@app.route('/reveal_answer')
def reveal_answer():
    global correct_answer
    global leaderboard
    global user_predictions
    
    return render_template('revealed_answer.html', predictions=predictions, upcoming_event=upcoming_event, revealed_answer=correct_answer, correct_answer_set=True, password_verified=True, leaderboard=leaderboard, user_predictions=user_predictions)

if __name__ == '__main__':
    app.run(debug=True)
