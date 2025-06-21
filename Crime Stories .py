import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# API Key
API_KEY = st.secrets["API_KEY"]

# URLs
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

# Streamlit setup
st.set_page_config(layout="wide")
st.title("🎯 YouTube Viral Topic Finder (True Crime Niche)")

# Filters
days = st.slider("📅 Search videos from past days:", 1, 30, 7)
min_subs, max_subs = st.slider("📊 Channel subscriber range:", 1000, 100000, (1000, 50000), step=1000)
max_results_per_keyword = st.slider("🎬 Max videos per keyword:", 1, 10, 5)

# 50 highly relevant keywords
keywords = [
    "missing persons", "cold case", "unsolved disappearances", "girl vanished", "boy went missing",
    "family disappeared", "child went missing", "vanished without a trace", "found after years",
    "shocking discovery", "real life mystery", "disappearance mystery", "unsolved for years",
    "mystery solved after years", "skeletal remains found", "creepy true crime", "true crime story",
    "tragic disappearance", "disturbing true story", "accidental discovery", "chilling case",
    "real unsolved case", "cold case solved", "abandoned clue", "body found in attic",
    "found in lake", "jogger finds body", "child missing case", "parents never gave up", "found buried",
    "missing teenager", "abduction case", "serial killer victim", "murder mystery", "crime documentary",
    "body in suitcase", "kid vanished", "remains discovered", "case reopened", "tip cracked the case",
    "witness disappeared", "DNA evidence", "unsolved murder", "vanished while hiking", "rural mystery",
    "chilling confession", "true crime analysis", "killer confession", "left behind clues", "hidden remains"
]

# Helper to format numbers
def human_format(num):
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}k"
    return str(num)

# Start search
if st.button("🚀 Fetch Viral Videos"):
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

                try:
                    search_res = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
                    search_res.raise_for_status()
                    search_data = search_res.json()
                except requests.RequestException as e:
                    continue

                items = search_data.get("items", [])
                if not items:
                    continue

                video_ids = [v["id"]["videoId"] for v in items if "videoId" in v["id"]]
                channel_ids = [v["snippet"]["channelId"] for v in items]

                # Get video stats and duration
                stats_res = requests.get(YOUTUBE_VIDEO_URL, params={
                    "part": "statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": API_KEY
                }).json()
                stats_dict = {v['id']: v for v in stats_res.get("items", [])}

                # Get channel stats
                channel_res = requests.get(YOUTUBE_CHANNEL_URL, params={
                    "part": "statistics",
                    "id": ",".join(channel_ids),
                    "key": API_KEY
                }).json()
                channels_dict = {c['id']: c for c in channel_res.get("items", [])}

                # Filter and combine data
                for vid in items:
                    video_id = vid["id"]["videoId"]
                    channel_id = vid["snippet"]["channelId"]
                    stat = stats_dict.get(video_id)
                    chan = channels_dict.get(channel_id)

                    if not stat or not chan:
                        continue

                    # Long-form filter: only if duration > 4 min
                    duration = stat["contentDetails"]["duration"]
                    if "M" not in duration and "H" not in duration:
                        continue  # no minutes or hours
                    if "H" not in duration and int(duration.split("M")[0].replace("PT", "")) < 4:
                        continue

                    title = vid["snippet"]["title"]
                    description = vid["snippet"].get("description", "")[:200]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

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
                        })

                progress.progress((idx + 1) / len(keywords))

            if all_results:
                sorted_results = sorted(all_results, key=lambda x: float(x["Views"].replace("k", "000").replace("M", "000000").replace(".", "")), reverse=True)
                st.success(f"✅ Found {len(sorted_results)} viral videos!")

                for res in sorted_results:
                    st.markdown(f"""
                    **🎬 Title:** {res['Title']}  
                    📅 **Views:** {res['Views']} 👍 **Likes:** {res['Likes']} 💯 **Like/View %:** {res['Like/View %']}%  
                    📺 **Subscribers:** {res['Subscribers']} 📈 **Views/Sub:** {res['Views/Sub']}  
                    🔗 [Watch Video]({res['URL']})  
                    ---
                    """)

                df = pd.DataFrame(sorted_results)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download CSV", csv, "viral_trends.csv", "text/csv")
            else:
                st.warning("No videos matched your filters.")

        except Exception as e:
            st.error(f"❌ Unexpected Error: {e}")
