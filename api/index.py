from flask import Flask, render_template, request, redirect, url_for
import tempfile, os, re
from datetime import datetime
import json

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
leaderboard_history = {}

# Temporary file paths for storing predictions
with tempfile.NamedTemporaryFile(mode='w+', delete=False) as predictions_file:
    predictions_file_path = predictions_file.name

# Directory for storing leaderboards
leaderboards_dir = tempfile.mkdtemp()

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
    global leaderboard_history

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

                # Save leaderboard to a timestamped file
                leaderboard_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                leaderboard_filename = f"leaderboard_{leaderboard_timestamp}.json"
                leaderboard_filepath = os.path.join(leaderboards_dir, leaderboard_filename)

                with open(leaderboard_filepath, "w") as file:
                    json.dump(points, file)

                # Update leaderboard variable and history
                leaderboard = sorted(points.items(), key=lambda x: x[1], reverse=False)
                leaderboard_history[leaderboard_timestamp] = leaderboard

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
    global leaderboard_history

    # Load leaderboard history
    leaderboard_files = [f for f in os.listdir(leaderboards_dir) if f.startswith("leaderboard_")]
    leaderboard_dates = [f.split("_")[1].split(".")[0] for f in leaderboard_files]

    return render_template('revealed_answer.html', predictions=predictions, upcoming_event=upcoming_event, revealed_answer=correct_answer, correct_answer_set=True, password_verified=True, leaderboard=leaderboard, user_predictions=user_predictions, leaderboard_history=leaderboard_history, leaderboard_dates=leaderboard_dates)

if __name__ == '__main__':
    app.run(debug=True)
