import requests
import json
import os
from datetime import datetime

# --------------------------
# 从环境变量读取 API Key
# --------------------------

# 检查环境变量是否设置
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    print("错误：未找到 TMDB_API_KEY 环境变量！")
    exit(1)

# --------------------------
# TMDb API 配置
# --------------------------

BASE_URL = "https://api.themoviedb.org/3"
SAVE_PATH = "Widgets/tmdbNowPlaying.json"  # 保存路径

# --------------------------
# 获取全球热门影视数据（中文）
# --------------------------

def get_global_trending_cn(time_window: str = "day", media_type: str = "all"):
    """
    获取全球热门影视数据（今日/本周热门），数据语言为中文（简体）
    
    参数:
        time_window (str): 时间范围，可选 "day"（今日）或 "week"（本周）
        media_type (str): 媒体类型，可选 "movie"（电影）、"tv"（剧集）或 "all"（默认）
    
    返回:
        list: 包含中文信息的影视字典列表
    """
    # 验证 API Key 是否为空
    if not TMDB_API_KEY:
        print("错误：TMDB API Key 未配置！")
        return []
    
    # 构造 API 端点（v3 的 trending 端点支持 language 参数）
    if media_type == "all":
        endpoint = f"/trending/all/{time_window}"
    else:
        endpoint = f"/trending/{media_type}/{time_window}"
    
    url = f"{BASE_URL}{endpoint}"
    
    # 请求参数（固定 language=zh-CN）
    params = {
        "api_key": TMDB_API_KEY,
        "language": "zh-CN"  # 强制返回中文信息
    }
    
    try:
        # 发送 GET 请求并检查 HTTP 状态码
        response = requests.get(url, params=params)
        response.raise_for_status()  # 若状态码非 200，抛出异常（如 401 无效 Key）
        data = response.json()
        
        # 提取关键信息（处理可能的空值）
        results = []
        for item in data.get("results", []):
            # 处理可能缺失的字段（如无标题、日期、简介等）
            title = item.get("title") or item.get("name", "未知标题")
            release_date = item.get("release_date") or item.get("first_air_date", "未知日期")
            overview = item.get("overview", "暂无简介")
            rating = item.get("vote_average", 0)  # 无评分时默认 0
            
            # 拼接完整图片 URL（若存在）
            poster_url = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get("poster_path") else "无海报"
            backdrop_url = f"https://image.tmdb.org/t/p/w500{item.get('backdrop_path')}" if item.get("backdrop_path") else "无背景图"
            
            # 确定媒体类型（电影/剧集）
            item_type = media_type
            if media_type == "all":
                # 当选择所有类型时，从返回数据中获取实际类型
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
        
        return results
    
    except requests.exceptions.HTTPError as e:
        # 处理 HTTP 错误（如 401 无效 Key、404 路径错误）
        status_code = e.response.status_code
        reason = e.response.reason
        print(f"HTTP 错误: {status_code} - {reason}")
        if status_code == 401:
            print("提示：请检查 API Key 是否正确或已过期！")
        return []
    except requests.exceptions.RequestException as e:
        # 处理网络连接错误（如无网络、超时）
        print(f"网络请求失败: {e}")
        return []
    except Exception as e:
        # 处理其他异常（如 JSON 解析失败）
        print(f"解析数据失败: {e}")
        return []

# --------------------------
# 保存数据为 JSON 文件
# --------------------------

def save_to_json(data: dict, file_path: str):
    """
    将数据保存为JSON文件
    
    参数:
        data (dict): 要保存的数据
        file_path (str): 文件保存路径
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 以写入模式打开文件，使用UTF-8编码
        with open(file_path, 'w', encoding='utf-8') as f:
            # 使用indent参数美化输出，ensure_ascii=False确保中文字符正常显示
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"数据已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存文件失败: {e}")

# --------------------------
# 主程序：获取数据并保存到JSON
# --------------------------

if __name__ == "__main__":
    # 获取今日全球热门（所有类型）
    today_global = get_global_trending_cn(time_window="day", media_type="all")
    print(f"获取到 {len(today_global)} 条今日热门数据")
    
    # 获取本周全球热门（仅电影）
    week_global_movies = get_global_trending_cn(time_window="week", media_type="movie")
    print(f"获取到 {len(week_global_movies)} 条本周热门电影数据")
    
    # 创建要保存的数据结构
    data_to_save = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "today_global": today_global,
        "week_global_movies": week_global_movies
    }
    
    # 保存数据到JSON文件
    save_to_json(data_to_save, SAVE_PATH)
    
    # 控制台输出示例数据（可选）
    print("\n=== 今日热门（前10条） ===")
    if today_global:
        for idx, item in enumerate(today_global[:10], 1):
            print(f"{idx}. {item['title']} ({item['type']})")
    
    print("\n=== 本周热门（前10条） ===")
    if week_global_movies:
        for idx, item in enumerate(week_global_movies[:10], 1):
            print(f"{idx}. {item['title']} (评分: {item['rating']})")
