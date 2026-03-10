# -*- coding: utf-8 -*-
"""
AI模拟交易追踪器
================
记录AI模拟盘操作和收益
与实盘对比比赛
"""

import json
import urllib.request
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# 股票代码映射
STOCKS = {
    '000032': ('sz', '深桑达A'),
    '002497': ('sz', '雅化集团'),
    '002176': ('sz', '江特电机'),
    '562910': ('sh', '高端制造'),
    '603501': ('sh', '豪威集团')
}

def get_price(code):
    """获取实时价格"""
    market, _ = STOCKS.get(code, ('sz', code))
    url = 'https://qt.gtimg.cn/q=' + market + code
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        parts = content.split('=')[1].strip(';').strip('"').split('~')
        return float(parts[3])
    except:
        return 0

def load_sim_portfolio():
    with open('ai_sim_portfolio.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_sim_portfolio(data):
    with open('ai_sim_portfolio.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_current_value():
    """获取模拟盘当前市值"""
    data = load_sim_portfolio()
    total = 0
    for acc, positions in data['positions'].items():
        for code, st in positions.items():
            price = get_price(code)
            if price > 0:
                total += price * st['shares']
    return total

def sim_buy(code, shares, price):
    """模拟买入"""
    data = load_sim_portfolio()
    trade = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'action': 'BUY',
        'code': code,
        'shares': shares,
        'price': price,
        'total': shares * price
    }
    data['trades'].append(trade)
    data['stats']['total_trades'] += 1
    save_sim_portfolio(data)
    return trade

def sim_sell(code, shares, price):
    """模拟卖出"""
    data = load_sim_portfolio()
    trade = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'action': 'SELL',
        'code': code,
        'shares': shares,
        'price': price,
        'total': shares * price
    }
    data['trades'].append(trade)
    data['stats']['total_trades'] += 1
    save_sim_portfolio(data)
    return trade

def show_status():
    """显示模拟盘状态"""
    data = load_sim_portfolio()
    current_value = get_current_value()
    start_value = data['start_value']
    pnl = current_value - start_value
    pnl_pct = pnl / start_value * 100
    
    print('='*70)
    print('AI模拟账户状态')
    print('='*70)
    print('起始日期:', data['start_date'])
    print('起始资金: %.0f CNY' % start_value)
    print('当前市值: %.0f CNY' % current_value)
    print('总盈亏: %+.0f CNY (%+.2f%%)' % (pnl, pnl_pct))
    print('')
    print('交易次数:', data['stats']['total_trades'])
    print('')
    
    # 持仓
    print('当前持仓:')
    for acc, positions in data['positions'].items():
        for code, st in positions.items():
            price = get_price(code)
            if price > 0:
                val = price * st['shares']
                print('  %s: %d x %.2f = %.0f' % (st['name'], st['shares'], price, val))
    
    # 交易记录
    if data['trades']:
        print('')
        print('交易记录:')
        for t in data['trades'][-5:]:
            print('  %s %s %d@%.2f' % (t['date'], t['action'], t['shares'], t['price']))
    
    print('='*70)
    
    # 对比实盘
    real_value = 850469  # 昨日市值
    real_pnl = current_value - real_value
    real_pnl_pct = real_pnl / real_value * 100
    
    print('')
    print('='*70)
    print('AI vs 实盘 对比')
    print('='*70)
    print('实盘起始: %.0f CNY (2026-03-10)' % real_value)
    print('AI起始:   %.0f CNY (2026-03-10)' % start_value)
    print('')
    print('实盘当前: %.0f CNY' % real_value)
    print('AI当前:   %.0f CNY' % current_value)
    print('')
    print('实盘盈亏: %+.0f CNY (%+.2f%%)' % (0, 0))
    print('AI盈亏:   %+.0f CNY (%+.2f%%)' % (pnl, pnl_pct))
    print('')
    if pnl > 0:
        print('*** AI领先 %.0f CNY ***' % pnl)
    elif pnl < 0:
        print('*** 落后实盘 %.0f CNY ***' % abs(pnl))
    else:
        print('*** 平局 ***')
    print('='*70)

if __name__ == '__main__':
    show_status()
