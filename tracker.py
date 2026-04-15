import json
import os
import requests
from datetime import datetime, timezone, timedelta

# 1. 严格设定北京时间 (UTC+8)
tz_beijing = timezone(timedelta(hours=8))
today_date = datetime.now(tz_beijing).strftime("%Y-%m-%d")

STATE_FILE = "state.json"
MD_FILE = "tracking.md"

def main():
    # 2. 读取配置面板
    if not os.path.exists(STATE_FILE):
        print(f"❌ 找不到 {STATE_FILE}文件。")
        return

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    if state.get("remaining_days", 0) <= 0:
        print("✅ 该股票10日追踪已完成，系统休眠中。如需追踪新股票，请在 state.json 中重置信息。")
        return

    code = state["code"]
    name = state["name"]
    start_price = state.get("start_price", 0)

    # 3. 通过新浪财经 API 获取今日实时收盘价
    try:
        url = f"https://hq.sinajs.cn/list={code}"
        headers = {"Referer": "http://finance.sina.com.cn/"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk' # 解决中文乱码
        parts = resp.text.split('"')[1].split(',')
        if len(parts) < 5:
            print("❌ 无法获取股票数据，请检查代码格式是否正确 (例如：sh600519, sz000001)")
            return
        current_price = float(parts[3])
    except Exception as e:
        print(f"❌ 网络请求或数据解析失败: {e}")
        return

    # 4. 如果是追踪的第一天 (初始价格为0)，则先锚定价格
    if start_price == 0:
        state["start_price"] = current_price
        state["start_date"] = today_date
        print(f"🎯 已锚定 {name} 初始追踪价格: {current_price}")
        # 写回 JSON 并生成初始表单，提前退出，不消耗追踪天数
        save_state_and_generate_md(state)
        return

    # 防呆设计：判断今天是否已经记录过
    if len(state["history"]) > 0 and state["history"][-1]["date"] == today_date:
        print("⚠️ 今天的收盘数据已经更新过，不再重复计算。")
        return

    # 5. 计算相对于初始价格的波段总涨幅
    total_return = ((current_price - start_price) / start_price) * 100

    # 6. 更新历史记录数组
    state["history"].append({
        "date": today_date,
        "price": current_price,
        "total_return": f"{total_return:+.2f}%"
    })
    
    # 7. 扣减剩余天数
    state["remaining_days"] -= 1
    
    save_state_and_generate_md(state)
    print(f"📊 {name} 今日更新成功，当前收益: {total_return:+.2f}%，剩余追踪天数: {state['remaining_days']}")

def save_state_and_generate_md(state):
    # 保存 JSON
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

    # 以标准表格形式生成 Markdown 报告
    md_content = "# 自动化股票10日波段表现追踪\n\n"
    md_content += f"### 📌 追踪标的: **{state['name']}** (`{state['code']}`)\n"
    md_content += f"- **起始日期**: {state['start_date']}\n"
    md_content += f"- **初始价格**: {state['start_price']}\n"
    md_content += f"- **剩余天数**: {state['remaining_days']} 天\n\n"

    md_content += "| 交易进度 | 日期 | 当前价格 | 累计收益率 (相对起始价格) |\n"
    md_content += "| :---: | :---: | :---: | :---: |\n"
    
    if state['start_price'] > 0:
        md_content += f"| 初始锚定 | {state['start_date']} | {state['start_price']} | 0.00% |\n"

    for i, item in enumerate(state["history"]):
        md_content += f"| 第 {i+1} 天 | {item['date']} | {item['price']} | **{item['total_return']}** |\n"

    # 保存 MD 文件
    with open(MD_FILE, "w", encoding="utf-8") as f:
        f.write(md_content)

if __name__ == "__main__":
    main()
