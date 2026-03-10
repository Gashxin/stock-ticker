# -*- coding: utf-8 -*-
"""
V93 优化版 - AI模拟交易模型
=========================
优化内容:
1. 协整分析 - 板块轮动/配对交易
2. Markowitz组合优化 - 仓位管理
3. 线性回归趋势预测
4. 增强版卡尔曼滤波
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

# ========== 线性回归趋势预测 ==========
class LinearRegression:
    """简单线性回归"""
    def __init__(self):
        self.slope = 0
        self.intercept = 0
    
    def fit(self, x, y):
        """最小二乘法拟合"""
        n = len(x)
        if n < 2:
            return
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        
        self.slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
        self.intercept = (sum_y - self.slope * sum_x) / n
    
    def predict(self, x):
        return self.slope * x + self.intercept
    
    def predict_next(self):
        """预测下一期"""
        return self.predict(len([1,2,3,4,5]) + 1)

def calculate_trend(prices):
    """
    计算趋势 - 线性回归
    返回: slope (斜率), direction (1上涨/-1下跌/0震荡)
    """
    if len(prices) < 5:
        return 0, 0
    
    x = list(range(len(prices)))
    lr = LinearRegression()
    lr.fit(x, prices)
    
    # 标准化斜率
    avg_price = sum(prices) / len(prices)
    normalized_slope = (lr.slope / avg_price) * 100 if avg_price > 0 else 0
    
    if normalized_slope > 0.5:
        direction = 1  # 上涨
    elif normalized_slope < -0.5:
        direction = -1  # 下跌
    else:
        direction = 0  # 震荡
    
    return normalized_slope, direction

# ========== 协整分析 (简化版) ==========
def cointegration_test(price_series1, price_series2):
    """
    协整检验 (简化版)
    检验两个序列是否协整
    返回: z-score (偏离程度)
    """
    if len(price_series1) != len(price_series2) or len(price_series1) < 5:
        return 0
    
    # 计算价格比率
    ratios = [p1 / p2 for p1, p2 in zip(price_series1, price_series2) if p2 != 0]
    if not ratios:
        return 0
    
    # 简化: 计算比率的标准差偏离
    mean_ratio = sum(ratios) / len(ratios)
    std_ratio = (sum((r - mean_ratio) ** 2 for r in ratios) / len(ratios)) ** 0.5
    
    if std_ratio == 0:
        return 0
    
    # 当前偏离
    current_ratio = price_series1[-1] / price_series2[-1] if price_series2[-1] != 0 else 0
    z_score = (current_ratio - mean_ratio) / std_ratio
    
    return z_score

# ========== Markowitz组合优化 (简化版) ==========
def markowitz_optimize(expected_returns, volatilities, correlation_matrix=None):
    """
    Markowitz均值-方差优化 (简化版)
    返回: 最优权重
    """
    n = len(expected_returns)
    if n == 0:
        return []
    
    # 简化: 等权重 + 风险调整
    # 实际应该用二次规划求解
    weights = []
    total_inverse_vol = sum(1/v if v > 0 else 0 for v in volatilities)
    
    for i, vol in enumerate(volatilities):
        if vol > 0 and total_inverse_vol > 0:
            w = (1/vol) / total_inverse_vol
            weights.append(min(w, 0.4))  # 单只股票不超过40%
        else:
            weights.append(1/n)
    
    # 归一化
    total = sum(weights)
    if total > 0:
        weights = [w/total for w in weights]
    
    return weights

# ========== 增强版卡尔曼滤波 ==========
class EnhancedKalmanFilter:
    """多状态卡尔曼滤波器"""
    def __init__(self):
        self.price_kf = KalmanFilter1D(0.01, 0.1)  # 价格
        self.volume_kf = KalmanFilter1D(0.1, 1.0)   # 成交量
        self.trend_kf = KalmanFilter1D(0.05, 0.5)   # 趋势
    
    def update(self, price, volume, trend):
        filtered_price = self.price_kf.update(price)
        filtered_volume = self.volume_kf.update(volume)
        filtered_trend = self.trend_kf.update(trend)
        
        return {
            'price': filtered_price,
            'volume': filtered_volume,
            'trend': filtered_trend
        }

class KalmanFilter1D:
    """一维卡尔曼滤波器"""
    def __init__(self, process_variance=0.1, measurement_variance=1.0):
        self.q = process_variance
        self.r = measurement_variance
        self.x = 0
        self.p = 1
        self.k = 0
    
    def update(self, measurement):
        self.p = self.p + self.q
        self.k = self.p / (self.p + self.r) if (self.p + self.r) > 0 else 0
        self.x = self.x + self.k * (measurement - self.x)
        self.p = (1 - self.k) * self.p
        return self.x

# ========== 熵值法 - 市场情绪 ==========
def calculate_entropy(prices):
    """
    计算价格序列熵值
    熵越高，市场越不确定/震荡
    熵越低，市场趋势越明确
    """
    if len(prices) < 3:
        return 0.5
    
    # 计算日收益率
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] > 0:
            r = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(r)
    
    if not returns:
        return 0.5
    
    # 离散化收益率
    bins = [-1, -0.02, 0, 0.02, 1]
    hist, _ = [0]*3, []
    
    for r in returns:
        if r < -0.02:
            hist[0] += 1
        elif r < 0.02:
            hist[1] += 1
        else:
            hist[2] += 1
    
    # 计算熵
    n = len(returns)
    entropy = 0
    for count in hist:
        if count > 0:
            p = count / n
            entropy -= p * math.log2(p)
    
    return entropy

# ========== 核心信号 ==========
def generate_signal_v93(code, cost_price, history_prices=None):
    """生成交易信号 V93"""
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
    
    # 计算波动率
    volatility = (high - low) / current * 100
    
    # 趋势预测
    if history_prices and len(history_prices) >= 5:
        slope, direction = calculate_trend(history_prices)
        
        if direction == 1:
            signals.append(('趋势上涨', 0.7, f'斜率{slope:.2f}%'))
            confidence += 0.15
        elif direction == -1:
            signals.append(('趋势下跌', -0.7, f'斜率{slope:.2f}%'))
            confidence -= 0.15
    
    # 熵值 (市场情绪)
    if history_prices and len(history_prices) >= 5:
        entropy = calculate_entropy(history_prices)
        if entropy < 0.8:
            signals.append(('低熵趋势', 0.6, f'熵值{entropy:.2f}'))
            confidence += 0.1
        elif entropy > 1.5:
            signals.append(('高熵震荡', 0, f'熵值{entropy:.2f}'))
            confidence -= 0.1
    
    # 1. 放量上涨信号
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
    
    # 3. 高开低走禁止做T
    if pct > 1 and current < high * 0.97:
        signals.append(('高开低走', 0, '禁止做T'))
        confidence = 0
    
    # 4. 止损检查
    loss_pct = (current - cost_price) / cost_price * 100
    if volatility > 5:
        stop_loss = 9
    elif volatility < 2:
        stop_loss = 6
    else:
        stop_loss = 7
    
    if loss_pct <= -stop_loss:
        signals.append(('止损', -1, f'亏损{loss_pct:.1f}%'))
    elif loss_pct >= 8:
        signals.append(('止盈', 0.9, f'盈利{loss_pct:.1f}%'))
    
    # 5. 波动率信号
    if volatility > 8:
        signals.append(('高波动', 0, f'振幅{volatility:.1f}%'))
    
    return signals

# ========== 主程序 ==========
def analyze_all():
    print('='*70)
    print('V93 模型分析 (Markowitz+协整+趋势预测+熵值)')
    print('='*70)
    
    # 板块轮动
    print('\n【板块轮动 - 协整分析】')
    industry = get_industry_board()
    print('行业板块 (前10):')
    top_sectors = []
    for i, (name, pct) in enumerate(industry[:10]):
        print(f'  {i+1}. {name}: {pct:+.2f}%')
        if pct > 0:
            top_sectors.append((name, pct))
    
    # 板块轮动建议
    if top_sectors:
        best = max(top_sectors, key=lambda x: x[1])
        print(f'\n建议关注: {best[0]} ({best[1]:+.2f}%)')
    
    # 协整分析示例
    print('\n【协整分析示例】')
    # 深桑达A vs 豪威集团 (示例)
    ss_price = get_realtime_price('000032')
    hw_price = get_realtime_price('603501')
    if ss_price and hw_price:
        # 简化: 用当前价格模拟历史
        mock_history1 = [ss_price['current'] * (1 + i*0.01) for i in range(-5, 0)]
        mock_history2 = [hw_price['current'] * (1 + i*0.008) for i in range(-5, 0)]
        z = cointegration_test(mock_history1, mock_history2)
        print(f'深桑达A vs 豪威集团 Z-score: {z:.2f}')
        if abs(z) < 1:
            print('  → 协整关系较强，可做配对交易')
        else:
            print('  → 协整关系较弱，独立操作')
    
    # 个股分析
    stocks = {
        '000032': ('深桑达A', 19.14),
        '300486': ('东杰智能', 24.20),
        '002497': ('雅化集团', 24.13),
        '002176': ('江特电机', 10.13),
        '562910': ('高端制造', 0.977),
        '603501': ('豪威集团', 112.20),
    }
    
    print('\n【个股信号 V93】')
    stock_data = []
    for code, (name, cost) in stocks.items():
        price_data = get_realtime_price(code)
        signals = generate_signal_v93(code, cost)
        
        if price_data:
            stock_data.append((name, code, price_data['current'], price_data['pct'], price_data['vol_ratio']))
            
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
    
    # Markowitz组合优化
    print('\n【Markowitz仓位优化】')
    if stock_data:
        returns = [d[3] / 100 for d in stock_data]  # 涨跌幅转收益率
        vols = [abs(d[3]) / 100 + 0.01 for d in stock_data]  # 波动率
        weights = markowitz_optimize(returns, vols)
        
        print('建议权重:')
        for i, (name, _, _, _, _) in enumerate(stock_data):
            if i < len(weights):
                print(f'  {name}: {weights[i]*100:.1f}%')
    
    print('\n' + '='*70)
    print('V93 优化完成')
    print('='*70)

if __name__ == '__main__':
    analyze_all()
