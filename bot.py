import os
import json
import requests

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BUFFER_API_KEY = os.getenv("BUFFER_API_KEY")
BUFFER_CHANNEL_IDS = [cid.strip() for cid in os.getenv("BUFFER_CHANNEL_IDS", "").split(",") if cid.strip()]

HISTORY_FILE = "posted_movies.json"
APK_LINK = "https://drive.google.com/uc?export=download&id=19RPdMPaflAMCujyiroh95BxDWJRoff4X"

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
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&page=1"
    response = requests.get(url)
    if response.status_code == 200:
        results = response.json().get("results", [])
        for movie in results:
            if movie["id"] not in posted_ids:
                movie["category"] = genre_name
                return movie
    return None

def post_to_buffer(movie):
    title = movie.get("title")
    overview = movie.get("overview", "No description available.")
    category = movie.get("category", "Featured")
    poster_path = movie.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
    
    post_text = (
        f"🎬 [{category.upper()}] {title}\n\n"
        f"{overview}\n\n"
        f"🍿 Watch this and thousands of other movies on FILM BOX!\n\n"
        f"📥 ┌────────────────────────┐\n"
        f"     INSTALL FILM BOX APP\n"
        f"  └────────────────────────┘\n"
        f"👉 Download APK: {APK_LINK}\n\n"
        f"Poster: {poster_url}"
    )
    
    graphql_url = "https://api.buffer.com"
    
    for channel_id in BUFFER_CHANNEL_IDS:
        mutation = {
            "query": """
                mutation CreatePost($input: CreatePostInput!) {
                    createPost(input: $input) {
                        ... on PostActionSuccess {
                            post { id text }
                        }
                        ... on MutationError {
                            message
                        }
                    }
                }
            """,
            "variables": {
                "input": {
                    "text": post_text,
                    "channelId": channel_id,
                    "schedulingType": "automatic",
                    "mode": "addToQueue"
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        res = requests.post(graphql_url, json=mutation, headers=headers)
        res_json = res.json()
        print(f"Queued '{title}' ({category}) to channel {channel_id}: {res_json}")

if __name__ == "__main__":
    if not TMDB_API_KEY or not BUFFER_API_KEY or not BUFFER_CHANNEL_IDS:
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
    
    for movie in selected_movies:
        post_to_buffer(movie)
        
    save_history(posted_ids)
