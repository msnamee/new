import os
import requests
import re
from datetime import datetime, timezone, timedelta

tz_bj = timezone(timedelta(hours=8))
today = datetime.now(tz_bj).strftime("%Y-%m-%d")

def fetch_price(code):
    try:
        url = f"https://hq.sinajs.cn/list={code}"
        headers = {"Referer": "http://finance.sina.com.cn/"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        data = resp.text.split('"')[1].split(',')
        return float(data[3]), data[0] # 返回现价和名称
    except:
        return None, None

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 从内容中寻找代码，格式如：Code: sh600519
    match = re.search(r'Code:\s*(s[hz]\d{6})', content)
    if not match: return
    code = match.group(1)

    # 2. 检查是否已经结束追踪 (满10行数据)
    lines = content.strip().split('\n')
    data_lines = [l for l in lines if '| 202' in l] # 统计带有日期的表格行
    if len(data_lines) >= 11: # 1行初始 + 10行追踪
        return 

    # 3. 获取实时价
    price, name = fetch_price(code)
    if not price: return

    # 4. 如果是新文件，初始化结构
    if "| 交易进度 |" not in content:
        header = f"# {name} 10日追踪报告\n\n"
        header += f"Code: {code}\n"
        header += f"- **初始锚定日**: {today}\n"
        header += f"- **初始价格**: {price}\n\n"
        header += "| 交易进度 | 日期 | 当前价格 | 累计收益 |\n"
        header += "| :---: | :---: | :---: | :---: |\n"
        header += f"| 初始 | {today} | {price} | 0.00% |\n"
        new_content = header
    else:
        # 防重复记录
        if today in content: return
        
        # 提取初始价格计算收益
        start_price_match = re.search(r'初始价格\*\*:\s*([\d.]+)', content)
        if not start_price_match: return
        start_price = float(start_price_match.group(1))
        
        total_return = ((price - start_price) / start_price) * 100
        day_num = len(data_lines)
        new_row = f"| 第 {day_num} 天 | {today} | {price} | **{total_return:+.2f}%** |\n"
        new_content = content.strip() + "\n" + new_row

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

# 扫描 stocks 文件夹
if __name__ == "__main__":
    if not os.path.exists('stocks'): os.makedirs('stocks')
    for filename in os.listdir('stocks'):
        if filename.endswith('.md'):
            process_file(os.path.join('stocks', filename))
