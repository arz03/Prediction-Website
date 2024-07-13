# app.py
from flask import Flask, render_template, request, redirect, url_for
import tempfile
import os
from datetime import datetime

app = Flask(__name__)

# Hardcoded password for setting the correct answer (replace with a secure method in production)
password_for_answer = "arjun"

# Set the upcoming event (e.g., what the streamer will wear)
upcoming_event = "Guess the time when jaiyash will start the stream."

# Simple list to store predictions and points
predictions = []
user_predictions = {}
points = {}
correct_answer = ""
leaderboard = []

# Using tempfile to handle predictions and leaderboard files
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
    user_prediction = datetime.strptime(user_prediction, "%H:%M").strftime("%H:%M")

    # Store user predictions in a file for later reference
    with open(predictions_file_path, "a") as file:
        file.write(f"{username}, {user_prediction}\n")
        print(f"{username}, {user_prediction}\n")

    return render_template('index.html', upcoming_event=f"{username}, your prediction has been submitted. Results will be revealed once jaiyash starts the sream. Thank you!")

@app.route('/submit_answer')
def show_submit_answer():
    return render_template('submit_answer.html')

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    global correct_answer
    global leaderboard
    global user_predictions

    # Check if correct_answer is not set, i.e., predictions are still being accepted
    if not correct_answer:
        entered_password = request.form.get('password')

        if entered_password == password_for_answer:
            correct_answer = request.form.get('correct_answer') # Convert to lowercase for case-insensitive matching
            # Parse the correct_answer into a datetime object
            # Assuming the date is not important, using a placeholder date
            correct_time = datetime.strptime(correct_answer, "%H:%M")

            # Read predictions from file and update leaderboard
            user_predictions = {}
            with open(predictions_file_path, "r") as file:
                for line in file:
                    username, user_prediction = line.strip().split(", ")
                    user_prediction_time= datetime.strptime(user_prediction, "%H:%M")
                    user_predictions[username] = user_prediction_time

                    time_difference_seconds = abs((user_prediction_time - correct_time).total_seconds())
                    time_difference = time_difference_seconds / 60
                    points[username] = time_difference

                    #if user_prediction.lower() in correct_answer:
                    #    points[username] = time_difference

            # Update leaderboard file
            with open(leaderboard_file_path, "w") as file:
                for username, score in sorted(points.items(), key=lambda x: x[1], reverse=True):
                    file.write(f"{username}, {score}, {user_predictions.get(username, 'N/A')}\n")

            # Update leaderboard variable
            leaderboard = sorted(points.items(), key=lambda x: x[1], reverse=False)
            print(f"leaderboard list: {leaderboard}")

            return render_template('submit_answer.html', upcoming_event=upcoming_event, correct_answer_submitted=True, correct_answer_set=True, password_verified=True)

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
