import requests
import json
import os
from datetime import datetime, timezone, timedelta

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    print("错误：未找到 TMDB_API_KEY 环境变量！")
    exit(1)

BASE_URL = "https://api.themoviedb.org/3"
SAVE_PATH = os.path.join(os.getcwd(), "tmdbNowPlaying.json")

def get_global_trending_cn(time_window: str = "day", media_type: str = "all"):
    if not TMDB_API_KEY:
        print("错误：TMDB API Key 未配置！")
        return []
    
    if media_type == "all":
        endpoint = f"/trending/all/{time_window}"
    else:
        endpoint = f"/trending/{media_type}/{time_window}"
    
    url = f"{BASE_URL}{endpoint}"
    
    params = {
        "api_key": TMDB_API_KEY,
        "language": "zh-CN"
    }
    
    try:
        print(f"正在请求API: {url}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("results", []):
            title = item.get("title") or item.get("name", "未知标题")
            release_date = item.get("release_date") or item.get("first_air_date", "未知日期")
            overview = item.get("overview", "暂无简介")
            rating = round(item.get("vote_average", 0), 1)
            
            poster_url = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get("poster_path") else "无海报"
            backdrop_url = f"https://image.tmdb.org/t/p/w500{item.get('backdrop_path')}" if item.get("backdrop_path") else "无背景图"
            
            item_type = media_type
            if media_type == "all":
                item_type = item.get("media_type", "unknown")
            
            results.append({
                "id": item.get("id"),
                "title": title,
                "type": item_type,
                "release_date": release_date,
                "overview": overview,
                "rating": rating,
                "poster_url": poster_url,
                "backdrop_url": backdrop_url
            })
        
        print(f"共获取到 {len(results)} 条数据")
        return results
    
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        reason = e.response.reason
        print(f"HTTP 错误: {status_code} - {reason}")
        if status_code == 401:
            print("提示：请检查 API Key 是否正确或已过期！")
        return []
    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {str(e)}")
        return []
    except Exception as e:
        print(f"解析数据失败: {str(e)}")
        return []

def save_to_json(data: dict, file_path: str):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
        
        print(f"✅ 数据已成功保存到: {os.path.abspath(file_path)}")
        return True
    except Exception as e:
        print(f"❌ 保存文件失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== 开始执行TMDb数据获取 ===")
    print(f"当前工作目录: {os.getcwd()}")
    
    today_global = get_global_trending_cn(time_window="day", media_type="all")
    print(f"获取到 {len(today_global)} 条今日热门数据")
    
    week_global_movies = get_global_trending_cn(time_window="week", media_type="movie")
    print(f"获取到 {len(week_global_movies)} 条本周热门数据")
    
    beijing_timezone = timezone(timedelta(hours=8))
    beijing_now = datetime.now(beijing_timezone)
    last_updated = beijing_now.strftime("%Y-%m-%d %H:%M:%S")
    
    data_to_save = {
        "last_updated": last_updated,
        "today_global": today_global,
        "week_global_movies": week_global_movies
    }
    
    save_success = save_to_json(data_to_save, SAVE_PATH)
    
    if not save_success:
        print("⚠️ 文件保存失败，脚本将退出")
        exit(1)
    
    print("\n=== 今日热门 ===")
    if today_global:
        for idx, item in enumerate(today_global[:20], 1):
            print(f"{idx}. {item['title']} ({item['type']}) 评分: {item['rating']}")
    
    print("\n=== 本周热门 ===")
    if week_global_movies:
        for idx, item in enumerate(week_global_movies[:20], 1):
            print(f"{idx}. {item['title']} (评分: {item['rating']})")
    
    print("\n=== 执行完成 ===")
