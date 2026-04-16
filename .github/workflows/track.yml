import os
import requests
import re
import urllib.parse
import traceback
from datetime import datetime, timezone, timedelta

# 设定北京时间
tz_bj = timezone(timedelta(hours=8))
now_obj = datetime.now(tz_bj)
today_date = now_obj.strftime("%Y-%m-%d")
now_full_str = now_obj.strftime("%Y-%m-%d %H:%M:%S")

def get_code_by_name(name):
    """通过股票名称模糊搜索代码 (腾讯智能搜索)"""
    name = name.strip()
    try:
        encoded_name = urllib.parse.quote(name)
        url = f"http://smartbox.gtimg.cn/s3/?v=2&q={encoded_name}&t=all"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if 'v_hint="' in resp.text:
            data = resp.text.split('v_hint="')[1].split('"')[0]
            if not data: return None
            first_match = data.split('^')[0]
            parts = first_match.split('~')
            if len(parts) >= 2:
                market = parts[0].lower()
                code = parts[1]
                if market in ['sh', 'sz']:
                    return market + code
    except:
        pass
    return None

def fetch_price(code):
    """获取实时股价 (腾讯财经 API)"""
    try:
        code = code.strip().lower()
        if code.isdigit() and len(code) == 6:
            code = ('sh' if code.startswith('6') else 'sz') + code
        url = f"http://qt.gtimg.cn/q={code}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        if '="' in resp.text:
            data_str = resp.text.split('="')[1]
            data_parts = data_str.split('~')
            if len(data_parts) > 3:
                return float(data_parts[3]), data_parts[1]
    except:
        pass
    return None, None

def process_file(filepath):
    filename = os.path.basename(filepath)
    stock_name = filename.replace('.md', '').strip()
    
    content = ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        with open(filepath, 'r', encoding='gbk') as f:
            content = f.read()

    # 1. 识别代码
    match = re.search(r'[Cc]ode[：:]?\s*(s[hz]\d{6}|\d{6})', content)
    code = match.group(1) if match else get_code_by_name(stock_name)
    
    if not code:
        print(f"❌ [{stock_name}] 识别失败。")
        return

    # 2. 获取现价
    price, real_name = fetch_price(code)
    if not price:
        print(f"❌ [{stock_name}] 行情抓取失败。")
        return

    # 3. 初始化逻辑 (文件为空或没有表格)
    if "| 交易进度 |" not in content:
        # 记录添加的日期和精确时间
        header = f"# {real_name} 10日追踪报告\n\n"
        header += f"Code: {code}\n"
        header += f"添加时间: {now_full_str}\n"
        header += f"初始锚定日: {today_date}\n"
        header += f"- **初始价格**: {price}\n\n"
        header += "| 交易进度 | 日期 | 当前价格 | 累计收益 |\n"
        header += "| :---: | :---: | :---: | :---: |\n"
        header += f"| 初始 | {today_date} | {price} | 0.00% |\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header)
        print(f"✨ [{real_name}] 已成功记录添加时间 {now_full_str} 并初始化。")
        return

    # 4. 追加记录逻辑
    if today_date in content:
        print(f"⏩ [{real_name}] 今日数据已存在，跳过。")
        return

    # 提取初始价格计算收益
    start_price_match = re.search(r'初始价格.*?([\d.]+)', content)
    if not start_price_match: return
    start_price = float(start_price_match.group(1))
    
    # 计算累计收益和天数
    lines = content.strip().split('\n')
    day_num = sum(1 for l in lines if '| 第' in l) + 1
    
    if day_num > 10:
        print(f"✅ [{real_name}] 10日追踪已完成。")
        return

    total_return = ((price - start_price) / start_price) * 100
    new_row = f"| 第 {day_num} 天 | {today_date} | {price} | **{total_return:+.2f}%** |"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n" + new_row)
    print(f"📈 [{real_name}] 已更新第 {day_num} 天数据。")

if __name__ == "__main__":
    folder = 'stocks'
    if not os.path.exists(folder): os.makedirs(folder)
    print(f"=== 启动追踪程序 (北京时间: {now_full_str}) ===")
    for filename in os.listdir(folder):
        if filename.endswith('.md'):
            try:
                process_file(os.path.join(folder, filename))
            except:
                traceback.print_exc()
    print("=== 执行完毕 ===")
