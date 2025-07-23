import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
import json
from datetime import datetime
import pytz

# ==================== 配置参数 ====================
ACTOR_SELECTORS = [  # 演员卡片选择器优先级列表
    'div.actor-card',
    'div.col-md-2.col-sm-3.col-xs-4.item',
    'div.grid-item.actor',
    '[class*="actor-card"]'
]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
]
RETRY_DELAY_RANGE = (1, 3)   # 重试延迟范围（秒）
PAGE_DELAY_RANGE = (1, 3)    # 页面间延迟范围（秒）
TIMEOUT = 10                 # 请求超时时间（秒）
MAX_RETRIES = 3              # 最大重试次数
OUTPUT_DIR = "data"          # 输出目录

# ==================== 核心功能 ====================
def get_headers():
    """生成随机User-Agent的请求头（禁用Brotli压缩）"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "identity, gzip, deflate",  # 禁用Brotli
        "Connection": "keep-alive",
        "Referer": "https://www.javrate.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache"
    }

def human_delay(min_sec=1, max_sec=3):
    """随机延迟模拟人类操作"""
    time.sleep(random.uniform(min_sec, max_sec))

def create_session():
    """创建带请求头的会话"""
    session = requests.Session()
    session.headers.update(get_headers())
    return session

def get_page(session, url, max_retries=MAX_RETRIES):
    """获取页面内容"""
    for attempt in range(max_retries):
        try:
            human_delay(*PAGE_DELAY_RANGE)
            
            response = session.get(url, timeout=TIMEOUT)

            # 直接使用response.text（自动处理gzip/deflate）
            html = response.text
            
            # 验证内容完整性（检查关键选择器是否存在）
            soup = BeautifulSoup(html, 'html.parser')
            if not any(soup.select(selector) for selector in ACTOR_SELECTORS):
                raise ValueError("页面缺少演员卡片元素（可能内容不完整或结构变化）")
            
            return html

        except requests.exceptions.HTTPError as e:
            print(f"[请求失败] HTTP错误: {str(e)} (尝试 {attempt+1}/{max_retries})")
        except requests.exceptions.Timeout:
            print(f"[请求失败] 请求超时: {str(e)} (尝试 {attempt+1}/{max_retries})")
        except UnicodeDecodeError as e:
            print(f"[解码失败] 字符编码错误: {str(e)} (尝试 {attempt+1}/{max_retries})")
        except ValueError as e:
            print(f"[内容错误] {str(e)} (尝试 {attempt+1}/{max_retries})")
        except Exception as e:
            print(f"[请求失败] 未知错误: {str(e)} (尝试 {attempt+1}/{max_retries})")

        if attempt < max_retries - 1:
            human_delay(RETRY_DELAY_RANGE[0], RETRY_DELAY_RANGE[1])

    print(f"[最终失败] 无法获取页面: {url}")
    return None

def parse_actors(html):
    """解析演员信息"""
    if not html:
        print("[解析错误] 传入的HTML内容为空")
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    actors = {}

    # 遍历所有可能的选择器尝试匹配
    for selector in ACTOR_SELECTORS:
        actor_cards = soup.select(selector)
        if actor_cards:
            break
    else:
        print("[解析] 所有选择器均未找到候选卡片")
        return {}

    for idx, card in enumerate(actor_cards, 1):
        try:
            # 提取演员名称（多级 fallback）
            name = extract_actor_name(card)
            if not name or name.strip().lower() == "unknown":
                print(f"[解析警告] 卡片 {idx} 名称无效，跳过")
                continue

            # 提取演员ID（多级 fallback）
            actor_id = extract_actor_id(card)
            if not actor_id:
                print(f"[解析警告] 卡片 {idx} ID无效: {name}")
                continue

            # 清理名称（去除多余空格和特殊符号）
            clean_name = re.sub(r'\s+', ' ', name).strip()
            actors[clean_name] = actor_id
            print(f"✅ 添加成功{idx}: {clean_name} (ID: {actor_id})")

        except Exception as e:
            print(f"[解析错误] 卡片 {idx} 处理失败: {str(e)}")
            continue

    return actors

def extract_actor_name(card):
    """多级提取演员名称"""
    # 优先从a标签的title属性获取
    a_tag = card.find('a', href=True)
    if a_tag and a_tag.get('title'):
        return a_tag['title'].strip()

    # 其次从h3标签获取（去除SVG干扰）
    h3_tag = card.find('h3')
    if h3_tag:
        texts = [t.strip() for t in h3_tag.stripped_strings if not t.startswith('<svg')]
        return ' '.join(texts) if texts else None

    # 最后从图片alt属性获取
    img_tag = card.find('img')
    if img_tag and img_tag.get('alt'):
        return img_tag['alt'].strip()

    return None

def extract_actor_id(card):
    """多级提取演员ID"""
    # 从a标签的href提取（优先）
    a_tag = card.find('a', href=True)
    if a_tag and '/Actor/Detail/' in a_tag['href']:
        match = re.search(r'/Actor/Detail/([a-f0-9-]+)\.html', a_tag['href'])
        if match:
            return match.group(1)

    # 从图片src提取（备用）
    img_tag = card.find('img')
    if img_tag and 'src' in img_tag.attrs:
        match = re.search(r'/actor/([a-f0-9-]+)/', img_tag['src'])
        if match:
            return match.group(1)

    return None

def save_to_json(data, filepath):
    """保存数据到JSON文件"""
    if not data:
        print("[保存错误] 无有效数据可保存")
        return False, 0

    try:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        beijing_time = datetime.now(beijing_tz)
        last_updated = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
        
        output_data = {
            "last_updated": last_updated,
            "total_count": len(data),
            "actors": data
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        return True, len(data)
    except Exception as e:
        print(f"[保存错误] 文件写入失败: {str(e)}")
        return False, 0

# ==================== 主流程 ====================
def main():
    start_time = time.time()
    print("=" * 35)
    print("启动演员信息爬取程序")
    print("=" * 35)

    session = create_session()
    all_actors = {}
    total_pages = 150  # 根据需求调整目标页数
    success_pages = 0
    total_actors = 0

    for page in range(1, total_pages + 1):
        print(f"\n 开始处理第 {page} 页")
        url = f"https://www.javrate.com/actor/list/1-0-{page}.html"
        html = get_page(session, url)

        if not html:
            print(f"第 {page} 页获取失败，跳过")
            continue

        page_actors = parse_actors(html)
        if page_actors:
            page_count = len(page_actors)
            total_actors += page_count
            success_pages += 1
            all_actors.update(page_actors)
            print(f"第 {page} 页解析完成，找到 {page_count} 位演员")
        # 如果当前页演员数量少于24个，认为是最后一页
            if page_count < 24:
                print(f"第 {page} 页演员数量({page_count})少于24个，认为已到达最后一页，停止爬取")
                break
        else:
            print(f"第 {page} 页未找到有效演员信息")

        human_delay(*PAGE_DELAY_RANGE)

    # 保存最终结果
    output_path = os.path.join(OUTPUT_DIR, "javrate_actors.json")
    save_success, saved_count = save_to_json(all_actors, output_path)

    # 统计报告
    total_time = time.time() - start_time
    print("\n" + "=" * 35)
    print("爬取任务结束，统计报告：")
    print(f"目标页面数: {total_pages}")
    print(f"成功处理页面数: {success_pages}")
    print(f"总找到演员数: {total_actors}")
    print(f"实际保存数量: {saved_count}")
    print(f"输出路径: {output_path}")
    print(f"总耗时: {total_time:.2f} 秒")
    print("=" * 35)

    if save_success:
        print("[最终结果] 数据保存成功！")
    else:
        print("[最终结果] 数据保存失败！")

if __name__ == "__main__":
    main()
