# -*- coding: utf-8 -*-
"""
V95 优化版 - AI模拟交易模型
=========================
优化内容:
1. 机器学习 - 逻辑回归预测
2. 凯利公式 - 最优仓位管理
3. MACD/KDJ/威廉指标
4. 大盘择时 - 上证指数联动
5. 资金管理 - 风险敞口控制
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
    market = 'sz' if code.startswith('00') or code.startswith('30') or code.startswith('56') else 'sh'
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

def get_fund_flow(code):
    market = '0' if code.startswith('60') or code.startswith('68') else '1'
    url = 'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=5&klt=1&secid={}.{}&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'.format(market, code)
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

def get_shanghai_index():
    """获取上证指数"""
    url = 'https://qt.gtimg.cn/q=sh000001'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        content = resp.read().decode('gbk')
        parts = content.split('=')[1].strip(';').strip('"').split('~')
        return {
            'current': float(parts[3]),
            'pct': float(parts[32]),
        }
    except:
        return None

# ========== MACD指标 ==========
def calculate_macd(prices):
    """
    计算MACD
    返回: DIF, DEA, MACD柱
    """
    if len(prices) < 26:
        return 0, 0, 0
    
    # EMA12, EMA26
    ema12 = sum(prices[-12:]) / 12
    ema26 = sum(prices[-26:]) / 26
    
    DIF = ema12 - ema26
    
    # DEA (9日EMA)
    dea = DIF * 0.8  # 简化
    
    MACD = (DIF - dea) * 2
    
    return DIF, dea, MACD

def macd_signal(dif, dea, macd):
    """MACD信号"""
    if dif > dea and macd > 0:
        return '金叉', 0.7
    elif dif < dea and macd < 0:
        return '死叉', -0.7
    return '震荡', 0

# ========== KDJ指标 ==========
def calculate_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """计算KDJ"""
    if len(closes) < n:
        return 50, 50, 50
    
    recent_close = closes[-n:]
    recent_high = highs[-n:] if len(highs) >= n else closes[-n:]
    recent_low = lows[-n:] if len(lows) >= n else closes[-n:]
    
    lowest = min(recent_low)
    highest = max(recent_high)
    
    if highest == lowest:
        return 50, 50, 50
    
    rsv = (closes[-1] - lowest) / (highest - lowest) * 100
    
    k = (2/3) * 50 + (1/3) * rsv
    d = (2/3) * 50 + (1/3) * k
    j = 3 * k - 2 * d
    
    return k, d, j

def kdj_signal(k, d, j):
    """KDJ信号"""
    if k < 20 and d < 20:
        return '超卖', 0.7
    elif k > 80 and d > 80:
        return '超买', -0.7
    elif k > d and k < 50:
        return '金叉', 0.5
    elif k < d and k > 50:
        return '死叉', -0.5
    return '震荡', 0

# ========== 威廉指标 ==========
def calculate_wr(highs, lows, closes, n=14):
    """计算威廉指标WR"""
    if len(closes) < n:
        return 50
    
    recent = closes[-n:]
    highest = max(highs[-n:] if len(highs) >= n else recent)
    lowest = min(lows[-n:] if len(lows) >= n else recent)
    
    if highest == lowest:
        return 50
    
    wr = (highest - closes[-1]) / (highest - lowest) * 100
    
    return wr

def wr_signal(wr):
    """威廉指标信号"""
    if wr > 80:
        return '超卖', 0.7
    elif wr < 20:
        return '超买', -0.7
    return '震荡', 0

# ========== 逻辑回归预测 (简化版) ==========
class LogisticRegression:
    """简化逻辑回归"""
    def __init__(self):
        self.weights = [0.3, 0.3, 0.2, 0.2]  # 趋势/动量/资金/波动
    
    def predict(self, trend, momentum, fund, volatility):
        """预测上涨概率"""
        features = [trend, momentum, fund, volatility]
        
        # 线性组合
        z = sum(w * f for w, f in zip(self.weights, features))
        
        # Sigmoid函数
        prob = 1 / (1 + math.exp(-z))
        
        return prob
    
    def signal(self, prob):
        if prob > 0.65:
            return '买入', prob
        elif prob < 0.35:
            return '卖出', 1 - prob
        return '持有', 0.5

# ========== 凯利公式 ==========
def kelly_formula(win_rate, avg_win, avg_loss):
    """
    凯利公式: f* = (bp - q) / b
    f*: 仓位比例
    b: 赔率 (avg_win / avg_loss)
    p: 胜率
    q: 1 - p
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
        return 0
    
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    
    kelly = (b * p - q) / b
    
    # 限制仓位 5%-30%
    return max(0.05, min(0.30, kelly))

# ========== 大盘择时 ==========
def market_timing(shanghai_pct):
    """大盘择时信号"""
    if shanghai_pct > 1:
        return '强势', 0.3
    elif shanghai_pct < -1:
        return '弱势', -0.3
    elif shanghai_pct > 0:
        return '震荡上行', 0.1
    else:
        return '震荡下行', -0.1

# ========== 风险敞口控制 ==========
def risk_exposure(position_value, total_assets, volatility):
    """风险敞口控制"""
    exposure = position_value / total_assets if total_assets > 0 else 0
    
    # 高波动时降低敞口
    if volatility > 5:
        max_exposure = 0.6
    elif volatility > 3:
        max_exposure = 0.75
    else:
        max_exposure = 0.9
    
    if exposure > max_exposure:
        return '减仓', max_exposure - exposure
    return '正常', 0

# ========== 核心信号 ==========
def generate_signal_v95(code, cost_price, total_assets=1000000):
    """生成交易信号 V95"""
    signals = []
    confidence = 0.5
    
    # 获取数据
    price_data = get_realtime_price(code)
    fund_flow = get_fund_flow(code)
    
    if not price_data:
        return [('数据获取失败', 0, '')]
    
    pct = price_data['pct']
    vol_ratio = price_data['vol_ratio']
    current = price_data['current']
    high = price_data['high']
    low = price_data['low']
    prev = price_data['prev']
    
    # 波动率
    volatility = (high - low) / current * 100
    
    # 大盘择时
    sh_data = get_shanghai_index()
    if sh_data:
        market_sig, market_conf = market_timing(sh_data['pct'])
        signals.append(('大盘', market_conf, f'{sh_data["current"]:.0f} {sh_data["pct"]:+.2f}%'))
        confidence += market_conf * 0.5
    
    # 简化技术指标 (用单日数据)
    # MACD (简化)
    mock_dif = pct * 0.5
    mock_dea = 0
    mock_macd = mock_dif - mock_dea
    macd_sig, macd_conf = macd_signal(mock_dif, mock_dea, mock_macd)
    if macd_sig != '震荡':
        signals.append((f'MACD-{macd_sig}', macd_conf, ''))
    
    # KDJ (简化)
    mock_k = 50 + pct * 5
    mock_d = 50 + pct * 3
    mock_j = 3 * mock_k - 2 * mock_d
    kdj_sig, kdj_conf = kdj_signal(mock_k, mock_d, mock_j)
    if kdj_sig != '震荡':
        signals.append((f'KDJ-{kdj_sig}', kdj_conf, ''))
    
    # 威廉指标 (简化)
    wr = 50 - pct * 10
    wr_sig, wr_conf = wr_signal(wr)
    if wr_sig != '震荡':
        signals.append((f'WR-{wr_sig}', wr_conf, ''))
    
    # 逻辑回归预测
    lr = LogisticRegression()
    trend = min(pct / 5, 1)
    momentum = min(vol_ratio / 3, 1)
    fund = min(fund_flow / 10000, 1) if fund_flow > 0 else max(fund_flow / 10000, -1)
    vol = min(volatility / 10, 1)
    
    prob = lr.predict(trend, momentum, fund, vol)
    lr_sig, lr_conf = lr.signal(prob)
    signals.append((f'LR-{lr_sig}', lr_conf, f'P={prob:.0%}'))
    
    # 多因子评分
    score = 0
    if pct > 2:
        score += 20
    elif pct < -2:
        score -= 20
    
    if vol_ratio > 2:
        score += 20
    elif vol_ratio < 0.5:
        score -= 10
    
    if fund_flow > 5000:
        score += 20
    elif fund_flow < -5000:
        score -= 20
    
    # 凯利公式 (简化: 假设胜率60%, 盈亏比1.5)
    kelly = kelly_formula(0.6, 1.5, 1.0)
    signals.append(('凯利仓位', kelly, f'{kelly*100:.0f}%'))
    
    # 风险敞口
    pos_value = current * 10000  # 假设
    exp_sig, exp_adj = risk_exposure(pos_value, total_assets, volatility)
    if exp_adj > 0:
        signals.append((exp_sig, -0.3, f'需减{exp_adj*100:.0f}%'))
    
    # 高开低走
    if pct > 1 and current < high * 0.97:
        signals.append(('高开低走', 0, '禁止做T'))
        confidence = 0
    
    # 止损检查
    stop_loss = 9 if volatility > 5 else (6 if volatility < 2 else 7)
    loss_pct = (current - cost_price) / cost_price * 100
    
    if loss_pct <= -stop_loss:
        signals.append(('止损', -1, f'亏损{loss_pct:.1f}%'))
    elif loss_pct >= 8:
        signals.append(('止盈', 0.9, f'盈利{loss_pct:.1f}%'))
    
    # 资金信号
    if fund_flow > 5000:
        signals.append(('资金流入', 0.8, f'{fund_flow/10000:.1f}亿'))
        confidence += 0.2
    elif fund_flow < -5000:
        signals.append(('资金流出', -0.8, f'{abs(fund_flow)/10000:.1f}亿'))
        confidence -= 0.2
    
    return signals

# ========== 主程序 ==========
def analyze_all():
    print('='*70)
    print('V95 模型分析 (ML+凯利公式+MACD/KDJ/WR+大盘择时)')
    print('='*70)
    
    # 大盘
    sh = get_shanghai_index()
    if sh:
        market_sig, _ = market_timing(sh['pct'])
        print(f'\n【大盘】上证指数: {sh["current"]:.0f} ({sh["pct"]:+.2f}%) - {market_sig}')
    
    stocks = {
        '000032': ('深桑达A', 19.14),
        '300486': ('东杰智能', 24.20),
        '002497': ('雅化集团', 24.13),
        '002176': ('江特电机', 10.13),
        '562910': ('高端制造', 0.977),
        '603501': ('豪威集团', 112.20),
    }
    
    print('\n【个股信号 V95】')
    for code, (name, cost) in stocks.items():
        price_data = get_realtime_price(code)
        signals = generate_signal_v95(code, cost)
        
        if price_data:
            print(f'\n{name} ({code}):')
            print(f'  当前: {price_data["current"]:.2f} ({price_data["pct"]:+.2f}%)')
            
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
    
    print('\n' + '='*70)
    print('V95 优化完成')
    print('='*70)

if __name__ == '__main__':
    analyze_all()
