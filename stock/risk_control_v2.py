# -*- coding: utf-8 -*-
"""
股票风控模型 V2.0 - 增强版
===========================
基于业界最佳实践设计的综合风控系统

作者: 黄新民
更新: 2026-03-25
"""

# ==================== 第一部分：基础参数 ====================

# 止损止盈参数
STOP_LOSS_T1 = -7      # 第一止损线 -7%
STOP_LOSS_T2 = -10     # 第二止损线 -10%
STOP_LOSS_T3 = -15     # 第三止损线 -15% (强制清仓线)
TAKE_PROFIT_T1 = 5     # 第一止盈线 +5%
TAKE_PROFIT_T2 = 8     # 第二止盈线 +8%
TAKE_PROFIT_T3 = 15    # 第三止盈线 +15% (可以考虑分批卖出)

# 仓位管理
MAX_POSITION_PER_STOCK = 30      # 单只股票最大仓位 30%
MAX_T_POSITION = 30              # 做T最大仓位 30%
MAX_TRADES_PER_DAY = 3           # 单日最大交易次数
MAX_OPEN_POSITIONS = 5           # 最多同时持仓股票数

# 做T参数
T_STOP_LOSS = -2                 # 做T止损线 -2%
T_TAKE_PROFIT_MIN = 1.5          # 做T最小止盈 +1.5%
T_TAKE_PROFIT_MAX = 5            # 做T最大止盈 +5%
T_VOLUME_THRESHOLD = 1.3         # 放量阈值量比 > 1.3

# 大盘风控
MARKET_CRASH_THRESHOLD = -3      # 大盘暴跌阈值 -3%
MARKET_STOP_TRADING = -5          # 大盘熔断阈值 -5% (停止所有买入)

# ==================== 第二部分：风控函数 ====================

def check_stop_loss(current_pct):
    """
    止损检查
    Args:
        current_pct: 当前盈亏百分比
    Returns:
        (action, message): 操作建议和原因
    """
    if current_pct <= STOP_LOSS_T3:
        return ('强制清仓', f'亏损已达{STOP_LOSS_T3}%，必须清仓')
    elif current_pct <= STOP_LOSS_T2:
        return ('第二止损', f'亏损已达{STOP_LOSS_T2}%，建议减仓50%')
    elif current_pct <= STOP_LOSS_T1:
        return ('第一止损', f'亏损已达{STOP_LOSS_T1}%，密切关注')
    else:
        return (None, None)


def check_take_profit(current_pct):
    """
    止盈检查
    Args:
        current_pct: 当前盈亏百分比
    Returns:
        (action, message): 操作建议和原因
    """
    if current_pct >= TAKE_PROFIT_T3:
        return ('分批卖出', f'盈利已达{TAKE_PROFIT_T3}%，建议分批卖出')
    elif current_pct >= TAKE_PROFIT_T2:
        return ('第二止盈', f'盈利已达{TAKE_PROFIT_T2}%，可以卖出50%')
    elif current_pct >= TAKE_PROFIT_T1:
        return ('第一止盈', f'盈利已达{TAKE_PROFIT_T1}%，可以部分止盈')
    else:
        return (None, None)


def check_t_risk(entry_price, current_price, position_type='long'):
    """
    做T风控检查
    Args:
        entry_price: 买入价格
        current_price: 当前价格
        position_type: 'long' 做多, 'short' 做空
    Returns:
        (can_trade, action, message): 是否可以交易及原因
    """
    if position_type == 'long':
        pct = (current_price - entry_price) / entry_price * 100
    else:
        pct = (entry_price - current_price) / entry_price * 100
    
    # 止损检查
    if pct <= -T_STOP_LOSS:
        return (False, '做T止损', f'亏损{T_STOP_LOSS}%，必须止损')
    
    # 止盈检查
    if pct >= T_TAKE_PROFIT_MAX:
        return (False, '做T止盈', f'盈利{pct:.1f}%，可以止盈')
    
    # 可以交易
    if pct >= T_TAKE_PROFIT_MIN:
        return (True, '持有', f'盈利{pct:.1f}%，可继续持有')
    else:
        return (True, '持有', f'亏损{abs(pct):.1f}%，继续持有')


def check_market_risk(market_change):
    """
    大盘风险检查
    Args:
        market_change: 大盘涨跌幅
    Returns:
        (risk_level, message): 风险等级和建议
    """
    if market_change <= MARKET_STOP_TRADING:
        return ('极高', '停止所有买入操作，大盘可能熔断')
    elif market_change <= -MARKET_CRASH_THRESHOLD:
        return ('高', '建议减仓，不要新增买入')
    elif market_change <= -1:
        return ('中', '谨慎操作，注意风险')
    elif market_change >= 3:
        return ('低', '市场强势，可以积极操作')
    else:
        return ('正常', '市场正常，可以常规操作')


def calculate_position_size(total_capital, risk_per_trade=2):
    """
    仓位计算 - 基于凯利公式
    Args:
        total_capital: 总资金
        risk_per_trade: 单次交易风险承受能力百分比
    Returns:
        recommended_position: 建议仓位比例
    """
    # 简化版凯利公式
    # 假设胜率50%，盈亏比2:1
    win_rate = 0.5
    win_loss_ratio = 2
    
    kelly_pct = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
    kelly_pct = max(0, min(kelly_pct, 0.25))  # 限制在0-25%
    
    # 实际仓位 = 凯利仓位 * 风险系数
    recommended = kelly_pct * (risk_per_trade / 2) * 100
    
    return min(recommended, MAX_POSITION_PER_STOCK)


def get_risk_score(indicators):
    """
    综合风险评分
    Args:
        indicators: 技术指标字典
    Returns:
        (score, level,建议): 风险评分和等级
    """
    score = 50  # 基础分
    
    # 趋势评分
    trend = indicators.get('trend', 'neutral')
    if trend == 'up':
        score += 20
    elif trend == 'down':
        score -= 20
    
    # MACD评分
    macd = indicators.get('macd', 0)
    if macd > 0:
        score += 10
    else:
        score -= 10
    
    # RSI评分
    rsi = indicators.get('rsi', 50)
    if rsi < 30:
        score += 10  # 超卖，可能反弹
    elif rsi > 70:
        score -= 10  # 超买，注意风险
    
    # 成交量评分
    vol_ratio = indicators.get('vol_ratio', 1)
    if vol_ratio > 1.5:
        score += 5
    elif vol_ratio < 0.7:
        score -= 5
    
    # 布林带评分
    boll_position = indicators.get('boll_position', 'middle')
    if boll_position == 'lower':
        score += 10
    elif boll_position == 'upper':
        score -= 10
    
    # 风险等级
    if score >= 70:
        level = '低'
        suggestion = '积极做多'
    elif score >= 50:
        level = '中低'
        suggestion = '可以建仓'
    elif score >= 30:
        level = '中'
        suggestion = '谨慎观望'
    elif score >= 10:
        level = '中高'
        suggestion = '减仓观望'
    else:
        level = '高'
        suggestion = '禁止买入'
    
    return score, level, suggestion


# ==================== 第三部分：综合风控决策 ====================

def make_decision(current_pct, market_change, indicators):
    """
    综合风控决策
    Args:
        current_pct: 当前盈亏百分比
        market_change: 大盘涨跌幅
        indicators: 技术指标字典
    Returns:
        decision: 决策结果字典
    """
    decision = {
        'action': '持有',
        'reason': [],
        'risk_level': '中',
        'can_trade': True
    }
    
    # 1. 大盘风控
    market_risk, market_msg = check_market_risk(market_change)
    if market_risk in ['极高', '高']:
        decision['can_trade'] = False
        decision['reason'].append(f'大盘风险: {market_msg}')
    
    # 2. 止损止盈检查
    stop_action, stop_msg = check_stop_loss(current_pct)
    if stop_action:
        decision['action'] = stop_action
        decision['reason'].append(stop_msg)
    
    profit_action, profit_msg = check_take_profit(current_pct)
    if profit_action and not stop_action:
        decision['action'] = profit_action
        decision['reason'].append(profit_msg)
    
    # 3. 综合评分
    score, level, suggestion = get_risk_score(indicators)
    decision['risk_level'] = level
    
    if decision['can_trade']:
        decision['reason'].append(f'风险评分: {score}分 ({level})')
        decision['reason'].append(f'建议: {suggestion}')
    
    return decision


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 测试风控模型
    
    print("=" * 60)
    print("风控模型 V2.0 测试")
    print("=" * 60)
    
    # 测试止损止盈
    print("\n【止损止盈测试】")
    test_pcts = [-12, -8, -5, 0, 3, 6, 9, 16]
    for pct in test_pcts:
        stop_action, stop_msg = check_stop_loss(pct)
        profit_action, profit_msg = check_take_profit(pct)
        action = stop_action or profit_action or '持有'
        print(f"  盈亏{pct:+d}% -> {action}")
    
    # 测试大盘风控
    print("\n【大盘风控测试】")
    test_market = [-6, -3, -1, 0, 2, 4]
    for change in test_market:
        level, msg = check_market_risk(change)
        print(f"  大盘{change:+d}% -> {level}: {msg}")
    
    # 测试综合评分
    print("\n【综合评分测试】")
    test_indicators = [
        {'trend': 'up', 'macd': 1.5, 'rsi': 45, 'vol_ratio': 1.2, 'boll_position': 'middle'},
        {'trend': 'down', 'macd': -0.5, 'rsi': 75, 'vol_ratio': 0.6, 'boll_position': 'upper'},
    ]
    for ind in test_indicators:
        score, level, suggestion = get_risk_score(ind)
        print(f"  指标: {ind}")
        print(f"    -> 评分: {score}, 等级: {level}, 建议: {suggestion}")
