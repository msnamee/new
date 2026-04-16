import os
import requests
import re
import urllib.parse
import traceback
from datetime import datetime, timezone, timedelta

tz_bj = timezone(timedelta(hours=8))
today = datetime.now(tz_bj).strftime("%Y-%m-%d")

def get_code_by_name(name):
    """通过股票名称模糊搜索代码 (升级核心：采用腾讯智能搜索，彻底解决空白文件无法识别的问题)"""
    name = name.strip()
    try:
        encoded_name = urllib.parse.quote(name)
        # 腾讯智能搜索接口，联想能力极强
        url = f"http://smartbox.gtimg.cn/s3/?v=2&q={encoded_name}&t=all"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        
        # 腾讯返回格式示例: v_hint="sz~002060~广东建工~gdjg~...^sh~...
        if 'v_hint="' in resp.text:
            data = resp.text.split('v_hint="')[1].split('"')[0]
            if not data: return None
            
            # 截取第一个匹配项
            first_match = data.split('^')[0]
            parts = first_match.split('~')
            
            if len(parts) >= 2:
                market = parts[0].lower() # sz 或 sh
                code = parts[1]           # 002060
                if market in ['sh', 'sz']:
                    return market + code
    except Exception as e:
        print(f"⚠️ 腾讯搜索 {name} 代码时异常: {e}")
    return None

def fetch_price(code):
    """获取实时股价 (腾讯财经行情 API)"""
    try:
        code = code.strip().lower()
        if code.isdigit() and len(code) == 6:
            if code.startswith('6'): 
                code = 'sh' + code
            else: 
                code = 'sz' + code
                
        url = f"http://qt.gtimg.cn/q={code}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        
        if '="' in resp.text:
            data_str = resp.text.split('="')[1]
            data_parts = data_str.split('~')
            if len(data_parts) > 3:
                real_name = data_parts[1]
                current_price = float(data_parts[3])
                if current_price == 0.0 and len(data_parts) > 4:
                     current_price = float(data_parts[4])
                return current_price, real_name
    except Exception as e:
        print(f"⚠️ 腾讯接口获取行情异常 (代码:{code}): {e}")
    return None, None

def process_file(filepath):
    filename = os.path.basename(filepath)
    stock_name_from_file = filename.replace('.md', '').strip()
    
    content = ""
    try:
        # 如果是刚创建的完全空白文件，这里读出来的 content 就是 ""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"🔄 [{stock_name_from_file}] 检测到非 UTF-8 编码，自动切换 GBK 模式读取...")
        with open(filepath, 'r', encoding='gbk') as f:
            content = f.read()

    # 1. 识别代码：如果文件内容为空，正则必败，将直接走最新升级的 get_code_by_name(腾讯搜索)
    match = re.search(r'[Cc]ode[：:]?\s*(s[hz]\d{6}|\d{6})', content)
    if match:
        code = match.group(1)
    else:
        code = get_code_by_name(stock_name_from_file)
    
    if not code:
        print(f"❌ [{stock_name_from_file}] 无法识别股票代码，已跳过。请尝试在文件名加上代码，或在文件第一行写上 Code: 代码。")
        return

    # 2. 获取现价
    price, real_name = fetch_price(code)
    if not price:
        print(f"❌ [{stock_name_from_file}] 无法获取行情数据，已跳过。")
        return

    # 3. 检查是否追踪结束
    lines = content.strip().split('\n') if content.strip() else []
    data_lines = [l for l in lines if '|' in l and ('202' in l or '初始' in l)]
    if len(data_lines) >= 12: 
        print(f"✅ [{real_name}] 已完成追踪周期，不再更新。")
        return

    # 4. 构建/更新内容
    if "| 交易进度 |" not in content:
        header = f"# {real_name} 10日追踪报告\n\n"
        header += f"Code: {code}\n"
        header += f"- **初始价格**: {price}\n"
        header += f"- **追踪说明**: 系统根据文件名自动关联代码\n\n"
        header += "| 交易进度 | 日期 | 当前价格 | 累计收益 |\n"
        header += "| :---: | :---: | :---: | :---: |\n"
        header += f"| 初始 | {today} | {price} | 0.00% |\n"
        new_content = header
        print(f"✨ [{real_name}] 首次初始化追踪文档成功 (智能识别代码: {code})。")
    else:
        if today in content:
            print(f"⏩ [{real_name}] 今日数据 ({today}) 已存在，跳过。")
            return
        
        start_price_match = re.search(r'初始价格.*?([\d.]+)', content)
        if not start_price_match:
            print(f"❌ [{real_name}] 找不到初始价格数值，无法计算收益，已跳过！")
            return
            
        start_price = float(start_price_match.group(1))
        
        if start_price <= 0:
             print(f"❌ [{real_name}] 初始价格为 {start_price}，无法进行收益率运算，已跳过！")
             return
        
        total_return = ((price - start_price) / start_price) * 100
        day_num = sum(1 for l in lines if '| 第' in l) + 1
        new_row = f"| 第 {day_num} 天 | {today} | {price} | **{total_return:+.2f}%** |"
        new_content = content.strip() + "\n" + new_row
        print(f"📈 [{real_name}] 成功追加第 {day_num} 天收益记录 ({total_return:+.2f}%)。")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    folder = 'stocks'
    if not os.path.exists(folder): 
        os.makedirs(folder)
    
    print(f"=== 启动收盘追踪程序 (北京时间: {today}) ===")
    
    md_files = [f for f in os.listdir(folder) if f.endswith('.md')]
    
    if not md_files:
         print("📭 stocks 目录下没有找到任何 .md 文件。")
    
    for filename in md_files:
        filepath = os.path.join(folder, filename)
        try:
            process_file(filepath)
        except Exception as e:
            print(f"🚨 严重异常！在处理 [{filename}] 时发生崩溃：")
            traceback.print_exc()
            print("-" * 40)
            
    print("=== 追踪程序执行完毕 ===")
