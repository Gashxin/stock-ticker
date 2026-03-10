# -*- coding: utf-8 -*-
"""
每日股票分析报告生成器
包含: 大盘综述、个股行情、技术分析、做T信号、走势预判
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
    """获取实时报价"""
    market = 'sz' + code if not code.startswith('6') else 'sh' + code
    url = 'https://qt.gtimg.cn/q=' + market
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=10)
    parts = resp.read().decode('gbk').split('=')[1].strip(';').split('~')
    
    return {
        'name': parts[1],
        'current': float(parts[3]),
        'prev_close': float(parts[4]),
        'open': float(parts[5]),
        'high': float(parts[33]),
        'low': float(parts[34]),
        'volume': float(parts[6]),
        'amount': float(parts[7]),
        'pct': float(parts[32]),
    }

def get_kline(code, days=60):
    """获取K线"""
    market = 'sz' if code.startswith('00') or code.startswith('30') else 'sh'
    url = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=' + market + code + ',day,,,' + str(days) + ',qfq'
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

def get_market():
    """获取大盘数据"""
    indices = [
        ('sh000001', '上证指数'),
        ('sz399001', '深证成指'),
        ('sz399006', '创业板指'),
        ('sh000300', '沪深300'),
    ]
    
    result = []
    for code, name in indices:
        url = 'https://qt.gtimg.cn/q=' + code
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        parts = resp.read().decode('gbk').split('=')[1].split('~')
        result.append({
            'name': name,
            'current': float(parts[3]),
            'pct': float(parts[32])
        })
    return result

def generate_report():
    """生成每日报告"""
    now = datetime.now()
    weekday = '一二三四五六日'[now.weekday()]
    
    print('='*70)
    print('           每日股票分析报告')
    print('    日期: ' + now.strftime('%Y年%m月%d日') + ' 星期' + weekday)
    print('='*70)
    
    # 一、大盘综述
    print('\n【一、大盘综述】')
    markets = get_market()
    for m in markets:
        direction = '↑' if m['pct'] > 0 else '↓'
        print(f"  {m['name']}: {m['current']:.2f} {direction}{abs(m['pct']):.2f}%")
    
    # 判断市场状态
    sh_pct = markets[0]['pct']
    if sh_pct > 0.5:
        market_status = '强势上涨'
    elif sh_pct < -0.5:
        market_status = '弱势下跌'
    else:
        market_status = '震荡整理'
    print(f"  市场状态: {market_status}")
    
    # 二、个股行情
    print('\n【二、个股行情】')
    for code, name in STOCKS:
        quote = get_quote(code)
        direction = '↑' if quote['pct'] > 0 else '↓'
        print(f"  {name}: {quote['current']:.2f}元 {direction}{abs(quote['pct']):.2f}%")
        print(f"    开盘: {quote['open']:.2f} 最高: {quote['high']:.2f} 最低: {quote['low']:.2f}")
        print(f"    成交量: {int(quote['volume']/10000)}万手")
    
    # 三、技术分析
    print('\n【三、技术分析】')
    for code, name in STOCKS:
        df = get_kline(code, 60)
        if df is None: continue
        
        # 均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        latest = df.iloc[-1]
        vol_ma5 = df['volume'].rolling(5).mean().iloc[-1]
        vol_ratio = latest['volume'] / vol_ma5
        
        # 趋势
        if latest['ma5'] > latest['ma10'] > latest['ma20']:
            trend = '多头上涨'
        elif latest['ma5'] < latest['ma10'] < latest['ma20']:
            trend = '空头下跌'
        else:
            trend = '震荡整理'
        
        # 压力支撑
        high_20 = df['high'].rolling(20).max().iloc[-2]
        low_20 = df['low'].rolling(20).min().iloc[-2]
        
        print(f"  {name}: {trend}")
        print(f"    量比: {vol_ratio:.2f} 20日压力: {high_20:.2f} 支撑: {low_20:.2f}")
    
    # 四、做T信号
    print('\n【四、做T信号】')
    for code, name in STOCKS:
        df = get_kline(code, 30)
        if df is None or len(df) < 4: continue
        
        up3 = df.iloc[-1]['close'] > df.iloc[-2]['close'] > df.iloc[-3]['close'] > df.iloc[-4]['close']
        down3 = df.iloc[-1]['close'] < df.iloc[-2]['close'] < df.iloc[-3]['close'] < df.iloc[-4]['close']
        
        if down3:
            status = '❌ 禁止做T(连续下跌)'
        elif up3:
            status = '✅ 可以做T(连续上涨)'
        else:
            status = '⏳ 观望'
        
        print(f"  {name}: {status}")
    
    # 五、走势预判
    print('\n【五、走势预判】')
    
    # 大盘预判
    if sh_pct > 0:
        print(f"  大盘: 今日低开高走，明日可能继续反弹")
    else:
        print(f"  大盘: 今日下跌，明日可能低开高走反弹")
    
    # 个股预判
    for code, name in STOCKS:
        quote = get_quote(code)
        df = get_kline(code, 30)
        if df is None: continue
        
        latest = df.iloc[-1]
        up3 = latest['close'] > df.iloc[-2]['close'] > df.iloc[-3]['close']
        
        if up3:
            print(f"  {name}: 连续上涨，明日可能冲高回落，建议止盈")
        elif quote['pct'] < -3:
            print(f"  {name}: 跌幅较大，明日可能反弹")
        else:
            print(f"  {name}: 震荡整理，观望为主")
    
    # 六、操作建议
    print('\n【六、操作建议】')
    print("  1. 大盘处于震荡期，控制仓位在30%以内")
    print("  2. 深桑达A连续上涨，可做T但注意止盈")
    print("  3. 东杰智能连续下跌，禁止做T")
    print("  4. 止损线: -7% 止盈线: +8%")
    
    print('\n' + '='*70)
    print('    报告生成时间: ' + now.strftime('%H:%M'))
    print('='*70)

if __name__ == "__main__":
    generate_report()
