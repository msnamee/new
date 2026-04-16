import os
import requests
import re
import urllib.parse
from datetime import datetime, timezone, timedelta

tz_bj = timezone(timedelta(hours=8))
today = datetime.now(tz_bj).strftime("%Y-%m-%d")

def get_code_by_name(name):
    """通过股票名称模糊搜索代码"""
    name = name.strip()
    try:
        encoded_name = urllib.parse.quote(name)
        url = f"https://suggest3.sinajs.cn/suggest/type=&key={encoded_name}"
        # 修复：增加 User-Agent 防止被新浪反爬虫机制拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.text.split('"')[1]
        if not data: return None
        
        items = data.split(';')
        for item in items:
            parts = item.split(',')
            # 修复：容错匹配，只要名字包含在内即算成功，并确保市场代码正确
            if len(parts) > 4 and (name in parts[0] or name in parts[4]):
                market = parts[3].lower()
                if market in ['sh', 'sz']:
                    return market + parts[2]
    except Exception as e:
        print(f"⚠️ 搜索 {name} 代码时异常: {e}")
    return None

def fetch_price(code):
    """获取实时股价"""
    try:
        code = code.strip().lower()
        # 修复：兼容用户只写了6位纯数字的情况，自动补全前缀
        if code.isdigit() and len(code) == 6:
            if code.startswith('6'): 
                code = 'sh' + code
            else: 
                code = 'sz' + code
                
        url = f"https://hq.sinajs.cn/list={code}"
        # 修复：必须携带完整的 User-Agent 和 Referer
        headers = {
            "Referer": "http://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        data = resp.text.split('"')[1].split(',')
        
        if len(data) > 3:
            return float(data[3]), data[0]
    except Exception as e:
        print(f"⚠️ 获取行情数据异常 (代码:{code}): {e}")
    return None, None

def process_file(filepath):
    filename = os.path.basename(filepath)
    stock_name_from_file = filename.replace('.md', '').strip()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 识别代码：正则放宽，支持大小写、中英文冒号、无前缀纯数字
    match = re.search(r'[Cc]ode[：:]?\s*(s[hz]\d{6}|\d{6})', content)
    if match:
        code = match.group(1)
    else:
        code = get_code_by_name(stock_name_from_file)
    
    if not code:
        print(f"❌ [{stock_name_from_file}] 无法识别股票代码，已跳过。")
        return

    # 2. 获取现价
    price, real_name = fetch_price(code)
    if not price:
        print(f"❌ [{stock_name_from_file}] 无法获取新浪行情数据(请求代码:{code})，已跳过。")
        return

    # 3. 检查是否已经结束追踪 (满11行数据：1行初始+10行记录)
    lines = content.strip().split('\n')
    # 修复：更宽松的表格行定位方式
    data_lines = [l for l in lines if '|' in l and ('202' in l or '初始' in l)]
    if len(data_lines) >= 12: 
        print(f"✅ [{real_name}] 已完成追踪周期，不再更新。")
        return

    # 4. 构建/更新内容
    if "| 交易进度 |" not in content:
        # 初始化新文件
        header = f"# {real_name} 10日追踪报告\n\n"
        header += f"Code: {code}\n"
        header += f"- **初始价格**: {price}\n"
        header += f"- **追踪说明**: 系统根据文件名自动关联代码\n\n"
        header += "| 交易进度 | 日期 | 当前价格 | 累计收益 |\n"
        header += "| :---: | :---: | :---: | :---: |\n"
        header += f"| 初始 | {today} | {price} | 0.00% |\n"
        new_content = header
        print(f"✨ [{real_name}] 首次初始化追踪文档成功。")
    else:
        if today in content:
            print(f"⏩ [{real_name}] 今日数据 ({today}) 已存在，跳过。")
            return
        
        # 修复：增强正则，即使人为不小心删除了**星号，也能提取到初始价格
        start_price_match = re.search(r'初始价格.*?([\d.]+)', content)
        if not start_price_match:
            print(f"❌ [{real_name}] 找不到初始价格数值，无法计算收益，已跳过！")
            return
            
        start_price = float(start_price_match.group(1))
        
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
    for filename in os.listdir(folder):
        if filename.endswith('.md'):
            process_file(os.path.join(folder, filename))
    print("=== 追踪程序执行完毕 ===")
