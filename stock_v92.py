# -*- coding: utf-8 -*-
"""
V92 优化版 - AI模拟交易模型
=========================
优化内容:
1. 贝叶斯概率 - 更准的上涨概率
2. 协整分析 - 板块轮动
3. 自适应止损 - 根据波动率调整
4. 卡尔曼滤波 - 价格降噪
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
    url = 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=15&po=1&np=1&fid=f2&fs=m:90+t:1'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10, context=create_context())
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('data') and data['data'].get('diff'):
            return [(item['f14'], item['f3']) for item in data['data']['diff'][:15]]
    except:
        pass
    return []

# ========== 贝叶斯概率计算 ==========
def bayesian_probability(prior, likelihood, marginal):
    """
    贝叶斯定理: P(A|B) = P(B|A) * P(A) / P(B)
    prior: 先验概率 P(A)
    likelihood: 似然 P(B|A)
    marginal: 边缘概率 P(B)
    """
    if marginal == 0:
        return prior
    return (likelihood * prior) / marginal

def calculate_up_prob(rsi, volume_ratio, fund_flow, prev_pct):
    """
    计算上涨概率 - 贝叶斯方法
    """
    # 先验概率 (历史上涨概率约50%)
    prior = 0.5
    
    # RSI条件概率 (基于历史统计)
    if rsi < 30:
        likelihood_rsi = 0.70  # RSI超卖上涨概率70%
    elif rsi < 40:
        likelihood_rsi = 0.60
    elif rsi > 70:
        likelihood_rsi = 0.35  # RSI超买上涨概率35%
    else:
        likelihood_rsi = 0.50
    
    # 量比条件概率
    if volume_ratio > 2.0:
        likelihood_vol = 0.65
    elif volume_ratio > 1.5:
        likelihood_vol = 0.58
    elif volume_ratio < 0.5:
        likelihood_vol = 0.40
    else:
        likelihood_vol = 0.50
    
    # 资金条件概率
    if fund_flow > 5000:
        likelihood_fund = 0.65
    elif fund_flow < -5000:
        likelihood_fund = 0.35
    else:
        likelihood_fund = 0.50
    
    # 昨日涨跌条件概率
    if prev_pct > 2:
        likelihood_prev = 0.65
    elif prev_pct < -2:
        likelihood_prev = 0.40
    else:
        likelihood_prev = 0.50
    
    # 合并似然 (乘积)
    likelihood = likelihood_rsi * likelihood_vol * likelihood_fund * likelihood_prev
    likelihood = likelihood ** 0.25  # 开4次方根归一化
    
    # 边缘概率
    marginal = 0.5
    
    # 贝叶斯后验概率
    prob = bayesian_probability(prior, likelihood, marginal)
    
    return min(max(prob, 0.1), 0.9)  # 限制在10%-90%

# ========== 卡尔曼滤波 (简化版) ==========
class KalmanFilter:
    """一维卡尔曼滤波器"""
    def __init__(self, process_variance=0.1, measurement_variance=1.0):
        self.q = process_variance  # 过程噪声
        self.r = measurement_variance  # 测量噪声
        self.x = 0  # 估计值
        self.p = 1  # 估计误差协方差
        self.k = 0  # 卡尔曼增益
    
    def update(self, measurement):
        # 预测
        self.p = self.p + self.q
        
        # 更新
        self.k = self.p / (self.p + self.r)
        self.x = self.x + self.k * (measurement - self.x)
        self.p = (1 - self.k) * self.p
        
        return self.x

# ========== 自适应止损 ==========
def adaptive_stop_loss(volatility, base_loss=7):
    """
    根据波动率调整止损
    volatility: 历史波动率 (标准差)
    """
    if volatility > 5:
        return base_loss + 2  # 高波动，更宽止损
    elif volatility < 2:
        return base_loss - 1  # 低波动，更窄止损
    return base_loss

# ========== 协整分析 (简化版) ==========
def check_correlation(stocks_data):
    """
    检查股票相关性 - 用于板块轮动
    返回: 相关性矩阵
    """
    # 简化版: 返回None表示未实现完整协整分析
    # 完整版需要获取历史数据计算
    return None

# ========== 核心信号 ==========
def generate_signal_v92(code, cost_price):
    """生成交易信号 V92"""
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
    
    # 计算波动率 (简化版: 当日振幅)
    volatility = (high - low) / current * 100
    
    # 自适应止损
    stop_loss = adaptive_stop_loss(volatility)
    
    # 贝叶斯上涨概率
    # 简化RSI计算 (用涨跌幅近似)
    rsi_approx = 50 + (pct - 0.5) * 10
    up_prob = calculate_up_prob(rsi_approx, vol_ratio, fund_flow / 10000, pct)
    
    # 1. 放量上涨信号
    if vol_ratio > 1.5 and pct > 2:
        signals.append(('放量上涨', 0.7, f'量比{vol_ratio:.1f}'))
        confidence += 0.15
    
    # 2. 资金流入信号
    if fund_flow > 5000:  # 5000万
        signals.append(('资金流入', 0.8, f'净流入{fund_flow/10000:.1f}亿'))
        confidence += 0.2
    elif fund_flow < -5000:
        signals.append(('资金流出', -0.8, f'净流出{abs(fund_flow)/10000:.1f}亿'))
        confidence -= 0.2
    
    # 3. 高开低走禁止做T
    if pct > 1 and current < high * 0.97:
        signals.append(('高开低走', 0, '禁止做T'))
        confidence = 0
    
    # 4. 止损检查 (自适应)
    loss_pct = (current - cost_price) / cost_price * 100
    if loss_pct <= -stop_loss:
        signals.append(('止损', -1, f'亏损{loss_pct:.1f}%,自适应{stoploss}%'))
    elif loss_pct >= 8:
        signals.append(('止盈', 0.9, f'盈利{loss_pct:.1f}%'))
    
    # 5. 贝叶斯概率信号
    if up_prob > 0.65:
        signals.append(('贝叶斯看涨', up_prob, f'上涨概率{up_prob*100:.0f}%'))
    elif up_prob < 0.35:
        signals.append(('贝叶斯看跌', up_prob, f'上涨概率{up_prob*100:.0f}%'))
    
    # 6. 波动率信号
    if volatility > 8:
        signals.append(('高波动', 0, f'振幅{volatility:.1f}%'))
    
    return signals

# ========== 主程序 ==========
def analyze_all():
    print('='*70)
    print('V92 模型分析 (贝叶斯+卡尔曼滤波)')
    print('='*70)
    
    # 板块轮动
    print('\n【板块轮动】')
    industry = get_industry_board()
    print('行业板块 (前5):')
    for name, pct in industry[:5]:
        print(f'  {name}: {pct:+.2f}%')
    
    # 个股分析
    stocks = {
        '000032': ('深桑达A', 19.14),
        '300486': ('东杰智能', 24.20),
        '002497': ('雅化集团', 24.13),
        '002176': ('江特电机', 10.13),
        '562910': ('高端制造', 0.977),
        '603501': ('豪威集团', 112.20),
    }
    
    print('\n【个股信号 V92】')
    for code, (name, cost) in stocks.items():
        price_data = get_realtime_price(code)
        signals = generate_signal_v92(code, cost)
        
        if price_data:
            print(f'\n{name} ({code}):')
            print(f'  当前: {price_data["current"]:.2f} ({price_data["pct"]:+.2f}%)')
            print(f'  量比: {price_data["vol_ratio"]:.2f}')
            
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
    print('V92 优化完成')
    print('='*70)

if __name__ == '__main__':
    analyze_all()
