import os
import json
import requests
from datetime import datetime, timezone, timedelta

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"
SAVE_PATH = os.path.join(os.getcwd(), "TMDB_Trending.json")

def fetch_tmdb_data(time_window="day", media_type="all"):
    endpoint = f"/trending/all/{time_window}" if media_type == "all" else f"/trending/{media_type}/{time_window}"
    url = f"{BASE_URL}{endpoint}"
    params = {"api_key": TMDB_API_KEY, "language": "zh-CN"}
    response = requests.get(url, params=params)
    return response.json()

def get_media_details(media_type, media_id):
    detail_endpoint = f"/{media_type}/{media_id}"
    url = f"{BASE_URL}{detail_endpoint}"
    params = {"api_key": TMDB_API_KEY, "language": "zh-CN"}
    response = requests.get(url, params=params)
    return response.json()

def get_media_images(media_type, media_id):
    images_endpoint = f"/{media_type}/{media_id}/images"
    url = f"{BASE_URL}{images_endpoint}"
    params = {
        "api_key": TMDB_API_KEY,
        "include_image_language": "zh,en,null"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"backdrops": []}

def get_image_url(path, size="original"):
    return f"https://image.tmdb.org/t/p/{size}{path}"

def get_best_title_backdrop(image_data):
    backdrops = image_data.get("backdrops", [])
    
    def get_priority_score(backdrop):
        lang = backdrop.get("iso_639_1")
        if lang == "zh":
            lang_score = 0
        elif lang == "en":
            lang_score = 1
        elif lang is None:
            lang_score = 2
        else:
            lang_score = 3
        
        vote_avg = -backdrop.get("vote_average", 0)
        
        width = backdrop.get("width", 0)
        height = backdrop.get("height", 0)
        resolution = -(width * height)
        
        return (lang_score, vote_avg, resolution)
    
    sorted_backdrops = sorted(backdrops, key=get_priority_score)
    
    if not sorted_backdrops:
        return ""
    
    best_backdrop = sorted_backdrops[0]
    return get_image_url(best_backdrop["file_path"])
    
def process_tmdb_data(data, time_window, media_type):
    results = []
    for item in data.get("results", []):
        title = item.get("title") or item.get("name")
        release_date = item.get("release_date") or item.get("first_air_date")
        overview = item.get("overview")
        rating = round(item.get("vote_average", 0), 1)
        item_type = media_type if media_type != "all" else item.get("media_type", "unknown")
        media_id = item.get("id")

        poster_url = get_image_url(item.get("poster_path"))

        detail_data = get_media_details(item_type, media_id)
        genres = detail_data.get("genres", [])
        genre_title = "•".join([g["name"] for g in genres[:3]])

        image_data = get_media_images(item_type, media_id)
        title_backdrop_url = get_best_title_backdrop(image_data)

        results.append({
            "id": media_id,
            "title": title,
            "type": item_type,
            "genreTitle": genre_title,
            "rating": rating,
            "release_date": release_date,
            "overview": overview,
            "poster_url": poster_url,
            "title_backdrop": title_backdrop_url
        })
    
    return results

def save_to_json(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def print_results(items, title_text):
    print(f"\n{title_text}")
    for idx, item in enumerate(items[:20], 1):
        print(f"{idx:2d}. {item['title']} ({item['type']}) "
              f"评分: {item['rating']} | {item['genreTitle']}")

def main():
    print("=== 开始执行TMDB数据获取 ===")

    today_global = fetch_tmdb_data(time_window="day", media_type="all")
    today_processed = process_tmdb_data(today_global, "day", "all")

    week_global_all = fetch_tmdb_data(time_window="week", media_type="all")
    week_processed = process_tmdb_data(week_global_all, "week", "all")

    beijing_timezone = timezone(timedelta(hours=8))
    beijing_now = datetime.now(beijing_timezone)
    last_updated = beijing_now.strftime("%Y-%m-%d %H:%M:%S")

    data_to_save = {
        "last_updated": last_updated,
        "today_global": today_processed,
        "week_global_all": week_processed
    }

    save_to_json(data_to_save, SAVE_PATH)

    print(f"✅ 热门数据获取时间: {last_updated}")

    print_results(today_processed, "================= 今日热门  =================")
    print_results(week_processed, "================= 本周热门  =================")

    print("\n================= 执行完成 =================")

if __name__ == "__main__":
    main()