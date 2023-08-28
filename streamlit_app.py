import streamlit as st
import os
import csv
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from isodate import parse_duration
import pandas as pd
import time

# Authenticate using API key or OAuth credentials
def get_youtube():
    youtube = build("youtube", "v3", developerKey=GoogleApiKey)
    return youtube

def convert_df(df):
   return df.to_csv(index=False).encode('utf-8')


def show_channel_stats(channel_title, channel_description, 
                           channel_view_count, channel_subscriber_count,
                           channel_video_count):
        st.title(channel_title)
        st.write(channel_description)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(label='Videos',value=channel_video_count)


        with col2:
            st.metric(label='Subscribers',value=channel_subscriber_count)

        with col3:
            st.metric(label='Views',value=channel_view_count)


def get_video_stats(channel_id, api_key):
    youtube = get_youtube()
    videos = []
    next_page_token = None

    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()

    time.sleep(0.5)

    # st.write(response)

    if "items" in response and len(response["items"]) > 0:
        item = response["items"][0]
        channel_info = item["snippet"]
        channel_stats = item["statistics"]
        channel_title = channel_info["title"]
        channel_description = channel_info["description"]
        channel_view_count = channel_stats["viewCount"]
        channel_subscriber_count =channel_stats["subscriberCount"]
        channel_video_count = channel_stats["videoCount"]

        show_channel_stats(channel_title, channel_description, 
                        channel_view_count, channel_subscriber_count,
                        channel_video_count)

    while True:
        response = youtube.search().list(
            channelId=channel_id,
            part="id",
            maxResults=50,
            pageToken=next_page_token,
            type="video"
        ).execute()

        time.sleep(0.5)

        videos.extend(item["id"]["videoId"] for item in response.get("items", []))
        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

    video_stats = []

    for video_id in videos:
        response = youtube.videos().list(
            part="statistics,snippet,contentDetails",
            id=video_id
        ).execute()

        video_data = response.get("items", [])[0]


        stats = video_data["statistics"]
        snippet = video_data["snippet"]
        content_details = video_data["contentDetails"]

        title = snippet["title"]

        if "viewCount" in stats: 
            views = int(stats["viewCount"])
        likes = int(stats.get("likeCount", 0))
        duration_iso8601 = content_details["duration"]
        duration_seconds = int(parse_duration(duration_iso8601).total_seconds())
        video_link = f"https://www.youtube.com/watch?v={video_id}"

        # Calculate like rate
        like_rate = round(views / max(likes, 1))  # Avoid division by zero

        video_stats.append((title, video_link, views, likes, duration_seconds, like_rate))

    return video_stats

def export_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Title", "Video Link", "Views", "Likes", "Duration (s)", "Like Rate"])

        for stat in data:
            csv_writer.writerow(stat)

    print(f"Data written to {filename}")

def create_dataframe(data):
    columns = ["Title", "Video Link", "Views", "Likes", "Duration (s)", "Like Rate"]
    df = pd.DataFrame(data, columns=columns)
    return df


def get_data():
    with st.spinner('Fetching data...'):    
  
        video_stats = get_video_stats(channel_id, GoogleApiKey)
    
        average_views = sum(stat[2] for stat in video_stats) / len(video_stats)
        filtered_sorted_stats = [stat for stat in video_stats if stat[2] >= average_views]
        filtered_sorted_stats.sort(key=lambda x: x[5])

        # export_to_csv(filtered_sorted_stats, "youtube_stats.csv")
        df = create_dataframe(filtered_sorted_stats)
    st.write(df)

    st.download_button(
   "Press to Download",
   convert_df(df),
   channel_id+".csv",
   "text/csv",
   key='download-csv'
)


with st.sidebar:
    st.title(':arrow_forward: :zap: Youtoube Channel Research')
    if 'GOOGLE_API_KEY' in st.secrets:
        st.success('API key already provided!', icon='✅')
        GoogleApiKey = st.secrets['GOOGLE_API_KEY'] 
    else:
        GoogleApiKey = st.text_input('Enter Google API token:', type='password')
    # st.markdown('📖 Learn how to build this app in this [blog](#link-to-blog)!')


    with st.form("stats form"):
        channel_id= st.text_input('channel ID', value="")
        submitted = st.form_submit_button(label="Get stats")

if submitted == True:
    get_data()            

