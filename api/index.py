from flask import Flask, render_template, request, redirect, url_for
import tempfile, time, pytz, requests, os
from dotenv import load_dotenv
import discord, re
from datetime import datetime, timedelta
from threading import Thread

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# API key and channel ID for YouTube API
api_key = os.getenv("API_KEY")
channel_id = os.getenv("CHANNEL_ID")

# Discord token and announcement channel ID
TOKEN = os.getenv("DISCORD_TOKEN")
ANNOUNCEMENT_CHANNEL_ID = 1264189333380792330
# Password for submitting the answer
password_for_answer = os.getenv("PASSWORD_FOR_ANSWER")

# Upcoming event description
upcoming_event = "Guess the time when jaiyash will start the stream."

# List to store predictions
predictions = []

# Variable to store discord announcement time
discord_announcement_time = None

# Variable to store stream link
stream_link = ""

# Dictionary to store user predictions
user_predictions = {}

# Dictionary to store points for each user
points = {}

# Variable to store the correct answer
correct_answer = ""

# List to store the leaderboard
leaderboard = []

# Variable to store the stream start time
stream_start_time = None

# Discord bot to get the stream link
class DiscordBot(discord.Client):
    async def on_ready(self):
        print(f'Logged in on discord as {self.user}')

    async def on_message(self, message):
        if message.channel.id == ANNOUNCEMENT_CHANNEL_ID:
            global discord_announcement_time
            global stream_link
            discord_announcement_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M')
            stream_link = message.content
            print(f"Discord announcement time: {discord_announcement_time} Stream link: {stream_link}")
            if is_valid_youtube_live_stream(stream_link):
                # sleep for 30 seconds before calculating points
                #time.sleep(30)
                # Create a thread to run check_and_calculate_points() in the background
                thread = Thread(target=check_and_calculate_points)
                thread.start()
                thread.join(timeout=5400)  # Wait for 90 minutes (5400 seconds) for the thread to finish
                if thread.is_alive():
                    thread.stop()  # Stop the thread if it doesn't finish automatically after 90 minutes
            else:
                print(f"Invalid live stream link: {stream_link}")


intents = discord.Intents.default()
intents.messages = True
client = DiscordBot(intents=intents)
#client.run(TOKEN)

def extract_video_id(url):
    """
    Extracts the video ID from a YouTube URL.
    """
    video_id_match = re.search(r'v=([^&]+)', url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def is_valid_youtube_live_stream(url):
    """
    Checks if the given URL is a valid YouTube live stream.
    """
    print(f"YT api : Checking if 'Discord Stream Link' is a valid YouTube live stream...")
    video_id = extract_video_id(url)
    if not video_id:
        return False

    youtube_api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=snippet,liveStreamingDetails&key={api_key}"
    response = requests.get(youtube_api_url)
    if response.status_code != 200:
        return False

    data = response.json()
    if 'items' not in data or not data['items']:
        return False

    video_data = data['items'][0]
    live_streaming_details = video_data.get('liveStreamingDetails', None)
    if live_streaming_details and 'actualStartTime' in live_streaming_details:
        print(f"YT api : 'Discord Stream Link' is a valid YouTube live stream.")
        return True
    return False

# Create temporary files to store predictions and leaderboard
with tempfile.NamedTemporaryFile(mode='w+', delete=False) as predictions_file, tempfile.NamedTemporaryFile(mode='w+', delete=False) as leaderboard_file:
    predictions_file_path = predictions_file.name
    leaderboard_file_path = leaderboard_file.name

@app.route('/')
def home():
    """
    Renders the home page with the upcoming event description.
    """
    return render_template('index.html', upcoming_event=upcoming_event)

@app.route('/submit_prediction', methods=['POST'])
def submit_prediction():
    """
    Handles the submission of user predictions.
    """
    global predictions
    username = request.form.get('username')
    user_prediction = request.form.get('prediction')
    user_prediction = datetime.strptime(user_prediction, "%H:%M").strftime("%H:%M")

    with open(predictions_file_path, "a") as file:
        file.write(f"{username}, {user_prediction}\n")
        print(f"{username}, {user_prediction}\n")

    return render_template('index.html', upcoming_event=f"{username}, your prediction has been submitted. Results will be revealed once jaiyash starts the stream. Thank you!")

def get_live_start_time(api_key, channel_id):
    """
    Checks if Jaiyash is live yet and returns the live start time.
    """
    print("YT API : Checking if jaiyash is live yet...")
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "eventType": "live",
        "type": "video",
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)  # Timeout after 10 seconds
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        
        if not data["items"]:
            print("YT API : Jaiyash is not live yet.")
            return None  # Not live
        
        video_id = data["items"][0]["id"]["videoId"]
        
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "liveStreamingDetails",
            "id": video_id,
            "key": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)  # Timeout after 10 seconds
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        
        live_start_time = data["items"][0]["liveStreamingDetails"]["actualStartTime"]
        live_start_time = datetime.fromisoformat(live_start_time.replace("Z", "+00:00"))
        
        # Convert to IST
        ist = pytz.timezone('Asia/Kolkata')
        live_start_time_ist = live_start_time.astimezone(ist)
        
        return live_start_time_ist.strftime('%H:%M')  # 24-hour format

    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

@app.route('/submit_answer')
def show_submit_answer():
    """
    Renders the page to submit the correct answer.
    """
    with open(predictions_file_path, "r") as file:
        t_user_predictions = {}
        for line in file:
            username, user_prediction = line.strip().split(", ")
            t_user_predictions[username] = user_prediction

    print(f"user predictions: {t_user_predictions}")
    print(f"leaderboard: {leaderboard}")
    return render_template('submit_answer.html')

@app.route('/calculate_points')
def calculate_points():
    """
    Automatically calculates the points once the stream is live.
    """
    global correct_answer
    global leaderboard
    global user_predictions
    global live_start_time

    print("Calculating leaderboard...")

    if not correct_answer:
        while True:
            if live_start_time:
                correct_answer = live_start_time.strftime('%H:%M')
            else:
                correct_answer = get_live_start_time(api_key, channel_id)
            
            correct_time = datetime.strptime(correct_answer, "%H:%M")
            user_predictions = {}
            with open(predictions_file_path, "r") as file:
                for line in file:
                    username, user_prediction = line.strip().split(", ")
                    user_prediction_time = datetime.strptime(user_prediction, "%H:%M")
                    user_predictions[username] = user_prediction_time
            
                    time_difference_seconds = abs((user_prediction_time - correct_time).total_seconds())
                    time_difference = time_difference_seconds / 60
                    points[username] = time_difference
            
            with open(leaderboard_file_path, "w") as file:
                for username, score in sorted(points.items(), key=lambda x: x[1], reverse=True):
                    file.write(f"{username}, {score}, {user_predictions.get(username, 'N/A')}\n")
            
            leaderboard = sorted(points.items(), key=lambda x: x[1], reverse=False)
            print(f"Final leaderboard list: {leaderboard}")
            
            return render_template('submit_answer.html', upcoming_event=upcoming_event, correct_answer_submitted=True, correct_answer_set=True, password_verified=True)

@app.route('/reveal_answer')
def reveal_answer():
    """
    Renders the page to reveal the correct answer and leaderboard.
    """
    global correct_answer
    global leaderboard
    global user_predictions
    
    return render_template('revealed_answer.html', predictions=predictions, upcoming_event=upcoming_event, revealed_answer=correct_answer, correct_answer_set=True, password_verified=True, leaderboard=leaderboard, user_predictions=user_predictions)

@app.route('/reset')
def reset():
    """
    Resets the state of the application.
    """
    global correct_answer
    global leaderboard
    global predictions
    global user_predictions
    global points
    global stream_start_time
    global discord_announcement_time
    global stream_link
    global live_start_time

    correct_answer = ""
    leaderboard = []
    predictions = []
    user_predictions = {}
    points = {}
    stream_start_time = None
    discord_announcement_time = None
    stream_link = ""
    live_start_time = None

    open(predictions_file_path, 'w').close()
    open(leaderboard_file_path, 'w').close()

    return redirect(url_for('home'))

def check_and_calculate_points():
    """
    Checks if the stream is live and calculates points if it is.
    """
    global stream_start_time
    global live_start_time
    while True:
        live_start_time = get_live_start_time(api_key, channel_id)
        if live_start_time:
            if not stream_start_time:
                stream_start_time = datetime.now(pytz.timezone('Asia/Kolkata'))
                calculate_points()
                reset_time = stream_start_time + timedelta(hours=10)
                print(f"Stream has started at {stream_start_time}. Resetting state at {reset_time}.")
                print(f"Stream has started at {stream_start_time}. Resetting state at {reset_time}.")
                print(f"Stream has started at {stream_start_time}. Resetting state at {reset_time}.")
                print(f"Stream has started at {stream_start_time}. Resetting state at {reset_time}.")
                while datetime.now(pytz.timezone('Asia/Kolkata')) < reset_time:
                    time.sleep(60)  # Sleep in intervals of 60 seconds
                with app.app_context():
                    reset()
                    print("State has been automatically reset.")
                    print("State has been automatically reset.")
                    print("State has been automatically reset.")
                    print("State has been automatically reset.")
        else:
            print("Not live yet, checking again in 60 seconds...")
        time.sleep(60)  # Check every 60 seconds

if __name__ == '__main__':
    # Start discord bot
    discord_bot_thread = Thread(target=client.run, args=(TOKEN,))
    print("Starting discord bot...")
    discord_bot_thread.start()
    app.run(debug=False)
