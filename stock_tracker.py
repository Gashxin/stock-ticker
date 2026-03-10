# -*- coding: utf-8 -*-
"""
股票收益跟踪器 - 个人私密记录
=====================================
功能: 记录每次交易，计算收益率
隐私: 仅本地存储，不对外分享

使用方法:
1. 首次设置: 导入持仓
2. 每次交易: 记录买入/卖出
3. 查看收益: 运行查看报告
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 数据存储路径
DATA_FILE = 'stock_portfolio.json'

# ==================== 数据结构 ====================

def load_data():
    """加载数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            'holdings': {},      # 当前持仓: {股票代码: {数量, 成本, 日期}}
            'trades': [],        # 历史交易记录
            'stats': {           # 统计信息
                'total_invested': 0,
                'total_value': 0,
                'total_profit': 0,
                'total_return_rate': 0,
                'winning_trades': 0,
                'losing_trades': 0,
            }
        }

def save_data(data):
    """保存数据"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== 交易操作 ====================

def add_holding(code, name, shares, cost_per_share, date=None):
    """添加持仓"""
    data = load_data()
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # 记录成本(如果是加仓，需要合并计算)
    if code in data['holdings']:
        old_shares = data['holdings'][code]['shares']
        old_cost = data['holdings'][code]['total_cost']
        new_shares = old_shares + shares
        new_cost = old_cost + (shares * cost_per_share)
        data['holdings'][code] = {
            'name': name,
            'shares': new_shares,
            'cost_per_share': new_cost / new_shares,
            'total_cost': new_cost,
            'start_date': data['holdings'][code]['start_date'],
            'update_date': date
        }
    else:
        data['holdings'][code] = {
            'name': name,
            'shares': shares,
            'cost_per_share': cost_per_share,
            'total_cost': shares * cost_per_share,
            'start_date': date,
            'update_date': date
        }
    
    # 记录交易
    data['trades'].append({
        'date': date,
        'type': '买入',
        'code': code,
        'name': name,
        'shares': shares,
        'price': cost_per_share,
        'amount': shares * cost_per_share
    })
    
    save_data(data)
    print(f"✅ 已添加持仓: {name} {shares}股 @ {cost_per_share}元")

def sell_holding(code, shares, price, date=None):
    """卖出持仓"""
    data = load_data()
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    if code not in data['holdings']:
        print(f"❌ 错误: 没有{code}的持仓")
        return
    
    holding = data['holdings'][code]
    
    if shares > holding['shares']:
        print(f"❌ 错误: 卖出数量超过持有数量")
        return
    
    # 计算收益
    cost = shares * holding['cost_per_share']
    revenue = shares * price
    profit = revenue - cost
    return_rate = profit / cost * 100
    
    # 记录交易
    trade = {
        'date': date,
        'type': '卖出',
        'code': code,
        'name': holding['name'],
        'shares': shares,
        'price': price,
        'amount': revenue,
        'cost': cost,
        'profit': profit,
        'return_rate': return_rate
    }
    data['trades'].append(trade)
    
    # 更新持仓
    if shares == holding['shares']:
        del data['holdings'][code']
    else:
        remaining = holding['shares'] - shares
        remaining_cost = holding['total_cost'] - cost
        data['holdings'][code] = {
            'name': holding['name'],
            'shares': remaining,
            'cost_per_share': remaining_cost / remaining,
            'total_cost': remaining_cost,
            'start_date': holding['start_date'],
            'update_date': date
        }
    
    save_data(data)
    
    print(f"✅ 已卖出: {holding['name']} {shares}股 @ {price}元")
    print(f"   收益: {profit:.2f}元 ({return_rate:+.2f}%)")

def update_price(code, current_price):
    """更新当前价格"""
    data = load_data()
    
    if code in data['holdings']:
        data['holdings'][code]['current_price'] = current_price
        data['holdings'][code]['current_value'] = current_price * data['holdings'][code]['shares']
        save_data(data)
        print(f"✅ 已更新价格: {code} = {current_price}元")

# ==================== 统计报告 ====================

def show_portfolio():
    """显示当前持仓"""
    data = load_data()
    
    print('\n' + '='*60)
    print('    📊 当前持仓')
    print('='*60)
    
    if not data['holdings']:
        print('  暂无持仓')
        return
    
    total_value = 0
    total_cost = 0
    
    for code, h in data['holdings'].items():
        current_price = h.get('current_price', h['cost_per_share'])
        current_value = current_price * h['shares']
        profit = current_value - h['total_cost']
        return_rate = profit / h['total_cost'] * 100 if h['total_cost'] > 0 else 0
        
        total_value += current_value
        total_cost += h['total_cost']
        
        direction = '↑' if profit >= 0 else '↓'
        
        print(f"\n  {h['name']} ({code})")
        print(f"    持股数: {h['shares']}股")
        print(f"    成本价: {h['cost_per_share']:.2f}元")
        print(f"    当前价: {current_price:.2f}元")
        print(f"    总成本: {h['total_cost']:.2f}元")
        print(f"    当前价值: {current_value:.2f}元")
        print(f"    浮动盈亏: {profit:.2f}元 ({direction}{abs(return_rate):.2f}%)")
    
    # 汇总
    total_profit = total_value - total_cost
    total_return_rate = total_profit / total_cost * 100 if total_cost > 0 else 0
    direction = '↑' if total_profit >= 0 else '↓'
    
    print('\n' + '-'*60)
    print(f"  总成本: {total_cost:.2f}元")
    print(f"  总价值: {total_value:.2f}元")
    print(f"  总盈亏: {total_profit:.2f}元 ({direction}{abs(total_return_rate):.2f}%)")
    print('='*60)

def show_trades():
    """显示历史交易"""
    data = load_data()
    
    print('\n' + '='*60)
    print('    📜 历史交易记录')
    print('='*60)
    
    if not data['trades']:
        print('  暂无交易记录')
        return
    
    # 按日期排序
    trades = sorted(data['trades'], key=lambda x: x['date'], reverse=True)
    
    for t in trades[:20]:  # 显示最近20条
        if t['type'] == '买入':
            print(f"\n  {t['date']} 买入 {t['name']}")
            print(f"    {t['shares']}股 @ {t['price']}元 = {t['amount']:.2f}元")
        else:
            direction = '↑' if t['profit'] >= 0 else '↓'
            print(f"\n  {t['date']} 卖出 {t['name']}")
            print(f"    {t['shares']}股 @ {t['price']}元 = {t['amount']:.2f}元")
            print(f"    收益: {t['profit']:.2f}元 ({direction}{abs(t['return_rate']):.2f}%)")

def show_stats():
    """显示统计报告"""
    data = load_data()
    
    # 计算已平仓交易的统计
    closed_trades = [t for t in data['trades'] if t['type'] == '卖出']
    
    if closed_trades:
        winning = [t for t in closed_trades if t['profit'] > 0]
        losing = [t for t in closed_trades if t['profit'] <= 0]
        
        total_profit = sum(t['profit'] for t in closed_trades)
        win_rate = len(winning) / len(closed_trades) * 100 if closed_trades else 0
        
        avg_win = sum(t['return_rate'] for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t['return_rate'] for t in losing) / len(losing) if losing else 0
    
    print('\n' + '='*60)
    print('    📈 收益统计')
    print('='*60)
    
    print(f"\n  已平仓交易: {len(closed_trades)}笔")
    print(f"  盈利交易: {len(winning) if closed_trades else 0}笔")
    print(f"  亏损交易: {len(losing) if closed_trades else 0}笔")
    print(f"  胜率: {win_rate:.1f}%")
    
    if winning:
        print(f"  平均盈利: +{avg_win:.2f}%")
    if losing:
        print(f"  平均亏损: {avg_loss:.2f}%")
    
    print(f"\n  已实现总收益: {total_profit:.2f}元")
    
    # 持仓盈亏
    holdings_value = 0
    holdings_cost = 0
    for h in data['holdings'].values():
        current_price = h.get('current_price', h['cost_per_share'])
        holdings_value += current_price * h['shares']
        holdings_cost += h['total_cost']
    
    floating_profit = holdings_value - holdings_cost
    
    print(f"  浮动盈亏: {floating_profit:.2f}元")
    print(f"  总盈亏: {total_profit + floating_profit:.2f}元")
    
    print('='*60)

# ==================== 主菜单 ====================

def main():
    import sys
    
    if len(sys.argv) < 2:
        print('''
股票收益跟踪器
==============

使用方法:
  python stock_tracker.py add <代码> <名称> <数量> <成本价>  - 添加持仓
  python stock_tracker.py sell <代码> <数量> <卖出价>        - 卖出
  python stock_tracker.py price <代码> <当前价>              - 更新价格
  python stock_tracker.py portfolio                             - 查看持仓
  python stock_tracker.py trades                               - 查看交易记录
  python stock_tracker.py stats                                - 查看统计报告
  python stock_tracker.py all                                  - 查看全部报告

示例:
  python stock_tracker.py add 000032 深桑达A 1000 18.50
  python stock_tracker.py sell 000032 500 20.00
  python stock_tracker.py price 000032 19.14
  python stock_tracker.py all
''')
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 6:
            print("用法: python stock_tracker.py add <代码> <名称> <数量> <成本价>")
            return
        code = sys.argv[2]
        name = sys.argv[3]
        shares = int(sys.argv[4])
        cost = float(sys.argv[5])
        add_holding(code, name, shares, cost)
    
    elif command == 'sell':
        if len(sys.argv) < 5:
            print("用法: python stock_tracker.py sell <代码> <数量> <卖出价>")
            return
        code = sys.argv[2]
        shares = int(sys.argv[3])
        price = float(sys.argv[4])
        sell_holding(code, shares, price)
    
    elif command == 'price':
        if len(sys.argv) < 4:
            print("用法: python stock_tracker.py price <代码> <当前价>")
            return
        code = sys.argv[2]
        price = float(sys.argv[3])
        update_price(code, price)
    
    elif command == 'portfolio':
        show_portfolio()
    
    elif command == 'trades':
        show_trades()
    
    elif command == 'stats':
        show_stats()
    
    elif command == 'all':
        show_portfolio()
        show_trades()
        show_stats()
    
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    main()
