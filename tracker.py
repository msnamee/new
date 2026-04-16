import os
import requests
import re
import urllib.parse
from datetime import datetime, timezone, timedelta

tz_bj = timezone(timedelta(hours=8))
today = datetime.now(tz_bj).strftime("%Y-%m-%d")

def get_code_by_name(name):
    """通过股票名称模糊搜索代码 (备用新浪搜索)"""
    name = name.strip()
    try:
        encoded_name = urllib.parse.quote(name)
        url = f"https://suggest3.sinajs.cn/suggest/type=&key={encoded_name}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.text.split('"')[1]
        if not data: return None
        
        items = data.split(';')
        for item in items:
            parts = item.split(',')
            if len(parts) > 4 and (name in parts[0] or name in parts[4]):
                market = parts[3].lower()
                if market in ['sh', 'sz']:
                    return market + parts[2]
    except Exception as e:
        print(f"⚠️ 搜索 {name} 代码时异常: {e}")
    return None

def fetch_price(code):
    """
    获取实时股价 (核心升级：改用腾讯财经 API，防止 GitHub Actions IP 被拦截)
    接口格式：http://qt.gtimg.cn/q=sh600519
    """
    try:
        code = code.strip().lower()
        # 兼容只写了6位纯数字的情况，自动补全前缀
        if code.isdigit() and len(code) == 6:
            if code.startswith('6'): 
                code = 'sh' + code
            else: 
                code = 'sz' + code
                
        url = f"http://qt.gtimg.cn/q={code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        
        # 腾讯接口返回示例: v_sh600519="1~贵州茅台~600519~1650.00~1660.00~...";
        if '="' in resp.text:
            data_str = resp.text.split('="')[1]
            data_parts = data_str.split('~')
            
            # data_parts[1] 是名称，data_parts[3] 是当前价格
            if len(data_parts) > 3:
                real_name = data_parts[1]
                current_price = float(data_parts[3])
                
                # 如果当前价格为0 (可能是停牌)，尝试取昨日收盘价 data_parts[4]
                if current_price == 0.0 and len(data_parts) > 4:
