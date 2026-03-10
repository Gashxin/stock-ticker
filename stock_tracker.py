# -*- coding: utf-8 -*-
"""
股票收益跟踪器 - 个人私密记录 v3.0
=====================================
功能: 记录每次交易，计算收益率
     记录交易时间，用于统计指导收益

使用方法:
  python stock_tracker.py                    - 查看全部
  python stock_tracker.py add 账户 代码 名称 数量 成本价    - 添加持仓
  python stock_tracker.py sell 账户 代码 数量 卖出价       - 卖出
  python stock_tracker.py price 代码 当前价                 - 更新价格
  python stock_tracker.py guide 账户 代码 数量 价格 方向   - 记录指导交易
"""

import json
import os
import sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_FILE = 'stock_portfolio.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {'accounts': {}, 'guides': [], 'stats': {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== 持仓操作 ====================

def add_holding(account, code, name, shares, cost_per_share, date=None):
    data = load_data()
    if account not in data['accounts']:
        data['accounts'][account] = {'holdings': {}, 'trades': []}
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    holdings = data['accounts'][account]['holdings']
    
    if code in holdings:
        old = holdings[code]
        new_shares = old['shares'] + shares
        new_cost = old['total_cost'] + shares * cost_per_share
        holdings[code] = {
            'name': name, 'code': code,
            'shares': new_shares,
            'cost_per_share': round(new_cost / new_shares, 2),
            'total_cost': round(new_cost, 2),
            'start_date': old['start_date'], 'update_date': date
        }
    else:
        holdings[code] = {
            'name': name, 'code': code,
            'shares': shares, 'cost_per_share': cost_per_share,
            'total_cost': round(shares * cost_per_share, 2),
            'start_date': date, 'update_date': date
        }
    
    data['accounts'][account]['trades'].append({
        'date': date, 'type': '买入', 'code': code, 'name': name,
        'shares': shares, 'price': cost_per_share, 'amount': round(shares * cost_per_share, 2)
    })
    
    save_data(data)
    print(f"[OK] Added: {account} {name} ({code}) {shares} @ {cost_per_share}")

def sell_holding(account, code, shares, price, date=None):
    data = load_data()
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    if code not in data['accounts'][account]['holdings']:
        print(f"[Error] No position for {code}")
        return
    
    h = data['accounts'][account]['holdings'][code]
    if shares > h['shares']:
        print(f"[Error] Sell amount exceeds holding")
        return
    
    cost = shares * h['cost_per_share']
    revenue = shares * price
    profit = revenue - cost
    return_rate = profit / cost * 100
    
    data['accounts'][account]['trades'].append({
        'date': date, 'type': '卖出', 'code': code, 'name': name,
        'shares': shares, 'price': price, 'amount': round(revenue, 2),
        'cost': round(cost, 2), 'profit': round(profit, 2), 'return_rate': round(return_rate, 2)
    })
    
    if shares == h['shares']:
        del data['accounts'][account]['holdings'][code]
    else:
        remaining = h['shares'] - shares
        remaining_cost = h['total_cost'] - cost
        data['accounts'][account]['holdings'][code] = {
            'name': name, 'code': code, 'shares': remaining,
            'cost_per_share': round(remaining_cost / remaining, 2),
            'total_cost': round(remaining_cost, 2),
            'start_date': h['start_date'], 'update_date': date
        }
    
    save_data(data)
    print(f"[OK] Sold: {account} {name} {shares} @ {price}, P/L: {profit:.2f} ({return_rate:+.2f}%)")

# ==================== 指导记录 ====================

def add_guide(account, code, name, shares, price, direction, date=None):
    """记录指导交易"""
    data = load_data()
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    guide = {
        'date': date, 'account': account, 'code': code, 'name': name,
        'shares': shares, 'price': price, 'direction': direction,
        'status': 'pending', 'result_price': None, 'result_date': None
    }
    
    if 'guides' not in data:
        data['guides'] = []
    data['guides'].append(guide)
    save_data(data)
    print(f"[OK] Guide recorded: {account} {name} {direction} {shares} @ {price}")

def update_guide(code, result_price, result_date=None):
    """更新指导结果"""
    data = load_data()
    if result_date is None:
        result_date = datetime.now().strftime('%Y-%m-%d')
    
    for g in data.get('guides', []):
        if g['code'] == code and g['status'] == 'pending':
            g['status'] = 'completed'
            g['result_price'] = result_price
            g['result_date'] = result_date
    
    save_data(data)
    print(f"[OK] Guide updated: {code} result @ {result_price}")

# ==================== 显示报告 ====================

def show_portfolio():
    data = load_data()
    
    print('='*70)
    print('PORTFOLIO REPORT')
    print('='*70)
    
    total_inv = 0
    total_val = 0
    
    for acc, ad in data['accounts'].items():
        h = ad.get('holdings', {})
        if not h: continue
        
        print(f'\n--- {acc} ---')
        
        for code, st in h.items():
            cp = st.get('current_price', st['cost_per_share'])
            cv = cp * st['shares']
            pl = cv - st['total_cost']
            rr = pl / st['total_cost'] * 100 if st['total_cost'] > 0 else 0
            total_inv += st['total_cost']
            total_val += cv
            
            s = '+' if pl >= 0 else ''
            print(f"{st['name']} ({code})")
            print(f"  Shares: {st['shares']} | Cost: {st['cost_per_share']} -> Now: {cp}")
            print(f"  Value: {cv:.2f} | P/L: {s}{pl:.2f} ({s}{rr:.2f}%)")
    
    tp = total_val - total_inv
    tr = tp / total_inv * 100 if total_inv > 0 else 0
    s = '+' if tp >= 0 else ''
    
    print('\n' + '='*70)
    print(f"Total Cost: {total_inv:.2f}")
    print(f"Total Value: {total_val:.2f}")
    print(f"Total P/L: {s}{tp:.2f} ({s}{tr:.2f}%)")
    print('='*70)

def show_guides():
    """显示指导记录"""
    data = load_data()
    guides = data.get('guides', [])
    
    print('='*70)
    print('TRADING GUIDES')
    print('='*70)
    
    if not guides:
        print("No guides yet")
        return
    
    for g in sorted(guides, key=lambda x: x['date'], reverse=True):
        status = '[Pending]' if g['status'] == 'pending' else '[Done]'
        print(f"\n{g['date']} {status}")
        print(f"  {g['account']} | {g['name']} ({g['code']})")
        print(f"  {g['direction']} {g['shares']} @ {g['price']}")
        
        if g['status'] == 'completed':
            pl = (g['result_price'] - g['price']) * g['shares']
            rr = (g['result_price'] - g['price']) / g['price'] * 100
            s = '+' if pl >= 0 else ''
            print(f"  Result: {g['result_price']} | P/L: {s}{pl:.2f} ({s}{rr:.2f}%)")
    
    # 统计
    completed = [g for g in guides if g['status'] == 'completed']
    if completed:
        total_pl = sum((g['result_price'] - g['price']) * g['shares'] for g in completed)
        wins = len([g for g in completed if g['result_price'] > g['price']])
        print(f"\n--- Summary ---")
        print(f"Total guides: {len(completed)}")
        print(f"Wins: {wins} / {len(completed)} ({wins/len(completed)*100:.1f}%)")
        print(f"Total P/L: +{total_pl:.2f}")

def show_all():
    show_portfolio()
    show_guides()

# ==================== 主程序 ====================

def main():
    if len(sys.argv) < 2:
        show_all()
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'add' and len(sys.argv) >= 7:
        # add 账户 代码 名称 数量 成本价
        add_holding(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), float(sys.argv[6]))
    
    elif cmd == 'sell' and len(sys.argv) >= 6:
        # sell 账户 代码 数量 卖出价
        sell_holding(sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5]))
    
    elif cmd == 'guide' and len(sys.argv) >= 7:
        # guide 账户 代码 名称 数量 价格 方向(买入/卖出)
        add_guide(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), float(sys.argv[6]), sys.argv[7])
    
    elif cmd == 'guide-result' and len(sys.argv) >= 4:
        # guide-result 代码 结果价
        update_guide(sys.argv[2], float(sys.argv[3]))
    
    elif cmd == 'portfolio':
        show_portfolio()
    
    elif cmd == 'guides':
        show_guides()
    
    elif cmd == 'all':
        show_all()
    
    else:
        print('''
Stock Tracker v3.0
==================

Usage:
  python stock_tracker.py                    - Show all
  python stock_tracker.py add 账户 代码 名称 数量 成本价
  python stock_tracker.py sell 账户 代码 数量 卖出价
  python stock_tracker.py guide 账户 代码 名称 数量 价格 方向
  python stock_tracker.py guide-result 代码 结果价
  python stock_tracker.py portfolio
  python stock_tracker.py guides
''')

if __name__ == "__main__":
    main()
