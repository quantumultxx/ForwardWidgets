import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
import json
from datetime import datetime
import pytz

ACTOR_SELECTORS = [
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

OUTPUT_DIR = "data"

def get_headers():
    """生成请求头"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "identity, gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "https://www.javrate.com/"
    }

def create_session():
    session = requests.Session()
    session.headers.update(get_headers())
    return session

def get_page(session, url):
    time.sleep(random.uniform(1, 3))
    response = session.get(url, timeout=10)
    return response.text

def parse_actors(html):
    soup = BeautifulSoup(html, 'html.parser')
    actors = {}
    
    for selector in ACTOR_SELECTORS:
        actor_cards = soup.select(selector)
        if actor_cards:
            break
    
    for card in actor_cards:
        name = extract_actor_name(card)
        if not name:
            continue
            
        actor_id = extract_actor_id(card)
        if not actor_id:
            continue
            
        clean_name = re.sub(r'\s+', ' ', name).strip()
        actors[clean_name] = actor_id
    
    return actors

def extract_actor_name(card):
    a_tag = card.find('a', href=True)
    if a_tag and a_tag.get('title'):
        return a_tag['title'].strip()
    
    h3_tag = card.find('h3')
    if h3_tag:
        texts = [t.strip() for t in h3_tag.stripped_strings]
        return ' '.join(texts) if texts else None
    
    img_tag = card.find('img')
    if img_tag and img_tag.get('alt'):
        return img_tag['alt'].strip()
    
    return None

def extract_actor_id(card):
    a_tag = card.find('a', href=True)
    if a_tag and '/Actor/Detail/' in a_tag['href']:
        match = re.search(r'/Actor/Detail/([a-f0-9-]+)\.html', a_tag['href'])
        if match:
            return match.group(1)
    
    img_tag = card.find('img')
    if img_tag and 'src' in img_tag.attrs:
        match = re.search(r'/actor/([a-f0-9-]+)/', img_tag['src'])
        if match:
            return match.group(1)
    
    return None

def save_to_json(data, filepath):
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

def main():
    start_time = time.time()
    
    session = create_session()
    all_actors = {}
    total_pages = 150
    success_pages = 0
    total_actors = 0
    
    for page in range(1, total_pages + 1):
        url = f"https://www.javrate.com/actor/list/1-0-{page}.html"
        html = get_page(session, url)
        page_actors = parse_actors(html)
        
        if page_actors:
            page_count = len(page_actors)
            total_actors += page_count
            success_pages += 1
            all_actors.update(page_actors)
            print(f"第 {page} 页: 找到 {page_count} 位演员")
            
            if page_count < 24:
                print(f"第 {page} 页演员数量少于24个，停止")
                break
        
        time.sleep(random.uniform(1, 3))
    
    output_path = os.path.join(OUTPUT_DIR, "javrate_actors.json")
    save_to_json(all_actors, output_path)
    
    total_time = time.time() - start_time
    print("\n" + "=" * 40)
    print("统计报告：")
    print(f"目标页面数: {total_pages}")
    print(f"成功处理页面数: {success_pages}")
    print(f"总找到演员数: {total_actors}")
    print(f"实际保存数量: {len(all_actors)}")
    print(f"输出路径: {output_path}")
    print(f"总耗时: {total_time:.2f} 秒")
    print("=" * 40)

if __name__ == "__main__":
    main()