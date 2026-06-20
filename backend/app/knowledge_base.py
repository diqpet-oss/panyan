"""
盘眼 知识库引擎
整合70+本经典投资著作的核心原则，构建可运行的多维评分框架

框架划分（匹配用户书单十类别）：
  1. 价值投资  2. 技术分析  3. 市场与周期
  4. 行为金融  5. 交易实战  6. 基金与指数
  7. 财务与估值  8. 宏观金融  9. 传记与金融史
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("panyan.knowledge")


# ==================================================================
# 一、价值投资知识体系
# ==================================================================

class ValueInvestingFramework:
    """
    核心思想：买便宜的好公司
    来源：《聪明的投资者》《证券分析》《巴菲特致股东的信》
          《怎样选择成长股》《安全边际》《价值》《投资中最简单的事》
    """

    @staticmethod
    def score_margin_of_safety(
        price: float, intrinsic_value_est: Optional[float],
        pe_ttm: float, pb: float, industry_avg_pe: float = 20.0
    ) -> Dict[str, Any]:
        """格雷厄姆安全边际评分"""
        if intrinsic_value_est and intrinsic_value_est > 0:
            margin = (intrinsic_value_est - price) / intrinsic_value_est * 100
        else:
            # 用 PE 替代估算
            margin = (industry_avg_pe - pe_ttm) / industry_avg_pe * 100 if pe_ttm > 0 else 0

        score = min(max(int(margin / 5), 0), 10)  # 每5%安全边际得1分

        tags = []
        if margin >= 30:
            tags.append("深度安全边际")
        elif margin >= 15:
            tags.append("合理安全边际")
        elif margin >= 0:
            tags.append("轻微低估")
        else:
            tags.append("无安全边际(高估)")

        return {
            "margin_pct": round(margin, 1),
            "score": score,
            "tags": tags,
            "principle": "永远以低于内在价值的价格买入，留足容错空间",
            "source": "《聪明的投资者》— 本杰明·格雷厄姆",
        }

    @staticmethod
    def score_economic_moat(
        pe_ttm: float, pb: float, roe: Optional[float],
        gross_margin: Optional[float], turnover_rate: float
    ) -> Dict[str, Any]:
        """巴菲特护城河评分"""
        score = 0
        signals = []

        # 高ROE → 护城河强
        if roe and roe > 20:
            score += 3
            signals.append("高ROE → 强护城河")
        elif roe and roe > 15:
            score += 2
            signals.append("中等护城河")
        elif roe and roe > 10:
            score += 1
            signals.append("弱护城河")

        # 高毛利率 → 定价权
        if gross_margin and gross_margin > 40:
            score += 2
            signals.append("高毛利 → 定价权强")
        elif gross_margin and gross_margin > 25:
            score += 1
            signals.append("中等毛利")

        # 低换手率 → 长线持有者多
        if turnover_rate < 2:
            score += 1
            signals.append("低换手 → 长线资金")
        elif turnover_rate > 10:
            signals.append("高换手 → 短线博弈")

        # PE/PB 组合判断溢价
        if pe_ttm > 50 and pb > 5:
            signals.append("双高溢价 → 市场预期极高")
        elif pe_ttm < 15 and pb < 2:
            signals.append("双低估值 → 可能被市场忽视")

        return {
            "score": min(score, 10),
            "signals": signals,
            "principle": "投资具有持久竞争优势的企业，护城河比短期增长更重要",
            "source": "《巴菲特致股东的信》— 沃伦·巴菲特",
        }

    @staticmethod
    def score_can_slim(
        change_pct_1m: Optional[float], change_pct_3m: Optional[float],
        volume_ratio: float, eps_growth: Optional[float],
        industry_rank: Optional[int] = None
    ) -> Dict[str, Any]:
        """威廉·欧奈尔 CAN SLIM 系统评分"""
        score = 0
        checks = []

        # C = 当前季度每股收益
        if eps_growth and eps_growth > 25:
            score += 2
            checks.append("C ✓ EPS增长>25%")
        elif eps_growth and eps_growth > 0:
            checks.append("C △ EPS正增长但不足25%")

        # A = 年度收益增长
        if change_pct_3m and change_pct_3m > 20:
            score += 2
            checks.append("A ✓ 3月涨幅>20%")
        elif change_pct_3m and change_pct_3m > 0:
            checks.append("A △ 年度正收益")

        # N = 新东西（新产品/新高）
        if change_pct_1m and change_pct_1m > 10:
            score += 1
            checks.append("N ✓ 近期强势(新资金关注)")

        # S = 供需关系
        if volume_ratio > 1.5:
            score += 2
            checks.append("S ✓ 放量上涨(需求旺盛)")
        elif volume_ratio < 0.5:
            checks.append("S △ 缩量(可能缺乏动能)")

        # L = 龙头或滞后
        if industry_rank and industry_rank <= 3:
            score += 2
            checks.append("L ✓ 行业龙头(前3)")
        elif industry_rank and industry_rank > 10:
            checks.append("L △ 非行业领先")

        # I = 机构认同
        # M = 市场方向

        return {
            "score": min(score, 10),
            "checks": checks,
            "principle": "CAN SLIM 七因子系统，寻找机构认可的强势成长股",
            "source": "《笑傲股市》— 威廉·欧奈尔",
        }

    @staticmethod
    def score_magic_formula(market_cap: float, pe_ttm: float, roe: Optional[float]) -> Dict[str, Any]:
        """乔尔·格林布拉特神奇公式"""
        score = 0

        # 低PE + 高ROE = 好生意 + 好价格
        if pe_ttm < 15 and roe and roe > 15:
            score = 9
            verdict = "神奇公式目标：低PE高ROE优质股"
        elif pe_ttm < 20 and roe and roe > 10:
            score = 6
            verdict = "合理范围内"
        elif pe_ttm > 30:
            score = 2
            verdict = "高PE，不符合神奇公式标准"
        else:
            score = 4
            verdict = "一般"

        return {
            "score": score,
            "pe_ttm": pe_ttm,
            "roe": roe,
            "verdict": verdict,
            "principle": "按低PE和高ROE排序，分散买入排名靠前的公司",
            "source": "《股市稳赚》— 乔尔·格林布拉特",
        }

    @staticmethod
    def score_peter_lynch(
        pe_ttm: float, eps_growth: Optional[float],
        dividend_yield: Optional[float], market_cap: float
    ) -> Dict[str, Any]:
        """彼得·林奇 PEG & 分类评估"""
        # 计算 PEG
        peg = pe_ttm / eps_growth if eps_growth and eps_growth > 0 else None
        score = 0
        classification = ""

        # 分类
        cap_class = "大盘股" if market_cap > 10000000 else "中盘股" if market_cap > 1000000 else "小盘股"

        if peg and peg < 1:
            score += 4
            classification = "稳健增长型(被低估)"
        elif peg and peg < 1.5:
            score += 3
            classification = "稳健增长型(合理)"
        elif peg and peg < 2:
            score += 2
            classification = "增长型(略贵)"
        else:
            classification = "增长型(可能高估)"

        if dividend_yield and dividend_yield > 3:
            score += 2
            classification += " + 高股息"
        elif dividend_yield and dividend_yield > 1:
            score += 1

        # 困境反转型判断
        # 低PE + 有底部特征
        if pe_ttm < 10 and eps_growth and eps_growth > 0:
            score += 2
            classification += " (可能困境反转)"

        return {
            "score": min(score, 10),
            "peg": round(peg, 2) if peg else None,
            "classification": classification,
            "cap_class": cap_class,
            "principle": "不同类别股票用不同估值方法，PEG<1是最佳买入点",
            "source": "《彼得·林奇的成功投资》— 彼得·林奇",
        }

    @staticmethod
    def value_rating_aggregate(**kwargs) -> Dict[str, Any]:
        """价值投资综合评级"""
        scores = []
        details = {}

        for key, result in kwargs.items():
            if isinstance(result, dict) and "score" in result:
                scores.append(result["score"])
                details[key] = result

        avg = sum(scores) / len(scores) if scores else 0
        if avg >= 8:
            rating = "强烈买入"
        elif avg >= 6:
            rating = "买入"
        elif avg >= 4:
            rating = "观望"
        elif avg >= 2:
            rating = "避免"
        else:
            rating = "强烈避免"

        return {
            "avg_score": round(avg, 1),
            "rating": rating,
            "details": details,
            "principle_summary": "价值投资核心：以合理价格买入优质企业，长期持有",
        }


# ==================================================================
# 二、技术分析知识体系
# ==================================================================

class TechnicalAnalysisFramework:
    """
    核心思想：看趋势与价格行为
    来源：《日本蜡烛图技术》《股市趋势技术分析》《期货市场技术分析》
          《笑傲股市》《专业投机原理》《海龟交易法则》《量价分析》
    """

    @staticmethod
    def trend_strength(
        ma_short: float, ma_mid: float, ma_long: float,
        price: float, volume_trend: str = "normal"
    ) -> Dict[str, Any]:
        """道氏理论趋势强度评分"""
        score = 0
        signals = []

        # 多头排列
        if ma_short > ma_mid > ma_long:
            score += 3
            signals.append("多头排列(趋势向上)")
        elif ma_short > ma_mid and price > ma_short:
            score += 2
            signals.append("短期趋势向上")
        elif ma_long > ma_mid > ma_short:
            score -= 2
            signals.append("空头排列(趋势向下)")
        elif ma_long > ma_short:
            score -= 1
            signals.append("中期偏空")

        # 价格相对均线位置
        if price > ma_short * 1.05:
            score += 1
            signals.append("价格远离均线(强势)")
        elif price < ma_short * 0.95:
            score -= 1
            signals.append("价格跌破均线(弱势)")

        # 成交量确认
        if volume_trend == "expanding":
            score += 1
            signals.append("量能扩张 → 趋势有支撑")

        return {
            "score": max(min(score, 10), -10),
            "signals": signals,
            "direction": "strong_up" if score > 3 else "up" if score > 0 else "neutral" if score == 0 else "down" if score > -3 else "strong_down",
            "principle": "趋势是你的朋友，不逆势交易",
            "source": "《股市趋势技术分析》— 罗伯特·爱德华兹/约翰·迈吉",
        }

    @staticmethod
    def volume_price_analysis(
        price_change: float, volume_ratio: float,
        is_breakout: bool = False
    ) -> Dict[str, Any]:
        """量价关系分析"""
        vp_type = ""
        interpretation = ""

        if price_change > 0 and volume_ratio > 1.5:
            vp_type = "价涨量增(健康)"
            interpretation = "买方力量强劲，趋势可持续"
        elif price_change > 0 and volume_ratio < 0.8:
            vp_type = "价涨量缩(背离)"
            interpretation = "上涨动能减弱，可能回调"
        elif price_change < 0 and volume_ratio > 1.5:
            vp_type = "价跌量增(恐慌)"
            interpretation = "卖压沉重，可能继续下跌"
        elif price_change < 0 and volume_ratio < 0.8:
            vp_type = "价跌量缩(正常)"
            interpretation = "卖压衰减，可能见底"
        elif abs(price_change) < 0.5 and volume_ratio > 1.5:
            vp_type = "放量滞涨(出货)"
            interpretation = "主力可能在派发筹码"

        alert = ""
        if is_breakout and volume_ratio > 2:
            alert = "放量突破！有效信号"
        elif is_breakout and volume_ratio < 1:
            alert = "无量突破 → 假突破可能"

        return {
            "type": vp_type,
            "interpretation": interpretation,
            "alert": alert,
            "volume_ratio": round(volume_ratio, 2),
            "principle": "成交量是价格的先行指标，量在价先",
            "source": "《量价分析》— 安娜·库林",
        }

    @staticmethod
    def candlestick_pattern_meaning(pattern: str) -> Dict[str, Any]:
        """K线形态含义解读"""
        pattern_map = {
            "doji": {
                "meaning": "十字星 — 多空平衡，趋势可能反转",
                "strength": "中等",
                "action": "减仓观望",
            },
            "hammer": {
                "meaning": "锤子线 — 下跌后底部承接，看涨反转",
                "strength": "强",
                "action": "买入(需次日确认)",
            },
            "hanging_man": {
                "meaning": "吊颈线 — 上涨后抛压出现，看跌反转",
                "strength": "强",
                "action": "卖出或减仓",
            },
            "engulfing_bull": {
                "meaning": "阳包阴 — 多方完全覆盖空方，强烈看涨",
                "strength": "很强",
                "action": "买入",
            },
            "engulfing_bear": {
                "meaning": "阴包阳 — 空方完全覆盖多方，强烈看跌",
                "strength": "很强",
                "action": "卖出",
            },
            "morning_star": {
                "meaning": "晨星 — 底部反转信号，看涨",
                "strength": "很强",
                "action": "买入",
            },
            "evening_star": {
                "meaning": "暮星 — 顶部反转信号，看跌",
                "strength": "很强",
                "action": "卖出",
            },
            "shooting_star": {
                "meaning": "射击之星 — 上涨后长上影，看跌反转",
                "strength": "强",
                "action": "减仓",
            },
            "marubozu_bull": {
                "meaning": "光头光脚阳线 — 买方强势控制全天",
                "strength": "强",
                "action": "持有或加仓",
            },
            "marubozu_bear": {
                "meaning": "光头光脚阴线 — 卖方强势控制全天",
                "strength": "强",
                "action": "卖出",
            },
        }

        p = pattern_map.get(pattern, {
            "meaning": f"{pattern} — 参考K线形态",
            "strength": "待确认",
            "action": "观望",
        })
        p["principle"] = "K线是市场情绪的直接表达，组合形态比单根更有意义"
        p["source"] = "《日本蜡烛图技术》— 史蒂夫·尼森"
        return p

    @staticmethod
    def support_resistance_analysis(
        price: float, support: float, resistance: float,
        atr: Optional[float] = None
    ) -> Dict[str, Any]:
        """支撑阻力分析"""
        # 价格在支撑阻力之间的位置
        if support and resistance and resistance > support:
            position_pct = (price - support) / (resistance - support) * 100
        else:
            position_pct = 50

        if price <= support * 1.02:
            zone = "支撑区"
            action = "关注支撑有效性，跌破止损"
        elif price >= resistance * 0.98:
            zone = "阻力区"
            action = "突破确认可加仓，受阻减仓"
        elif 30 < position_pct < 70:
            zone = "中间区"
            action = "观望，等待回踩或突破"
        else:
            zone = "过渡区"
            action = "区间交易"

        risk = ""
        if atr:
            stop_loss = round(price - 2 * atr, 2)
            take_profit = round(price + 3 * atr, 2)
            risk_reward = round((take_profit - price) / (price - stop_loss), 2) if price > stop_loss else 0
            risk = f"止损{stop_loss} → 止盈{take_profit} (盈亏比{risk_reward})"

        return {
            "zone": zone,
            "action": action,
            "support": round(support, 2) if support else None,
            "resistance": round(resistance, 2) if resistance else None,
            "position_pct": round(position_pct, 1),
            "risk_analysis": risk,
            "principle": "支撑和阻力的角色互换，突破后的阻力变支撑",
            "source": "《期货市场技术分析》— 约翰·墨菲",
        }


# ==================================================================
# 三、市场与周期知识体系
# ==================================================================

class MarketCycleFramework:
    """
    核心思想：理解大势，顺周期而为
    来源：《周期》《非理性繁荣》《金融炼金术》《黑天鹅》《反脆弱》
          《大空头》《漫步华尔街》《股市长线法宝》
    """

    @staticmethod
    def cycle_position_score(
        pe_avg: Optional[float], pe_historical_avg: float = 17.0,
        sentiment: str = "neutral",
        volatility_index: Optional[float] = None
    ) -> Dict[str, Any]:
        """霍华德·马克斯周期定位"""
        # 估值分位
        if pe_avg and pe_historical_avg > 0:
            pe_ratio = pe_avg / pe_historical_avg
        else:
            pe_ratio = 1.0

        if pe_ratio > 1.5:
            valuation_phase = "高估"
            valuation_score = -3
        elif pe_ratio > 1.2:
            valuation_phase = "偏高"
            valuation_score = -1
        elif pe_ratio > 0.8:
            valuation_phase = "合理"
            valuation_score = 1
        elif pe_ratio > 0.6:
            valuation_phase = "低估"
            valuation_score = 3
        else:
            valuation_phase = "极度低估"
            valuation_score = 4

        # 情绪修正
        sentiment_score = {"fear": 3, "neutral": 0, "greed": -3, "panic": 4, "euphoria": -4}
        s_score = sentiment_score.get(sentiment, 0)

        total_score = valuation_score + s_score

        if total_score >= 5:
            position = "极度看多(买入区)"
        elif total_score >= 2:
            position = "看多(逐步建仓)"
        elif total_score >= -1:
            position = "中性(持有)"
        elif total_score >= -4:
            position = "看空(减仓)"
        else:
            position = "极度看空(清仓/对冲)"

        return {
            "position": position,
            "score": total_score,
            "valuation_phase": valuation_phase,
            "sentiment_assessment": sentiment,
            "principle": "周期不会消失，但会被遗忘。在别人恐惧时贪婪，在别人贪婪时恐惧",
            "source": "《周期》— 霍华德·马克斯",
        }

    @staticmethod
    def black_swan_awareness(
        volatility: Optional[float], leverage_ratio: Optional[float],
        concentration_count: int = 10
    ) -> Dict[str, Any]:
        """黑天鹅风险意识"""
        flags = []

        if concentration_count <= 3:
            flags.append("⚠ 持仓高度集中(纳西姆·塔勒布警告)")
        if leverage_ratio and leverage_ratio > 2:
            flags.append("⚠ 高杠杆(黑天鹅下必爆仓)")
        if volatility and volatility > 40:
            flags.append("⚠ 高波动环境(尾部风险大)")

        if flags:
            advice = "减小仓位，增加现金，使用对冲"
        else:
            advice = "风险可控，保持警惕"

        return {
            "flags": flags,
            "advice": advice,
            "principle": "黑天鹅不可预测，但可以做好准备——杠铃策略",
            "source": "《黑天鹅》《反脆弱》— 纳西姆·塔勒布",
        }


# ==================================================================
# 四、行为金融学知识体系
# ==================================================================

class BehavioralFinanceFramework:
    """
    核心思想：人性决定盈亏
    来源：《思考，快与慢》《错误的行为》《投资心理学》
          《乌合之众》《决策与判断》《交易心理学》
    """

    @staticmethod
    def detect_biases(
        recent_return: float, portfolio_turnover: float,
        has_stop_loss: bool, avg_holding_days: int,
        max_drawdown: float, trade_frequency: str = "medium"
    ) -> Dict[str, Any]:
        """行为偏差检测"""
        biases = []
        severity = 0

        # 过度自信
        if recent_return > 30 and trade_frequency == "high":
            biases.append({
                "bias": "过度自信",
                "description": "近期盈利可能导致过度交易",
                "severity": 3,
                "mitigation": "回顾交易记录，检查每笔决策依据",
                "book": "《思考，快与慢》— 丹尼尔·卡尼曼",
            })
            severity += 3

        # 损失厌恶
        if not has_stop_loss:
            biases.append({
                "bias": "损失厌恶(未设止损)",
                "description": "不愿认错，让亏损扩大",
                "severity": 4,
                "mitigation": "每笔交易前预设止损位，严格执行",
                "book": "《错误的行为》— 理查德·塞勒",
            })
            severity += 4

        # 处置效应
        if portfolio_turnover > 100 and recent_return > 0:
            biases.append({
                "bias": "处置效应",
                "description": "过早卖出盈利股，死扛亏损股",
                "severity": 2,
                "mitigation": "让利润奔跑，截断亏损",
                "book": "《投资心理学》— 约翰·诺夫辛格",
            })
            severity += 2

        # 锚定效应
        if avg_holding_days < 3:
            biases.append({
                "bias": "锚定效应",
                "description": "过短持仓可能受短期价格波动影响",
                "severity": 2,
                "mitigation": "以买入逻辑而非价格作为持有依据",
                "book": "《思考，快与慢》— 丹尼尔·卡尼曼",
            })
            severity += 2

        # 确认偏差
        biases.append({
            "bias": "确认偏差(通用提醒)",
            "description": "倾向于寻找支持自己观点的信息",
            "severity": 1,
            "mitigation": "主动寻找反面论据，进行压力测试",
            "book": "《思考，快与慢》— 丹尼尔·卡尼曼",
        })

        # 羊群效应（群体启发）
        if trade_frequency == "high":
            biases.append({
                "bias": "羊群效应",
                "description": "高频交易可能受群体情绪驱动",
                "severity": 2,
                "mitigation": "独立判断，避免跟风",
                "book": "《乌合之众》— 古斯塔夫·勒庞",
            })
            severity += 2

        bias_count = len([b for b in biases if b["severity"] >= 3])
        return {
            "active_biases": biases,
            "bias_count": len(biases),
            "high_risk_biases": bias_count,
            "severity_level": "高" if severity >= 6 else "中" if severity >= 3 else "低",
            "principle": "认识自己的认知偏差是克服它们的第一步",
        }


# ==================================================================
# 五、交易实战知识体系
# ==================================================================

class TradingFramework:
    """
    核心思想：执行与纪律
    来源：《股票大作手回忆录》《海龟交易法则》《以交易为生》
          《通向财务自由之路》《幽灵的礼物》《短线交易秘诀》
    """

    @staticmethod
    def trading_rules_checklist(
        has_plan: bool = False, has_stop_loss: bool = False,
        position_size_pct: float = 100,
        uses_trailing_stop: bool = False
    ) -> Dict[str, Any]:
        """交易纪律检查"""
        violations = []
        score = 10

        if not has_plan:
            violations.append("❌ 没有交易计划 → 凭感觉交易")
            score -= 3
        if not has_stop_loss:
            violations.append("❌ 没有止损 → 小亏变大亏")
            score -= 3
        if position_size_pct > 30:
            violations.append(f"⚠ 单笔仓位{position_size_pct}% > 30% → 过度集中")
            score -= 2
        if not uses_trailing_stop:
            violations.append("ℹ 建议使用移动止盈保护利润")
            score -= 1

        return {
            "discipline_score": max(score, 0),
            "violations": violations,
            "principle": "计划你的交易，交易你的计划",
            "sources": ["《股票大作手回忆录》— 埃德温·勒费弗",
                        "《海龟交易法则》— 柯蒂斯·费思"],
        }

    @staticmethod
    def position_sizing(kelly_fraction: float = 0.25,
                        win_rate: float = 0.5,
                        avg_win: float = 1.0, avg_loss: float = 1.0) -> Dict[str, Any]:
        """凯利公式仓位管理"""
        # 凯利公式: f* = (p*b - q) / b
        if avg_loss > 0:
            b = avg_win / avg_loss
            p = win_rate
            q = 1 - p
            kelly_pct = (p * b - q) / b if b > 0 else 0
        else:
            kelly_pct = 0

        fractional = kelly_pct * kelly_fraction  # 分仓凯利
        return {
            "full_kelly_pct": round(max(kelly_pct, 0) * 100, 1),
            "suggested_pct": round(max(fractional, 0) * 100, 1),
            "risk_level": "保守" if kelly_pct * kelly_fraction < 0.1 else "适中" if kelly_pct * kelly_fraction < 0.25 else "激进",
            "principle": "使用分仓凯利公式控制仓位，永远不要押上全部",
            "source": "《通向财务自由之路》— 范·撒普",
        }


# ==================================================================
# 六、基金与指数投资
# ==================================================================

class IndexInvestingFramework:
    """
    核心思想：普通人最优解
    来源：《共同基金常识》《约翰·博格的投资50年》
          《指数基金投资指南》《不落俗套的成功》
    """

    @staticmethod
    def index_allocation_advice(
        age: int = 30, risk_tolerance: str = "medium",
        time_horizon_years: int = 10
    ) -> Dict[str, Any]:
        """资产配置建议"""
        bond_pct = age  # 年龄=债券比例
        stock_pct = 100 - age

        if time_horizon_years < 3:
            stock_pct = max(stock_pct * 0.5, 20)
            bond_pct = 100 - stock_pct

        return {
            "equity_pct": stock_pct,
            "bond_pct": bond_pct,
            "suggested_mix": f"{stock_pct}%宽基指数 + {bond_pct}%债券/货币基金",
            "annual_cost_saving": "选择费率<0.15%的指数基金，10年节省约15%收益",
            "principle": "成本是确定的，收益是不确定的。控制成本是你能做的唯一确定的事",
            "source": "《共同基金常识》— 约翰·博格",
        }


# ==================================================================
# 七、财务与估值
# ==================================================================

class FinancialHealthFramework:
    """
    核心思想：看懂公司
    来源：《巴菲特教你读财报》《财务报表分析与证券估值》
          《财报就像一本故事书》《手把手教你读财报》
    """

    @staticmethod
    def balance_sheet_health(
        debt_ratio: Optional[float] = None,
        current_ratio: Optional[float] = None,
        cash_ratio: Optional[float] = None
    ) -> Dict[str, Any]:
        """资产负债表健康度"""
        score = 5
        flags = []

        if debt_ratio is not None:
            if debt_ratio > 70:
                score -= 3
                flags.append(f"❌ 资产负债率{debt_ratio}%(>70%) → 高杠杆风险")
            elif debt_ratio > 50:
                score -= 1
                flags.append(f"⚠ 负债率{debt_ratio}%(偏高)")
            elif debt_ratio < 30:
                score += 2
                flags.append(f"✓ 低负债率{debt_ratio}%(财务稳健)")

        if current_ratio is not None:
            if current_ratio > 2:
                score += 1
                flags.append(f"✓ 流动比率{current_ratio}(>2) → 短期偿债能力强")
            elif current_ratio < 1:
                score -= 2
                flags.append(f"❌ 流动比率{current_ratio}(<1) → 短期偿债风险")

        if cash_ratio is not None and cash_ratio > 0.3:
            score += 1
            flags.append(f"✓ 现金充裕(占比{cash_ratio*100:.0f}%)")

        return {
            "health_score": score,
            "max_score": 10,
            "flags": flags,
            "rating": "健康" if score >= 7 else "一般" if score >= 4 else "危险",
            "principle": "现金为王，负债是刀。好的公司负债率低、流动性强",
            "source": "《巴菲特教你读财报》— 玛丽·巴菲特",
        }

    @staticmethod
    def profitability_quality(
        roe: Optional[float] = None, gross_margin: Optional[float] = None,
        net_margin: Optional[float] = None,
        revenue_growth: Optional[float] = None
    ) -> Dict[str, Any]:
        """盈利能力质量"""
        score = 5

        if roe is not None:
            if roe > 20:
                score += 3
            elif roe > 15:
                score += 2
            elif roe > 10:
                score += 1
            else:
                score -= 1

        if gross_margin is not None:
            if gross_margin > 60:
                score += 2
            elif gross_margin > 40:
                score += 1

        if net_margin is not None:
            if net_margin > 15:
                score += 1

        if revenue_growth is not None:
            if revenue_growth > 20:
                score += 2
            elif revenue_growth > 10:
                score += 1
            elif revenue_growth < 0:
                score -= 2

        return {
            "profitability_score": min(score, 10),
            "rating": "优秀" if score >= 8 else "良好" if score >= 6 else "一般" if score >= 4 else "较差",
            "principle": "持续高ROE是优秀企业的核心特征，毛利高代表护城河",
            "source": "《手把手教你读财报》— 唐朝",
        }


# ==================================================================
# 八、宏观金融
# ==================================================================

class MacroFramework:
    """
    核心思想：理解世界运行
    来源：《货币金融学》《金融的本质》《这次不一样》《货币、权力与人》
    """

    @staticmethod
    def macro_regime_check(
        inflation_rate: Optional[float] = None,
        interest_rate: Optional[float] = None,
        gdp_growth: Optional[float] = None,
        credit_spread: Optional[float] = None
    ) -> Dict[str, Any]:
        """宏观制度检查"""
        regime = "正常"
        flags = []

        if inflation_rate is not None:
            if inflation_rate > 5:
                regime = "滞涨风险"
                flags.append(f"⚠ 高通胀{inflation_rate}% → 不利于股票估值")
            elif inflation_rate > 3:
                regime = "通胀偏高"
                flags.append(f"△ 通胀{inflation_rate}% → 关注加息节奏")

        if interest_rate is not None and interest_rate > 5:
            flags.append(f"⚠ 高利率{interest_rate}% → 压制估值")

        if gdp_growth is not None and gdp_growth < 3:
            flags.append("△ 经济增速放缓 → 关注防御性资产")

        if credit_spread is not None and credit_spread > 4:
            flags.append("⚠ 信用利差扩大 → 市场风险厌恶增加")

        return {
            "regime": regime,
            "flags": flags,
            "principle": "不要与美联储对抗。宏观环境决定70%的资产价格走势",
            "source": "《金融的本质》— 本·伯南克",
        }


# ==================================================================
# 九、传记与金融史教训
# ==================================================================

class HistoryLessonsFramework:
    """
    核心思想：从历史中学习
    来源：《滚雪球》《门口的野蛮人》《伟大的博弈》《激荡三十年》
    """

    @staticmethod
    def historical_lessons() -> List[Dict[str, str]]:
        return [
            {
                "lesson": "没有人能每次都预测市场",
                "story": "巴菲特承认自己也没有成功预测过市场顶部或底部",
                "action": "放弃择时，专注于持有优质资产",
                "book": "《滚雪球》— 艾丽斯·施罗德",
            },
            {
                "lesson": "杠杆是毁灭的根源",
                "story": "LTCM和雷曼兄弟的教训——高杠杆在极端行情下瞬间归零",
                "action": "永远不使用借来的钱投资股票",
                "book": "《伟大的博弈》— 约翰·戈登",
            },
            {
                "lesson": "市场恐慌时买入，疯狂时卖出",
                "story": "2008年金融危机和2015年A股股灾的历史重复",
                "action": "建立自己的恐惧-贪婪指标",
                "book": "《激荡三十年》— 吴晓波",
            },
            {
                "lesson": "控制你能控制的——成本和行为",
                "story": "频繁交易和追涨杀跌是散户亏损的两大原因",
                "action": "减少交易频率，坚持定投",
                "book": "《巴菲特传》— 罗杰·洛温斯坦",
            },
        ]


# ==================================================================
# 综合知识评分引擎
# ==================================================================

class KnowledgeEngine:
    """整合全部知识框架的综合引擎"""

    def __init__(self):
        self.value = ValueInvestingFramework()
        self.tech = TechnicalAnalysisFramework()
        self.cycle = MarketCycleFramework()
        self.behavior = BehavioralFinanceFramework()
        self.trading = TradingFramework()
        self.index = IndexInvestingFramework()
        self.finance = FinancialHealthFramework()
        self.macro = MacroFramework()
        self.history = HistoryLessonsFramework()

    def analyze_stock(self, quote_data: Dict[str, Any], kline_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        对单只股票执行全知识库分析

        输入:
          quote_data: {price, change_pct, pe_ttm, turnover_rate, ...}
          kline_data: {closes, volumes, ma5, ma10, ...} (可选)
        """
        results = {}
        price = quote_data.get("price", 0)
        pe_ttm = quote_data.get("pe_ttm", 20)
        turnover = quote_data.get("turnover_rate", 5)
        change_pct = quote_data.get("change_pct", 0)

        # 一、价值投资评分
        results["安全边际"] = self.value.score_margin_of_safety(
            price=price,
            intrinsic_value_est=quote_data.get("intrinsic_value"),
            pe_ttm=pe_ttm, pb=quote_data.get("pb", 1),
        )
        results["护城河"] = self.value.score_economic_moat(
            pe_ttm=pe_ttm, pb=quote_data.get("pb", 1),
            roe=quote_data.get("roe"), gross_margin=quote_data.get("gross_margin"),
            turnover_rate=turnover,
        )
        results["CAN_SLIM"] = self.value.score_can_slim(
            change_pct_1m=quote_data.get("change_pct_1m"),
            change_pct_3m=quote_data.get("change_pct_3m"),
            volume_ratio=quote_data.get("volume_ratio", 1),
            eps_growth=quote_data.get("eps_growth"),
        )
        results["神奇公式"] = self.value.score_magic_formula(
            market_cap=quote_data.get("market_cap", 0),
            pe_ttm=pe_ttm, roe=quote_data.get("roe"),
        )
        results["彼得林奇"] = self.value.score_peter_lynch(
            pe_ttm=pe_ttm, eps_growth=quote_data.get("eps_growth"),
            dividend_yield=quote_data.get("dividend_yield"),
            market_cap=quote_data.get("market_cap", 0),
        )

        # 二、技术分析
        if kline_data:
            results["趋势强度"] = self.tech.trend_strength(
                ma_short=kline_data.get("ma5", price),
                ma_mid=kline_data.get("ma10", price),
                ma_long=kline_data.get("ma20", price),
                price=price,
                volume_trend=kline_data.get("volume_trend", "normal"),
            )
            results["量价分析"] = self.tech.volume_price_analysis(
                price_change=change_pct,
                volume_ratio=quote_data.get("volume_ratio", 1),
            )
            if kline_data.get("support") and kline_data.get("resistance"):
                results["支撑阻力"] = self.tech.support_resistance_analysis(
                    price=price,
                    support=kline_data["support"],
                    resistance=kline_data["resistance"],
                    atr=kline_data.get("atr"),
                )

        # 三、财务健康
        results["资产负债表"] = self.finance.balance_sheet_health(
            debt_ratio=quote_data.get("debt_ratio"),
            current_ratio=quote_data.get("current_ratio"),
            cash_ratio=quote_data.get("cash_ratio"),
        )
        results["盈利能力"] = self.finance.profitability_quality(
            roe=quote_data.get("roe"),
            gross_margin=quote_data.get("gross_margin"),
            net_margin=quote_data.get("net_margin"),
            revenue_growth=quote_data.get("revenue_growth"),
        )

        # 四、综合评分
        value_scores = [v.get("score", 5) for v in results.values() if isinstance(v, dict) and "score" in v]
        total_avg = sum(value_scores) / len(value_scores) if value_scores else 0

        # 生成总评
        if total_avg >= 7.5:
            overall = "强烈推荐 ⭐⭐⭐⭐⭐"
            confidence = "高"
        elif total_avg >= 6:
            overall = "推荐 ⭐⭐⭐⭐"
            confidence = "较高"
        elif total_avg >= 4.5:
            overall = "中性 ⭐⭐⭐"
            confidence = "中等"
        elif total_avg >= 3:
            overall = "谨慎 ⭐⭐"
            confidence = "较低"
        else:
            overall = "避免 ⭐"
            confidence = "低"

        return {
            "stock_code": quote_data.get("code", ""),
            "stock_name": quote_data.get("name", ""),
            "overall_rating": overall,
            "confidence": confidence,
            "total_score": round(total_avg, 1),
            "framework_breakdown": results,
            "applicable_books": self._get_relevant_books(results),
        }

    def _get_relevant_books(self, results: Dict) -> List[Dict[str, str]]:
        """根据分析结果推荐相关书籍"""
        books = []

        # 价值投资
        for key in ["安全边际", "护城河", "神奇公式"]:
            r = results.get(key, {})
            if isinstance(r, dict) and r.get("score", 5) >= 7:
                if "source" in r:
                    books.append({"book": r["source"], "relevance": "价值投资"})
                break

        # 技术分析
        for key in ["趋势强度", "量价分析"]:
            r = results.get(key, {})
            if isinstance(r, dict):
                if "source" in r:
                    books.append({"book": r["source"], "relevance": "技术分析"})
                break

        # 行为金融
        r = results.get("行为偏差", {})
        if isinstance(r, dict) and r.get("high_risk_biases", 0) > 0:
            for b in r.get("active_biases", []):
                if b.get("severity", 0) >= 3:
                    books.append({"book": b.get("book", ""), "relevance": "行为金融"})

        return books[:6]  # 最多推荐6本

    def get_reading_path(self) -> Dict[str, Any]:
        """返回推荐阅读路径"""
        return {
            "入门(建立认知)": ["《投资最重要的事》", "《漫步华尔街》", "《思考，快与慢》"],
            "进阶(学会选股)": ["《聪明的投资者》", "《彼得·林奇的成功投资》"],
            "提高(学会交易)": ["《海龟交易法则》", "《以交易为生》"],
            "高阶(看周期)": ["《周期》", "《黑天鹅》"],
            "终身学习": ["《穷查理宝典》", "《股票大作手回忆录》"],
        }
