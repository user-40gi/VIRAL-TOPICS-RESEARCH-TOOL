import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = st.secrets["AIzaSyAIKESiph66SzOWR9LJOjkgltJJJo9MJrM"]

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

st.set_page_config(layout="wide")
st.title("YouTube Viral Topic Finder (Prehistoric Survival Niche)")

# Filters
days = st.slider("Search videos from past days:", 1, 30, 7)
min_subs, max_subs = st.slider("Channel subscriber range:", 1000, 100000, (1000, 50000), step=1000)
max_results_per_keyword = st.slider("Max videos per keyword:", 1, 10, 5)

# Injected keywords
keywords = [
    # Primary Keywords (High Priority)
    "stone age survival",
    "prehistoric humans",
    "why you wouldn't survive",
    "ancient human survival",
    "paleolithic life",
    "early humans documentary",
    "stone age documentary",
    "caveman survival",
    "human evolution",
    "primitive survival",

    # Secondary Keywords (Medium Priority)
    "neanderthal life",
    "ice age survival",
    "prehistoric animals",
    "ancient civilizations",
    "human origins",
    "stone age tools",
    "fire making ancient",
    "hunter gatherer",
    "bronze age",
    "mesolithic period",

    # Long-tail Keywords (Specific Topics)
    "what if you lived in stone age",
    "prehistoric humans vs modern humans",
    "how cavemen survived winter",
    "ancient human extinction",
    "stone age daily life",
    "prehistoric human diet",
    "early human migration",
    "caveman vs modern technology",
    "prehistoric human society",
    "ancient human discoveries",

    # Additional Trending Keywords
    "stone age life",
    "caveman documentary",
    "prehistoric survival",
    "ancient humans documentary",
    "paleolithic documentary",
    "early human evolution",
    "stone age people",
    "primitive life",
    "prehistoric life",
    "ancient survival skills",
    "caveman life",
    "stone age civilization",
    "prehistoric world",
    "ancient human history",
    "paleolithic humans"
]

def human_format(num):
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}k"
    return str(num)

def days_ago(published_at_str):
    published_date = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
    delta_days = (datetime.utcnow() - published_date).days
    return f"{delta_days} days ago"

# Main logic
if st.button("Fetch Viral Videos"):
    with st.spinner("Fetching viral videos..."):
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat("T") + "Z"
            all_results = []
            progress = st.progress(0)

            for idx, keyword in enumerate(keywords):
                search_params = {
                    "part": "snippet",
                    "q": keyword,
                    "type": "video",
                    "order": "viewCount",
                    "publishedAfter": start_date,
                    "maxResults": max_results_per_keyword,
                    "relevanceLanguage": "en",
                    "key": API_KEY
                }

                search_res = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
                items = search_res.json().get("items", [])
                if not items:
                    continue

                video_ids = [v["id"]["videoId"] for v in items if "videoId" in v["id"]]
                channel_ids = [v["snippet"]["channelId"] for v in items]

                stats_res = requests.get(YOUTUBE_VIDEO_URL, params={
                    "part": "statistics,contentDetails,snippet",
                    "id": ",".join(video_ids),
                    "key": API_KEY
                }).json()
                stats_dict = {v['id']: v for v in stats_res.get("items", [])}

                channel_res = requests.get(YOUTUBE_CHANNEL_URL, params={
                    "part": "statistics",
                    "id": ",".join(channel_ids),
                    "key": API_KEY
                }).json()
                channels_dict = {c['id']: c for c in channel_res.get("items", [])}

                for vid in items:
                    video_id = vid["id"]["videoId"]
                    channel_id = vid["snippet"]["channelId"]
                    stat = stats_dict.get(video_id)
                    chan = channels_dict.get(channel_id)

                    if not stat or not chan:
                        continue

                    duration = stat["contentDetails"]["duration"]
                    if "M" not in duration and "H" not in duration:
                        continue
                    try:
                        minutes = int(duration.split("M")[0].replace("PT", ""))
                        if minutes < 4 and "H" not in duration:
                            continue
                    except:
                        continue

                    title = vid["snippet"]["title"]
                    description = vid["snippet"].get("description", "")[:200]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    published_date = stat["snippet"]["publishedAt"]
                    uploaded = days_ago(published_date)

                    views = int(stat["statistics"].get("viewCount", 0))
                    likes = int(stat["statistics"].get("likeCount", 0))
                    subs = int(chan["statistics"].get("subscriberCount", 0))

                    if min_subs <= subs <= max_subs:
                        like_ratio = round((likes / views) * 100, 2) if views else 0
                        view_sub_ratio = round((views / subs), 2) if subs else 0
                        all_results.append({
                            "Title": title,
                            "Description": description,
                            "URL": video_url,
                            "Views": human_format(views),
                            "Likes": human_format(likes),
                            "Like/View %": like_ratio,
                            "Views/Sub": view_sub_ratio,
                            "Subscribers": human_format(subs),
                            "Uploaded": uploaded
                        })

                progress.progress((idx + 1) / len(keywords))

            if all_results:
                sorted_results = sorted(
                    all_results,
                    key=lambda x: float(x["Views"].replace("k", "000").replace("M", "000000").replace(".", "")),
                    reverse=True
                )
                st.success(f"Found {len(sorted_results)} viral videos!")

                for res in sorted_results:
                    st.markdown(f"""
                    **Title:** {res['Title']}  
                    Uploaded: {res['Uploaded']}  
                    Views: {res['Views']} Likes: {res['Likes']} Like/View %: {res['Like/View %']}%  
                    Subscribers: {res['Subscribers']} Views/Sub: {res['Views/Sub']}  
                    Link: [Watch Video]({res['URL']})  
                    ---
                    """)

                df = pd.DataFrame(sorted_results)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", csv, "viral_trends.csv", "text/csv")
            else:
                st.warning("No videos matched your filters.")
        except Exception as e:
            st.error(f"Unexpected Error: {e}")
