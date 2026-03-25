# -*- coding: utf-8 -*-
"""
V90 做T实时提醒器 - 修正版
监控: 深桑达A、东杰智能、大族激光、豪威集团

做T条件:
1. 连续2-3天上涨
2. 放量+上涨(量比>1.5)
3. 突破20日高点+放量

禁止做T:
1. 连续下跌3天后
2. 高开低走日
"""

import urllib.request
import json
import pandas as pd
import numpy as np
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

STOCKS = [
    ('000032', '深桑达A'),
    ('300486', '东杰智能'),
    ('002008', '大族激光'),
    ('603501', '豪威集团'),
]

def get_quote(code):
    market = 'sz' + code if not code.startswith('6') else 'sh' + code
    url = 'https://qt.gtimg.cn/q=' + market
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        data = content.split('=')[1].strip(';')
        parts = data.split('~')
        return {
            'name': parts[1],
            'current': float(parts[3]),
            'pct': float(parts[32]),
            'open': float(parts[5]),
        }
    except: return None

def get_kline(code, days=60):
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
    except: return None

def main():
    print('='*70)
    print('    V90 做T实时提醒器')
    print('    时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)
    
    alerts = []
    
    for code, name in STOCKS:
        quote = get_quote(code)
        df = get_kline(code, 60)
        
        if quote is None or df is None or len(df) < 30:
            continue
        
        # 计算指标
        df['vol_ma5'] = df['volume'].rolling(5).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma5']
        df['high_20'] = df['high'].rolling(20).max()
        df['breakout'] = df['close'] > df['high_20'].shift(1)
        
        latest = df.iloc[-1]
        
        # 连续上涨/下跌
        up_today = latest['close'] > df.iloc[-2]['close']
        up_yesterday = df.iloc[-2]['close'] > df.iloc[-3]['close']
        up_3days_ago = df.iloc[-3]['close'] > df.iloc[-4]['close']
        
        down_today = latest['close'] < df.iloc[-2]['close']
        down_yesterday = df.iloc[-2]['close'] < df.iloc[-3]['close']
        down_3days_ago = df.iloc[-3]['close'] < df.iloc[-4]['close']
        
        # 判断
        can_t = False
        reason = ''
        forbidden = False
        forbid_reason = ''
        
        # 禁止: 连续下跌3天
        if down_today and down_yesterday and down_3days_ago:
            forbidden = True
            forbid_reason = '连续下跌3天'
        # 禁止: 高开低走
        elif latest['open'] > df.iloc[-2]['close'] * 1.01 and latest['close'] < latest['open']:
            forbidden = True
            forbid_reason = '高开低走'
        # 可以做T: 连续上涨
        elif up_today and up_yesterday:
            can_t = True
            reason = '连续上涨'
        # 可以做T: 放量突破
        elif latest['breakout'] and latest['vol_ratio'] > 1.3:
            can_t = True
            reason = '放量突破'
        
        print('\n' + name + ' (' + code + ')')
        print('  当前: ' + str(quote['current']) + '元 (' + str(quote['pct']) + '%)')
        print('  放量: ' + str(round(latest['vol_ratio'], 2)) + 'x')
        print('  突破20日: ' + str(latest['breakout']))
        
        if forbidden:
            print('  >>> 禁止做T: ' + forbid_reason + ' <<<')
        elif can_t:
            print('  >>> 可以做T! ' + reason + ' <<<')
            alerts.append(name + ': ' + reason)
        else:
            print('  >>> 观望 <<<')
    
    print('\n' + '='*70)
    if alerts:
        print('\n🔥 做T信号: ' + ', '.join(alerts))
    else:
        print('\n⏳ 无做T信号')

if __name__ == "__main__":
    main()
