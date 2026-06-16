import os
import httpx
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
URL = "https://www.googleapis.com/youtube/v3/videos"

params = {
    "part": "snippet",
    "chart": "mostPopular",
    "regionCode": "US",
    "maxResults": 5,
    "key": API_KEY,
}

response = httpx.get(URL, params=params)
response.raise_for_status()  # raises an error if the request failed

data = response.json()

print("Top 5 trending videos in the US:\n")
for i, item in enumerate(data["items"], start=1):
    title = item["snippet"]["title"]
    channel = item["snippet"]["channelTitle"]
    print(f"{i}. {title} — {channel}")