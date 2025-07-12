import os
import json
import requests
import time
from datetime import datetime, timezone, timedelta

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    print("错误：未找到 TMDB_API_KEY ！")
    exit(1)

BASE_URL = "https://api.themoviedb.org/3"
SAVE_PATH = os.path.join(os.getcwd(), "TMDB_Trending.json")

def fetch_tmdb_data(time_window="day", media_type="all"):
    if not TMDB_API_KEY:
        print("错误：TMDB API Key 未配置！")
        return []
    
    endpoint = f"/trending/all/{time_window}" if media_type == "all" else f"/trending/{media_type}/{time_window}"
    url = f"{BASE_URL}{endpoint}"
    params = {"api_key": TMDB_API_KEY, "language": "zh-CN"}

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            print(f"API请求成功: {url}")
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            reason = e.response.reason
            print(f"HTTP错误 ({status_code}): {reason} (URL: {url})")
            if status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", retry_delay))
                print(f"触发限流，等待 {retry_after} 秒后重试...")
                time.sleep(retry_after)
                continue
            if status_code == 401:
                print("API Key无效或已过期，请检查环境变量！")
            return []
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {str(e)} (URL: {url})")
            if attempt == max_retries - 1:
                print("所有重试均失败，放弃请求")
                return []

def get_media_details(media_type, media_id):
    detail_endpoint = f"/{media_type}/{media_id}"
    url = f"{BASE_URL}{detail_endpoint}"
    params = {"api_key": TMDB_API_KEY, "language": "zh-CN"}

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            reason = e.response.reason
            return None
        except requests.exceptions.RequestException as e:
            print(f"媒体详情网络请求失败: {str(e)} (ID: {media_id})")
            if attempt == max_retries - 1:
                print(f"放弃获取媒体ID {media_id} 的详细信息")
                return None

def process_tmdb_data(data, time_window, media_type):
    results = []
    for item in data.get("results", []):
        title = item.get("title") or item.get("name", "未知标题")
        release_date = item.get("release_date") or item.get("first_air_date", "未知日期")
        overview = item.get("overview", "暂无简介")
        rating = round(item.get("vote_average", 0), 1)
        poster_url = f"https://image.tmdb.org/t/p/original{item.get('poster_path')}" if item.get("poster_path") else "无海报"
        backdrop_url = f"https://image.tmdb.org/t/p/original{item.get('backdrop_path')}" if item.get("backdrop_path") else "无背景图"
        item_type = media_type if media_type != "all" else item.get("media_type", "unknown")

        genre_title = "未知分类"
        if media_id := item.get("id"):
            if item_type in ["movie", "tv"]:
                detail_data = get_media_details(item_type, media_id)
                if detail_data:
                    genres = detail_data.get("genres", [])
                    genre_title = ", ".join([g["name"] for g in genres[:2]])

        results.append({
            "id": media_id,
            "title": title,
            "type": item_type,
            "release_date": release_date,
            "overview": overview,
            "rating": rating,
            "poster_url": poster_url,
            "backdrop_url": backdrop_url,
            "genreTitle": genre_title
        })
    return results

def save_to_json(data, file_path):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"数据成功保存至: {file_path}")
        return True
    except Exception as e:
        print(f"文件保存失败: {str(e)}")
        return False

if __name__ == "__main__":
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

    save_success = save_to_json(data_to_save, SAVE_PATH)
    if not save_success:
        print("文件保存失败，脚本终止执行")
        exit(1)

    print(f"✅ 热门数据获取时间: {last_updated}")

    print("""
================= 今日热门 =================""")
    if today_processed:
        for idx, item in enumerate(today_processed[:20], 1):
            print(f"{idx}. {item['title']} ({item['type']}) 评分: {item['rating']} | {item['genreTitle']}")

    print("""
================= 本周热门 =================""")
    if week_processed:
        for idx, item in enumerate(week_processed[:20], 1):
            print(f"{idx}. {item['title']} ({item['type']}) 评分: {item['rating']} | {item['genreTitle']}")

    print("""
================= 执行完成 =================""")
