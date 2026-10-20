import os
import json
import requests
from datetime import datetime, timedelta, timezone

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY")

# Facebook Page Channel ID
PAGE_CHANNEL_ID = os.getenv("BUFFER_CHANNEL_IDS", "6ad4ee63778b240e2f4a7dcc").split(",")[0].strip()

HISTORY_FILE = "posted_movies.json"
APK_LINK = "https://drive.google.com/uc?export=download&id=1-MzbkxuEXllxTWdPv0zVXRmXtmBlfA9N"
WHATSAPP_LINK = "https://chat.whatsapp.com/L02vNHjowvW83MLbJVqIwC?s=cl&p=a&mlu=4&ilr=4"
FB_PAGE_LINK = "https://www.facebook.com/profile.php?id=61595278122419"
FB_GROUP_LINK = "https://www.facebook.com/share/g/19zsQAbGu7/"
BLOGGER_LINK = "https://filmboxproductions.blogspot.com"
PAYPAL_LINK = "https://www.paypal.com/donate?business=lomalianorman@gmail.com&currency_code=USD"

# TMDB Category / Genre IDs
GENRES = {
    "Action": 28,
    "Comedy": 35,
    "Horror": 27,
    "Romance": 10749,
    "Sci-Fi": 878,
    "Adventure": 12,
    "Thriller": 53,
    "Animation": 16,
    "Fantasy": 14,
    "Crime": 80
}

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_history(posted_ids):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(posted_ids), f)

def fetch_category_movies(genre_name, genre_id, posted_ids):
    # Check pages 1 through 5 to ensure fresh unposted movies
    for page in range(1, 6):
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&page={page}"
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get("results", [])
            for movie in results:
                if movie["id"] not in posted_ids:
                    movie["category"] = genre_name
                    return movie
    return None

def post_to_buffer(movie, scheduled_time):
    title = movie.get("title")
    overview = movie.get("overview", "No description available.")
    poster_path = movie.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
    
    # Format scheduled time into ISO format (YYYY-MM-DDTHH:MM:SSZ)
    due_at_iso = scheduled_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    post_text = (
        f"🎬 {title}\n\n"
        f"{overview}\n\n"
        f"🍿 Watch thousands of movies HD on FILM BOX!\n\n"
        f"🌐 Visit our Blog:\n🔗 {BLOGGER_LINK}\n\n"
        f"👍 Follow our Facebook Page:\n🔗 {FB_PAGE_LINK}\n\n"
        f"👥 Join our Facebook Group:\n🔗 {FB_GROUP_LINK}\n\n"
        f"💬 Join our WhatsApp Group:\n🔗 {WHATSAPP_LINK}\n\n"
        f"☕ Support Project via PayPal:\n🔗 {PAYPAL_LINK}\n\n"
        f"📲 INSTALL FILM BOX APP 👇\n"
        f"📥 Download APK: {APK_LINK}"
    )
    
    graphql_url = "https://api.buffer.com"
    
    input_data = {
        "text": post_text,
        "channelId": PAGE_CHANNEL_ID,
        "schedulingType": "automatic",
        "mode": "customScheduled",
        "dueAt": due_at_iso,
        "metadata": {
            "facebook": {
                "type": "post"
            }
        }
    }

    if poster_url:
        input_data["assets"] = {
            "image": {
                "url": poster_url
            }
        }

    mutation = {
        "query": """
            mutation CreatePost($input: CreatePostInput!) {
                createPost(input: $input) {
                    ... on PostActionSuccess {
                        post { id text dueAt }
                    }
                    ... on MutationError {
                        message
                    }
                }
            }
        """,
        "variables": {
            "input": input_data
        }
    }
    
    headers = {
        "Authorization": f"Bearer {BUFFER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    res = requests.post(graphql_url, json=mutation, headers=headers)
    res_json = res.json()
    print(f"Scheduled '{title}' for {due_at_iso} on Facebook Page: {res_json}")

if __name__ == "__main__":
    if not TMDB_API_KEY or not BUFFER_API_KEY:
        print("Missing required environment variables!")
        exit(1)
        
    posted_ids = load_history()
    selected_movies = []
    
    for genre_name, genre_id in GENRES.items():
        movie = fetch_category_movies(genre_name, genre_id, posted_ids)
        if movie:
            selected_movies.append(movie)
            posted_ids.add(movie["id"])
            if len(selected_movies) >= 10:
                break
                
    print(f"Selected {len(selected_movies)} new unique movies across categories.")
    
    # First post starts 10 minutes from now
    start_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    for idx, movie in enumerate(selected_movies):
        # Space out each post by exactly 1 hour (+0h, +1h, +2h...)
        post_time = start_time + timedelta(hours=idx)
        post_to_buffer(movie, post_time)
        
    save_history(posted_ids)
