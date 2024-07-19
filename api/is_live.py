import requests
from datetime import datetime, timedelta
import pytz

def get_live_start_time(api_key, channel_id):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "eventType": "live",
        "type": "video",
        "key": api_key
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if not data["items"]:
        return None  # Not live
    
    video_id = data["items"][0]["id"]["videoId"]
    
    url = f"https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "liveStreamingDetails",
        "id": video_id,
        "key": api_key
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    live_start_time = data["items"][0]["liveStreamingDetails"]["actualStartTime"]
    live_start_time = datetime.fromisoformat(live_start_time.replace("Z", "+00:00"))
    
    # Convert to IST
    ist = pytz.timezone('Asia/Kolkata')
    live_start_time_ist = live_start_time.astimezone(ist)
    
    return live_start_time_ist.strftime('%H:%M')  # 24-hour format
