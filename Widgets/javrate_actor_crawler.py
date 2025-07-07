import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
import json
from datetime import datetime

# 伪装成真实浏览器的请求头
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
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

# 模拟人类操作延迟
def human_delay(min_sec=1, max_sec=3):
    """随机延迟，模拟人类操作"""
    time.sleep(random.uniform(min_sec, max_sec))

# 创建会话
def create_session():
    session = requests.Session()
    session.headers.update(get_headers())
    return session

# 获取页面内容
def get_page(session, url, max_retries=3):
    """获取页面内容，带重试机制"""
    for attempt in range(max_retries):
        try:
            human_delay(0.5, 2.0)  # 请求前延迟
            response = session.get(url, timeout=15)
            
            # 检查是否被重定向到验证页面
            if "Just a moment..." in response.text or "Checking if the site connection is secure" in response.text:
                print(f"检测到Cloudflare验证，尝试{attempt+1}/{max_retries}")
                human_delay(3, 8)  # 被检测时延长延迟
                continue
            
            # 检查内容长度是否合理
            if len(response.text) < 10000:
                print(f"返回内容过短（{len(response.text)}字符），可能被反爬，重试中...")
                human_delay(3, 6)
                continue
                
            response.raise_for_status()  # 检查HTTP状态码
            return response.text
        
        except Exception as e:
            print(f"请求失败 ({attempt+1}/{max_retries}): {str(e)}")
            human_delay(2, 5)  # 失败后延迟
    
    print(f"无法获取页面: {url}")
    return None

# 解析演员信息 - 针对新HTML结构优化
def parse_actors(html):
    """从HTML中解析演员信息"""
    if not html:
        return {}
    
    # 使用更可靠的html.parser替代lxml
    soup = BeautifulSoup(html, 'html.parser')
    actors_dict = {}
    
    # 直接使用特定的卡片选择器
    actor_cards = soup.select('div.actor-card')
    
    if not actor_cards:
        print("未找到演员卡片，尝试备用选择器")
        # 尝试其他可能的选择器
        actor_cards = soup.select('div.col-md-2.col-sm-3.col-xs-4.item')
    
    print(f"找到 {len(actor_cards)} 个演员卡片")
    
    for card in actor_cards:
        try:
            # 从a标签的title属性获取演员名称
            a_tag = card.find('a', href=True)
            name = a_tag.get('title', '').strip() if a_tag else None
            
            # 如果title属性没有名称，尝试从h3标签获取
            if not name or name == "未知":
                h3_tag = card.find('h3')
                if h3_tag:
                    # 提取纯文本内容，忽略svg图标
                    name = ''.join([text for text in h3_tag.stripped_strings if not text.startswith('<svg')]).strip()
            
            # 如果还是没有获取到名称，尝试从图片alt属性获取
            if not name or name == "未知":
                img_tag = card.find('img')
                if img_tag and img_tag.get('alt'):
                    name = img_tag['alt'].strip()
            
            # 确保名称有效
            if not name or name == "未知":
                print(f"无法确定名称: {card}")
                continue
                
            # 获取演员ID - 从href中提取UUID
            actor_id = None
            if a_tag and '/Actor/Detail/' in a_tag['href']:
                match = re.search(r'/Actor/Detail/([a-f0-9-]+)\.html', a_tag['href'])
                if match:
                    actor_id = match.group(1)
            
            # 备用方案：从图片URL提取ID
            if not actor_id:
                img_tag = card.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    img_src = img_tag['src']
                    match = re.search(r'/actor/([a-f0-9-]+)/', img_src)
                    if match:
                        actor_id = match.group(1)
            
            if actor_id:
                # 清理名称中的多余空格
                name = re.sub(r'\s+', '', name)
                print(f"✅ 添加成功: {name}, ID: {actor_id}")
                actors_dict[name] = actor_id
            else:
                print(f"无法提取ID: {name} - {a_tag['href'] if a_tag else '无链接'}")
                
        except Exception as e:
            print(f"解析卡片时出错: {str(e)}")
            continue
    
    return actors_dict

# 保存结果到JSON
def save_to_json(actors_dict, filepath):
    """将结果保存到JSON文件"""
    if not actors_dict:
        print("没有数据可保存")
        return False, 0
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(actors_dict, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filepath}")
        return True, len(actors_dict)
    except Exception as e:
        print(f"保存JSON文件时出错: {str(e)}")
        return False, 0

# 主函数
def main():
    start_time = time.time()  # 记录开始时间
    print("开始爬取演员信息...")
    session = create_session()
    
    all_actors = {}
    pages_to_scrape = 117  # 要爬取的页数
    total_actors_found = 0  # 总共找到的演员数量
    successful_pages = 0    # 成功处理的页面数量
    
    for page in range(1, pages_to_scrape + 1):
        print(f"\n{'='*40}")
        print(f"开始处理第 {page} 页")
        
        url = f"https://www.javrate.com/actor/list/1-0-{page}.html"
        html = get_page(session, url)
        
        if html:
            page_actors = parse_actors(html)
            if page_actors:
                # 记录本页找到的演员数量
                page_count = len(page_actors)
                total_actors_found += page_count
                
                # 增加成功页面计数
                successful_pages += 1
                
                # 合并到总字典
                all_actors.update(page_actors)
                print(f"第 {page} 页找到 {page_count} 位演员")
            else:
                print(f"第 {page} 页未找到演员信息")
        else:
            print(f"第 {page} 页获取失败")
        
        # 页面间延迟
        if page < pages_to_scrape:
            human_delay(3, 7)
    
    # 保存结果到JSON
    output_dir = "Widgets"
    filename = "javrate_actors.json"
    output_path = os.path.join(output_dir, filename)
    
    save_success, saved_count = save_to_json(all_actors, output_path)
    
    # 计算总耗时
    total_time = time.time() - start_time
    
    # 打印格式化摘要
    print("\n" + "=" * 12 + " 爬 取 结 果 统 计 " + "=" * 12)
    print(f"数 据 已 保 存 至 : {output_path}")
    print(f"原 始 数 据 量 : {total_actors_found} 条")
    print(f"JSON实 际 保 存 量 : {saved_count} 位演员")
    
    if save_success:
        print("数 据 保 存 成 功 ！")
    else:
        print("数 据 保 存 失 败 ！")
    
    print(f"总 耗 时 : {total_time:.2f} 秒")
    print("=" * 15 + " 爬 取 结 束 " + "=" * 15)

if __name__ == "__main__":
    main()