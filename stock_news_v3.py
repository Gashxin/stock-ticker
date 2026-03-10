# -*- coding: utf-8 -*-
"""
财经新闻爬虫 v3 - 东方财富接口
==============================
修复数据解析问题
"""

import urllib.request
import json
import ssl
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

def create_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_realtime_price(code):
    """获取实时价格 - 腾讯接口"""
    market = 'sz' if code.startswith('00') or code.startswith('30') or code.startswith('56') else 'sh'
    url = f'https://qt.gtimg.cn/q={market}{code}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        parts = content.split('=')[1].strip(';').strip('"').split('~')
        return {
            'code': code,
            'name': parts[1],
            'current': float(parts[3]),
            'prev': float(parts[4]),
            'open': float(parts[5]),
            'pct': float(parts[32]),
            'high': float(parts[33]),
            'low': float(parts[34]),
            'volume': int(parts[6]),
            'amount': float(parts[7]),
            'vol_ratio': float(parts[38]) if parts[38] else 1.0,
        }
    except Exception as e:
        return {'error': str(e)}

def get_fund_flow(code):
    """获取资金流向 - 东方财富"""
    market = '0' if code.startswith('60') or code.startswith('68') else '1'
    url = f'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=5&klt=1&secid={market}.{code}&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=create_context())
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('klines'):
            klines = data['data']['klines']
            result = []
            for k in klines[-5:]:
                parts = k.split(',')
                result.append({
                    'date': parts[0],
                    'net_inflow': float(parts[1]) if parts[1] else 0,
                })
            return result
    except:
        pass
    return []

def get_longhub_list():
    """获取今日龙虎榜"""
    url = 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&fid=f3&fs=m:90+t:2'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=create_context())
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('diff'):
            result = []
            for item in data['data']['diff'][:10]:
                result.append({
                    'name': item.get('f14', ''),
                    'code': item.get('f57', ''),
                    'pct': item.get('f3', 0),
                })
            return result
    except:
        pass
    return []

def get_concept_board():
    """获取概念板块涨跌"""
    url = 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1&fid=f2&fs=m:90+t:3'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=create_context())
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('diff'):
            result = []
            for item in data['data']['diff'][:15]:
                result.append({
                    'name': item.get('f14', ''),
                    'pct': item.get('f3', 0),
                })
            return result
    except:
        pass
    return []

def get_industry_board():
    """获取行业板块涨跌"""
    url = 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1&fid=f2&fs=m:90+t:1'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=create_context())
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('diff'):
            result = []
            for item in data['data']['diff'][:15]:
                result.append({
                    'name': item.get('f14', ''),
                    'pct': item.get('f3', 0),
                })
            return result
    except:
        pass
    return []

def analyze_fund_flow(flow_data):
    """分析资金流向"""
    if not flow_data:
        return '未知', 0
    total = sum(d['net_inflow'] for d in flow_data)
    if total > 500:
        return '净流入', total
    elif total < -500:
        return '净流出', total
    return '平衡', total

# 主程序
if __name__ == '__main__':
    print('='*70)
    print('财经数据爬虫 v3')
    print('='*70)
    
    # 个股数据
    stocks = [('000032', '深桑达A'), ('300486', '东杰智能'), ('603501', '豪威集团')]
    
    print('\n【个股数据】')
    for code, name in stocks:
        price = get_realtime_price(code)
        flow = get_fund_flow(code)
        
        if 'error' not in price:
            print(f'\n{name} ({code}):')
            print(f'  当前: {price["current"]:.2f} ({price["pct"]:+.2f}%)')
            print(f'  涨跌: {price["current"]-price["prev"]:+.2f}')
            print(f'  最高: {price["high"]:.2f}, 最低: {price["low"]:.2f}')
            print(f'  量比: {price["vol_ratio"]:.2f}')
            
            if flow:
                sentiment, amount = analyze_fund_flow(flow)
                print(f'  资金: {sentiment} {amount/10000:.1f}万')
    
    # 板块数据
    print('\n\n【行业板块涨幅榜】')
    industry = get_industry_board()
    for i, item in enumerate(industry[:10]):
        print(f'  {i+1}. {item["name"]}: {item["pct"]:+.2f}%')
    
    print('\n【概念板块涨幅榜】')
    concept = get_concept_board()
    for i, item in enumerate(concept[:10]):
        print(f'  {i+1}. {item["name"]}: {item["pct"]:+.2f}%')
    
    print('\n【龙虎榜】')
    lhb = get_longhub_list()
    for i, item in enumerate(lhb[:5]):
        print(f'  {i+1}. {item["name"]}: {item["pct"]:+.2f}%')
    
    print('\n' + '='*70)
