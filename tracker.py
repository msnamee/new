import os
import requests
import re
import urllib.parse
from datetime import datetime, timezone, timedelta

tz_bj = timezone(timedelta(hours=8))
today = datetime.now(tz_bj).strftime("%Y-%m-%d")

def get_code_by_name(name):
    """通过股票名称模糊搜索代码"""
    try:
        # 使用新浪搜索建议接口
        encoded_name = urllib.parse.quote(name)
        url = f"https://suggest3.sinajs.cn/suggest/type=&key={encoded_name}"
        resp = requests.get(url, timeout=10)
        # 结果格式: var suggestdata_1713187213454 = "宁德时代,11,300750,sz,宁德时代,,宁德时代,99";
        data = resp.text.split('"')[1]
        if not data: return None
        
        items = data.split(';')
        for item in items:
            parts = item.split(',')
            # 找到最匹配的一项，返回 交易所+代码 (如 sz300750)
            if parts[0] == name:
                return parts[3] + parts[2]
    except:
        return None

def fetch_price(code):
    """获取实时股价"""
    try:
        url = f"https://hq.sinajs.cn/list={code}"
        headers = {"Referer": "http://finance.sina.com.cn/"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        data = resp.text.split('"')[1].split(',')
        return float(data[3]), data[0]
    except:
        return None, None

def process_file(filepath):
    filename = os.path.basename(filepath)
    stock_name_from_file = filename.replace('.md', '')
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 识别代码：如果文件里没写代码，就用文件名去搜
    match = re.search(r'Code:\s*(s[hz]\d{6})', content)
    if match:
        code = match.group(1)
    else:
        code = get_code_by_name(stock_name_from_file)
    
    if not code:
        print(f"❌ 无法识别股票名称: {stock_name_from_file}")
        return

    # 2. 获取现价
    price, real_name = fetch_price(code)
    if not price: return

    # 3. 检查是否已经结束追踪 (满11行数据：1行初始+10行记录)
    lines = content.strip().split('\n')
    data_lines = [l for l in lines if '| 202' in l]
    if len(data_lines) >= 11: return

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
    else:
        if today in content: return
        
        start_price_match = re.search(r'初始价格\*\*:\s*([\d.]+)', content)
        if not start_price_match: return
        start_price = float(start_price_match.group(1))
        
        total_return = ((price - start_price) / start_price) * 100
        day_num = len(data_lines)
        new_row = f"| 第 {day_num} 天 | {today} | {price} | **{total_return:+.2f}%** |\n"
        new_content = content.strip() + "\n" + new_row

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    folder = 'stocks'
    if not os.path.exists(folder): os.makedirs(folder)
    for filename in os.listdir(folder):
        if filename.endswith('.md'):
            process_file(os.path.join(folder, filename))
