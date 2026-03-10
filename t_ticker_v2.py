# -*- coding: utf-8 -*-
"""
V90 做T实时提醒器 v2.0
=========================

功能: 交易日实时监控做T信号，触发时自动提醒

监控股票:
- 深桑达A (000032) - 涨跌幅10%
- 东杰智能 (300486) - 涨跌幅20%(创业板)
- 雅化集团 (002497)
- 江特电机 (002176)
- 高端制造 (562910) - 涨跌幅30%(北交所)
- 豪威集团 (603501)

做T条件 (满足任一):
1. 连续2-3天上涨 → 可以做T
2. 放量+上涨(量比>1.5) → 可以做T
3. 突破20日高点+放量 → 可以做T

禁止做T:
1. 连续下跌3天后 → 禁止
2. 高开低走日 → 禁止

使用方法:
1. 手动运行: python t_ticker_v2.py
2. 定时运行: 设置Windows任务计划，每30分钟运行一次

作者: 黄新民
日期: 2026-03-10
"""


def get_price_limit(code):
    """获取股票涨跌幅限制
    - 688xxx: 科创板 20%
    - 300xxx: 创业板 20%
    - 8xxxx/4xxxx: 北交所 30%
    - 002xxx: 中小板 10%
    - 000xxx/001xxx: 深交所主板 10%
    - 600xxx/601xxx/603xxx: 上交所主板 10%
    - ST/*ST: 5%
    """
    code = str(code)
    
    # 北交所
    if code.startswith('8') or code.startswith('4'):
        return 30
    # 科创板
    if code.startswith('688'):
        return 20
    # 创业板
    if code.startswith('300'):
        return 20
    # ST/*ST
    if code.startswith('ST') or code.startswith('*ST'):
        return 5
    # 上海主板
    if code.startswith('600') or code.startswith('601') or code.startswith('603'):
        return 10
    # 深圳主板/中小板
    if code.startswith('000') or code.startswith('001') or code.startswith('002'):
        return 10
    # 默认
    return 10

import urllib.request
import json
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# ==================== 配置 ====================
STOCKS = [
    ('000032', '深桑达A'),
    ('300486', '东杰智能'),
    ('002497', '雅化集团'),
    ('002176', '江特电机'),
    ('562910', '高端制造'),
    ('603501', '豪威集团'),
]

# ==================== 数据获取 ====================

def get_quote(code):
    """获取实时报价"""
    market = 'sz' + code if not code.startswith('6') else 'sh' + code
    url = 'https://qt.gtimg.cn/q=' + market
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        parts = content.split('=')[1].strip(';').split('~')
        
        return {
            'code': code,
            'name': parts[1],
            'current': float(parts[3]),
            'prev_close': float(parts[4]),
            'open': float(parts[5]),
            'high': float(parts[33]),
            'low': float(parts[34]),
            'volume': float(parts[6]),
            'pct': float(parts[32]),
        }
    except:
        return None

def get_kline(code, days=30):
    """获取K线数据"""
    market = 'sz' if code.startswith('00') or code.startswith('30') else 'sh'
    url = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=' + market + code + ',day,,,' + str(days) + ',qfq'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        content = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
        data = json.loads(content)
        key = market + code
        klines = data['data'].get(key, {}).get('qfqday') or data['data'].get(key, {}).get('day')
        if not klines: return None
        
        df = pd.DataFrame([k[:6] for k in klines], columns=['date','open','close','high','low','volume'])
        for c in ['open','close','high','low']: df[c] = df[c].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except:
        return None

def calc_indicators(df):
    """计算技术指标"""
    df = df.copy()
    df['vol_ma5'] = df['volume'].rolling(5).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma5']
    df['high_20'] = df['high'].rolling(20).max()
    df['breakout'] = df['close'] > df['high_20'].shift(1)
    df['close_1'] = df['close'].shift(1)
    df['close_2'] = df['close'].shift(2)
    df['close_3'] = df['close'].shift(3)
    return df

# ==================== 信号检测 ====================

def check_signal(code, name):
    """检查做T信号"""
    quote = get_quote(code)
    df = get_kline(code, 30)
    
    if df is None or quote is None:
        return None
    
    df = calc_indicators(df)
    
    if len(df) < 5:
        return None
    
    latest = df.iloc[-1]
    prev_close = latest['close_1']
    
    # 连续上涨判断
    up1 = latest['close'] > latest['close_1']
    up2 = latest['close_1'] > latest['close_2']
    up3 = latest['close_2'] > latest['close_3']
    
    # 连续下跌判断
    down1 = latest['close'] < latest['close_1']
    down2 = latest['close_1'] < latest['close_2']
    down3 = latest['close_2'] < latest['close_3']
    
    # 高开低走判断
    high_open = latest['open'] > prev_close * 1.01  # 高开1%以上
    low_close = latest['close'] < latest['open']    # 收阴线
    is_high_open_low_close = high_open and low_close
    
    # 信号判断
    can_t = False
    reason = ''
    forbidden = False
    forbid_reason = ''
    
    # 禁止做T条件 (优先级最高)
    # 高开低走: 成功率0%，必须禁止
    if is_high_open_low_close:
        forbidden = True
        forbid_reason = '高开低走(禁止)'
    elif down1 and down2 and down3:
        forbidden = True
        forbid_reason = '连续下跌3天'
    
    # 可做T条件 (仅在不禁用时)
    if not forbidden:
        # 连续3天上涨: 今天AND昨天AND2天前都上涨
        if latest['breakout'] and latest['vol_ratio'] > 1.3:
            can_t = True
            reason = '突破20日+放量'
        elif up1 and up2 and up3:
            can_t = True
            reason = '连续3天上涨'
        elif up1 and up2:
            can_t = True
            reason = '连续2天上涨'
        elif latest['vol_ratio'] > 1.5 and up1:
            can_t = True
            reason = '放量上涨'
    
    # 返回结果
    return {
        'code': code,
        'name': name,
        'quote': quote,
        'can_t': can_t,
        'reason': reason,
        'forbidden': forbidden,
        'forbid_reason': forbid_reason,
        'up3': up1 and up2 and up3,  # 真正的连续3天上涨
        'up2': up1 and up2,  # 真正的连续2天上涨
        'down3': down1 and down2 and down3,  # 真正的连续3天下跌
        'breakout': latest['breakout'],
        'vol_ratio': round(latest['vol_ratio'], 2),
        'price_limit': get_price_limit(code),  # 涨跌幅限制
    }

def is_trading_hours():
    """检查是否在交易时间"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    
    # 9:30-11:30 上午
    if hour == 9 and minute >= 30:
        return True
    if 10 <= hour <= 11:
        return True
    if hour == 11 and minute <= 30:
        return True
    
    # 13:00-15:00 下午
    if 13 <= hour <= 14:
        return True
    if hour == 15 and minute == 0:
        return True
    
    return False

# ==================== 主程序 ====================

def main():
    now = datetime.now()
    is_trading = is_trading_hours()
    
    print('='*70)
    print('    V90 做T实时提醒器 v2.0')
    print('    时间: ' + now.strftime('%Y-%m-%d %H:%M:%S'))
    print('    交易时段: ' + ('是' if is_trading else '否'))
    print('='*70)
    
    alerts = []
    results = []
    
    for code, name in STOCKS:
        result = check_signal(code, name)
        
        if result:
            q = result['quote']
            results.append(result)
            
            print('\n' + result['name'] + ' (' + result['code'] + ')')
            print('  当前: ' + str(q['current']) + '元 (' + str(q['pct']) + '%)')
            print('  放量: ' + str(result['vol_ratio']) + 'x')
            print('  涨跌幅: ' + str(result['price_limit']) + '%')
            print('  突破20日: ' + str(result['breakout']))
            print('  连续上涨: ' + ('3天' if result['up3'] else '2天' if result['up2'] else '无'))
            
            if result['forbidden']:
                print('  >>> 禁止做T: ' + result['forbid_reason'] + ' <<<')
            elif result['can_t']:
                print('  >>> ✅ 可以做T! 原因: ' + result['reason'] + ' <<<')
                alerts.append(result['name'] + ': ' + result['reason'])
            else:
                print('  >>> ⏳ 观望 <<<')
    
    print('\n' + '='*70)
    
    # 输出信号汇总
    if alerts:
        print('\n🔥 【做T信号提醒】')
        for a in alerts:
            print('  ' + a)
        print('\n  操作建议: 开盘买入，收盘卖出，止损-2%')
    else:
        print('\n⏳ 今日无做T信号')
    
    # 输出文件供其他程序读取
    alert_file = 't_alerts.txt'
    with open(alert_file, 'w', encoding='utf-8') as f:
        if alerts:
            f.write('有信号\n')
            for a in alerts:
                f.write(a + '\n')
        else:
            f.write('无信号\n')
    
    print('\n' + '='*70)
    print('    报告完成')
    print('='*70)

if __name__ == "__main__":
    main()
