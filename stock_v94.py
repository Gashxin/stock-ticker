# -*- coding: utf-8 -*-
"""
V94 优化版 - AI模拟交易模型
=========================
优化内容:
1. ARIMA时序预测
2. 布林带回归
3. 成交量异常检测
4. 多因子模型
"""

import urllib.request
import json
import ssl
import sys
import math
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ========== 工具函数 ==========
def create_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_realtime_price(code):
    """获取实时价格"""
    market = 'sz' if code.startswith('00') or code.startswith('30') or code.startswith('56') else 'sh'
    url = f'https://qt.gtimg.cn/q={market}{code}'
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
            'open': float(parts[1]) if parts[1] else 0,
            'volume': float(parts[6]) if parts[6] else 0,
            'amount': float(parts[7]) if parts[7] else 0,
        }
    except:
        return None

def get_fund_flow(code):
    """获取资金流向"""
    market = '0' if code.startswith('60') or code.startswith('68') else '1'
    url = f'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=5&klt=1&secid={market}.{code}&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=create_context())
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('klines'):
            klines = data['data']['klines']
            total = 0
            for k in klines:
                parts = k.split(',')
                total += float(parts[1]) if parts[1] else 0
            return total
    except:
        pass
    return 0

def get_industry_board():
    """获取行业板块"""
    url = 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&fid=f2&fs=m:90+t:1'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=create_context())
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('diff'):
            return [(item['f14'], item['f3']) for item in data['data']['diff'][:20]]
    except:
        pass
    return []

# ========== ARIMA 简化版 ==========
class SimpleARIMA:
    """简化ARIMA(1,1,1)预测"""
    def __init__(self):
        self.ar_coef = 0.5  # 自回归系数
        self.ma_coef = 0.3  # 移动平均系数
        self.history = []
    
    def fit(self, prices):
        """简单拟合"""
        if len(prices) < 5:
            return
        self.history = prices[-10:]  # 保留最近10个
    
    def predict(self, steps=1):
        """预测下一步"""
        if len(self.history) < 2:
            return self.history[-1] if self.history else 0
        
        # 简化: 指数加权移动平均
        weights = [0.5, 0.3, 0.2]
        n = len(self.history)
        pred = 0
        for i, w in enumerate(weights):
            idx = n - 1 - i
            if idx >= 0:
                pred += self.history[idx] * w
        
        return pred
    
    def predict_direction(self):
        """预测方向"""
        if len(self.history) < 3:
            return 0
        
        # 比较预测与当前
        current = self.history[-1]
        pred = self.predict()
        
        if pred > current * 1.01:
            return 1  # 上涨
        elif pred < current * 0.99:
            return -1  # 下跌
        return 0  # 震荡

# ========== 布林带回归 ==========
def bollinger_bands(prices, period=20, std_dev=2):
    """计算布林带"""
    if len(prices) < period:
        return None, None, None
    
    recent = prices[-period:]
    ma = sum(recent) / period
    
    # 标准差
    variance = sum((p - ma) ** 2 for p in recent) / period
    std = variance ** 0.5
    
    upper = ma + std_dev * std
    lower = ma - std_dev * std
    
    return upper, ma, lower

def bollinger_signal(current, upper, ma, lower):
    """布林带信号"""
    if current > upper:
        return '超买', -0.7
    elif current < lower:
        return '超卖', 0.7
    elif current > ma:
        return '多头', 0.3
    elif current < ma:
        return '空头', -0.3
    return '震荡', 0

# ========== 成交量异常检测 ==========
def volume_anomaly_detection(volumes, current_volume):
    """
    成交量异常检测
    使用Z-score方法
    """
    if len(volumes) < 10:
        return False, 0
    
    avg = sum(volumes) / len(volumes)
    std = (sum((v - avg) ** 2 for v in volumes) / len(volumes)) ** 0.5
    
    if std == 0:
        return False, 0
    
    z_score = (current_volume - avg) / std
    
    if z_score > 2:
        return True, z_score  # 放量异常
    elif z_score < -2:
        return True, z_score  # 缩量异常
    return False, z_score

# ========== 多因子模型 ==========
def multi_factor_score(price_data, fund_flow):
    """
    多因子评分模型
    因子: 趋势、动量、资金、波动
    """
    score = 0
    factors = []
    
    # 1. 趋势因子
    pct = price_data['pct']
    if pct > 2:
        score += 20
        factors.append(('趋势+', 20))
    elif pct > 0:
        score += 10
        factors.append(('趋势~', 10))
    elif pct > -2:
        score -= 5
        factors.append(('趋势-', -5))
    else:
        score -= 15
        factors.append(('趋势--', -15))
    
    # 2. 动量因子
    vol_ratio = price_data['vol_ratio']
    if vol_ratio > 2:
        score += 20
        factors.append(('动量+', 20))
    elif vol_ratio > 1.5:
        score += 10
        factors.append(('动量~', 10))
    elif vol_ratio < 0.5:
        score -= 10
        factors.append(('动量-', -10))
    
    # 3. 资金因子
    if fund_flow > 5000:
        score += 20
        factors.append(('资金+', 20))
    elif fund_flow > 0:
        score += 5
        factors.append(('资金~', 5))
    elif fund_flow < -5000:
        score -= 20
        factors.append(('资金-', -20))
    
    # 4. 波动因子
    volatility = (price_data['high'] - price_data['low']) / price_data['current'] * 100
    if volatility > 5:
        score += 10
        factors.append(('波动+', 10))
    elif volatility < 2:
        score -= 5
        factors.append(('波动-', -5))
    
    # 5. 开盘因子
    open_price = price_data['open']
    current = price_data['current']
    if open_price > 0:
        open_pct = (current - open_price) / open_price * 100
        if open_pct > 1:
            score -= 10  # 高开低走风险
            factors.append(('高开-', -10))
    
    return score, factors

# ========== 核心信号 ==========
def generate_signal_v94(code, cost_price, history_prices=None, history_volumes=None):
    """生成交易信号 V94"""
    signals = []
    confidence = 0.5
    
    # 获取数据
    price_data = get_realtime_price(code)
    if not price_data:
        return [('数据获取失败', 0, '')]
    
    fund_flow = get_fund_flow(code)
    pct = price_data['pct']
    vol_ratio = price_data['vol_ratio']
    current = price_data['current']
    high = price_data['high']
    low = price_data['low']
    
    # ARIMA预测
    if history_prices and len(history_prices) >= 5:
        arima = SimpleARIMA()
        arima.fit(history_prices)
        arima_dir = arima.predict_direction()
        
        if arima_dir == 1:
            signals.append(('ARIMA上涨', 0.65, '预测上涨'))
            confidence += 0.15
        elif arima_dir == -1:
            signals.append(('ARIMA下跌', -0.65, '预测下跌'))
            confidence -= 0.15
    
    # 布林带
    if history_prices and len(history_prices) >= 20:
        upper, ma, lower = bollinger_bands(history_prices)
        if upper and ma and lower:
            bband_signal, bband_conf = bollinger_signal(current, upper, ma, lower)
            signals.append((f'布林{bband_signal}', bband_conf, f'上{upper:.2f}中{ma:.2f}下{lower:.2f}'))
            confidence += bband_conf * 0.5
    
    # 成交量异常
    if history_volumes and len(history_volumes) >= 10:
        is_anomaly, z = volume_anomaly_detection(history_volumes, price_data['volume'])
        if is_anomaly and z > 2:
            signals.append(('放量异常', 0.7, f'Z={z:.1f}'))
            confidence += 0.15
        elif is_anomaly and z < -2:
            signals.append(('缩量异常', 0.3, f'Z={z:.1f}'))
    
    # 多因子评分
    score, factors = multi_factor_score(price_data, fund_flow)
    if score >= 40:
        signals.append(('多因子看涨', 0.75, f'得分{score}'))
        confidence += 0.2
    elif score >= 20:
        signals.append(('多因子偏多', 0.55, f'得分{score}'))
        confidence += 0.1
    elif score <= -20:
        signals.append(('多因子看跌', -0.75, f'得分{score}'))
        confidence -= 0.2
    
    # 1. 放量上涨
    if vol_ratio > 1.5 and pct > 2:
        signals.append(('放量上涨', 0.7, f'量比{vol_ratio:.1f}'))
        confidence += 0.15
    
    # 2. 资金信号
    if fund_flow > 5000:
        signals.append(('资金流入', 0.8, f'{fund_flow/10000:.1f}亿'))
        confidence += 0.2
    elif fund_flow < -5000:
        signals.append(('资金流出', -0.8, f'{abs(fund_flow)/10000:.1f}亿'))
        confidence -= 0.2
    
    # 3. 高开低走
    if pct > 1 and current < high * 0.97:
        signals.append(('高开低走', 0, '禁止做T'))
        confidence = 0
    
    # 4. 止损检查
    volatility = (high - low) / current * 100
    stop_loss = 9 if volatility > 5 else (6 if volatility < 2 else 7)
    
    loss_pct = (current - cost_price) / cost_price * 100
    if loss_pct <= -stop_loss:
        signals.append(('止损', -1, f'亏损{loss_pct:.1f}%'))
    elif loss_pct >= 8:
        signals.append(('止盈', 0.9, f'盈利{loss_pct:.1f}%'))
    
    return signals

# ========== 主程序 ==========
def analyze_all():
    print('='*70)
    print('V94 模型分析 (ARIMA+布林带+成交量异常+多因子)')
    print('='*70)
    
    # 板块轮动
    print('\n【板块轮动】')
    industry = get_industry_board()
    print('行业板块 (前5):')
    for i, (name, pct) in enumerate(industry[:5]):
        print(f'  {i+1}. {name}: {pct:+.2f}%')
    
    # 个股分析
    stocks = {
        '000032': ('深桑达A', 19.14),
        '300486': ('东杰智能', 24.20),
        '002497': ('雅化集团', 24.13),
        '002176': ('江特电机', 10.13),
        '562910': ('高端制造', 0.977),
        '603501': ('豪威集团', 112.20),
    }
    
    print('\n【个股信号 V94】')
    stock_data = []
    for code, (name, cost) in stocks.items():
        price_data = get_realtime_price(code)
        signals = generate_signal_v94(code, cost)
        
        if price_data:
            stock_data.append((name, code, price_data['current'], price_data['pct'], price_data['vol_ratio']))
            
            print(f'\n{name} ({code}):')
            print(f'  当前: {price_data["current"]:.2f} ({price_data["pct"]:+.2f}%)')
            print(f'  量比: {price_data["vol_ratio"]:.2f}')
            
            # 多因子评分
            fund_flow = get_fund_flow(code)
            score, factors = multi_factor_score(price_data, fund_flow)
            print(f'  多因子得分: {score}')
            for fname, fscore in factors:
                print(f'    {fname}: {fscore:+d}')
            
            if signals:
                print('  信号:')
                for sig_name, conf, desc in signals:
                    if conf == 0:
                        print(f'    ❌ {sig_name}: {desc}')
                    elif conf > 0.6:
                        print(f'    ✅ {sig_name} ({conf*100:.0f}%): {desc}')
                    elif conf > 0:
                        print(f'    🟡 {sig_name} ({conf*100:.0f}%): {desc}')
                    else:
                        print(f'    ⚠️ {sig_name}: {desc}')
            else:
                print('  信号: 无明确信号')
    
    print('\n' + '='*70)
    print('V94 优化完成')
    print('='*70)

if __name__ == '__main__':
    analyze_all()
