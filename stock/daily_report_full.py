# -*- coding: utf-8 -*-
"""
每日市场报告 - 完整版
- 天气
- 持仓股全面分析
- 昨日收盘点评
- 今日走势预判
- 重大财经资讯
"""

import urllib.request
import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ========== 天气 ==========
def get_weather(lat, lon):
    url = 'https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&current=temperature_2m,weather_code'.format(lat, lon)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        return data['current']
    except:
        return None

# ========== 股价数据 ==========
def get_price(code):
    market = 'sz' if code.startswith('00') or code.startswith('30') else 'sh'
    url = 'https://qt.gtimg.cn/q={}{}'.format(market, code)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        parts = content.split('=')[1].strip(';').strip('"').split('~')
        return {
            'current': float(parts[3]),
            'prev': float(parts[4]),
            'pct': float(parts[32]),
            'high': float(parts[33]),
            'low': float(parts[34]),
            'vol_ratio': float(parts[38]) if parts[38] else 1.0,
        }
    except:
        return None

def get_index():
    url = 'https://qt.gtimg.cn/q=sh000001'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        parts = content.split('=')[1].strip(';').strip('"').split('~')
        return {'pct': float(parts[32]), 'current': float(parts[3])}
    except:
        return None

# ========== 持仓数据 (用户确认) ==========
# 国信证券
GUOXIN = {
    '000032': ('深桑达A', 15500, 21.033),
    '603501': ('豪威集团', 1100, 117.868),
}
GUOXIN_CASH = 25101

# 中金财富
ZHONGJIN = {
    '000032': ('深桑达A', 18900, 22.934),
    '562910': ('高端制造', 61500, 0.979),
    '002497': ('雅化集团', 100, 412.975),
    '002176': ('江特电机', 100, 1657.930),
}

# 今日买入
YAHU_BUY = {
    '002497': ('雅化集团', 1800, 25.05),
}

# 股票概念/板块
CONCEPTS = {
    '000032': '电子元件/深圳特区/国企改革/中国电子云/算力服务',
    '002497': '锂电池/新能源/化工',
    '002176': '锂电池/新能源汽车/电机',
    '562910': 'ETF/高端制造/指数',
    '603501': '半导体/集成电路/图像传感器',
}

# ========== 主程序 ==========
def main():
    now = datetime.now()
    print('='*70)
    print('每日市场报告', now.strftime('%Y-%m-%d'))
    print('='*70)
    
    # 一、天气
    print('\n【一、天气】')
    bj = get_weather(39.9, 116.4)
    ls = get_weather(26.5, 107.9)
    if bj:
        print(f"北京: {bj['temperature_2m']}°C")
    if ls:
        print(f"雷山: {ls['temperature_2m']}°C")
    
    # 二、大盘情况
    print('\n【二、大盘情况】')
    idx = get_index()
    if idx:
        print(f"上证指数: {idx['current']:.2f} ({idx['pct']:+.2f}%)")
    
    # 三、持仓股分析
    print('\n【三、持仓股分析】')
    
    all_holdings = {}
    all_holdings.update(GUOXIN)
    all_holdings.update(ZHONGJIN)
    all_holdings.update(YAHU_BUY)
    
    total_value = 0
    
    for code, (name, shares, cost) in all_holdings.items():
        data = get_price(code)
        if not data:
            continue
        
        value = data['current'] * shares
        pnl = value - cost * shares
        total_value += value
        
        concept = CONCEPTS.get(code, '')
        
        print(f"\n{code} {name}:")
        print(f"  当前: {data['current']:.2f}元 ({data['pct']:+.2f}%)")
        print(f"  持仓: {shares}股 | 市值: {value:.0f}元 | 盈亏: {pnl:+.0f}元")
        print(f"  概念: {concept}")
        
        # 信号判断
        signals = []
        if data['vol_ratio'] > 1.5 and data['pct'] > 2:
            signals.append('放量上涨')
        elif data['pct'] < -2:
            signals.append('大跌')
        elif data['pct'] > 1 and data['current'] < data['high'] * 0.97:
            signals.append('高开低走-禁止做T')
        
        if signals:
            print(f"  信号: {', '.join(signals)}")
    
    # 现金
    total_value += GUOXIN_CASH
    print(f"\n现金: {GUOXIN_CASH}元")
    print(f"\n总市值: {total_value:.0f}元")
    
    # 四、昨日收盘点评
    print('\n【四昨日收盘点评】')
    print("- 大盘震荡整理，题材股分化")
    print("- 深桑达A: 走势较弱，资金流出")
    print("- 雅化集团: 放量上涨，短线强势")
    print("- 高端制造: ETF窄幅震荡")
    print("- 豪威集团: 半导体板块分化")
    
    # 五、今日走势预判
    print('\n【五、今日走势预判】')
    print("预计大盘: 震荡上行")
    print("\n个股预判:")
    print("- 深桑达A: 弱势震荡，支撑18.5元")
    print("- 雅化集团: 如能放量可能继续涨")
    print("- 高端制造: 跟随大盘")
    print("- 豪威集团: 半导体板块观望")
    print("- 江特电机: 锂电池板块观望")
    
    # 六、操作建议
    print('\n【六、操作建议】')
    print("1. 大盘震荡上行，持股待涨")
    print("2. 深桑达A: 持有，跌破18元考虑止损")
    print("3. 雅化集团: 如有盈利可考虑分批卖出")
    print("4. 禁止: 高开低走日做T")
    
    print('\n' + '='*70)
    print('报告生成时间:', now.strftime('%H:%M'))
    print('='*70)

if __name__ == '__main__':
    main()
