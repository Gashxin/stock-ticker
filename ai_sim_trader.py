# -*- coding: utf-8 -*-
"""
AI模拟交易追踪器 v2
================
- 自动计算现金
- 持仓+现金 = 总资产
- 自我检查机制
"""

import json
import urllib.request
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

STOCKS = {
    '000032': ('sz', '深桑达A'),
    '300486': ('sz', '东杰智能'),
    '002497': ('sz', '雅化集团'),
    '002176': ('sz', '江特电机'),
    '562910': ('sh', '高端制造'),
    '603501': ('sh', '豪威集团')
}

def get_price(code):
    market, _ = STOCKS.get(code, ('sz', code))
    url = f'https://qt.gtimg.cn/q={market}{code}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        parts = content.split('=')[1].strip(';').strip('"').split('~')
        return float(parts[3])
    except:
        return 0

def load_portfolio():
    with open('ai_sim_portfolio.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_portfolio(data):
    with open('ai_sim_portfolio.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calculate_total():
    """计算总资产 = 持仓市值 + 现金"""
    data = load_portfolio()
    
    # 持仓市值
    position_value = 0
    for acc, positions in data['positions'].items():
        for code, st in positions.items():
            price = get_price(code)
            if price > 0:
                position_value += price * st['shares']
    
    # 总资产 = 持仓 + 现金
    total = position_value + data.get('cash', 0)
    
    return {
        'position_value': position_value,
        'cash': data.get('cash', 0),
        'total': total,
        'start': data['start_value']
    }

def self_check():
    """自我检查"""
    result = calculate_total()
    issues = []
    
    # 检查1: 总资产应该大于现金
    if result['total'] < result['cash']:
        issues.append('错误: 总资产小于现金！')
    
    # 检查2: 收益率应该合理
    pnl = result['total'] - result['start']
    pnl_pct = pnl / result['start'] * 100
    if abs(pnl_pct) > 50:
        issues.append('警告: 收益率异常 (%.1f%%)' % pnl_pct)
    
    # 检查3: 现金为负数
    if result['cash'] < 0:
        issues.append('错误: 现金为负数！')
    
    return issues

def show_status():
    result = calculate_total()
    issues = self_check()
    
    print('='*70)
    print('AI模拟账户')
    print('='*70)
    print('起始: %.0f CNY' % result['start'])
    print('持仓市值: %.0f CNY' % result['position_value'])
    print('现金: %.0f CNY' % result['cash'])
    print('='*70)
    print('总资产: %.0f CNY' % result['total'])
    print('盈亏: %+.0f CNY (%+.2f%%)' % (result['total']-result['start'], (result['total']-result['start'])/result['start']*100))
    
    if issues:
        print('')
        print('⚠️ 自检问题:')
        for issue in issues:
            print('  - ' + issue)
    
    print('='*70)

if __name__ == '__main__':
    show_status()
