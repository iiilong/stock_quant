# A股量化回测系统

基于Python的A股量化交易回测系统，支持多种策略。

## 功能

- 多种量化策略：趋势跟踪、均值回归、动量策略、MACD策略、复合策略
- 完整回测引擎：支持止损止盈、手续费、滑点
- 绩效分析：夏普比率、最大回撤、胜率等
- 可视化：净值曲线、月度收益、策略对比
- A股数据获取：使用AKShare免费数据源

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
cd stock_quant
python main.py
```

## 配置

在 `config.py` 中修改：

- `BacktestConfig`: 回测参数（初始资金、手续费率等）
- `StrategyConfig`: 策略参数（均线周期、RSI参数等）
- `StockPool`: 股票池（默认沪深300成分股）

## 输出

回测结果保存在 `output/` 目录：

- `equity_curve.png`: 最佳策略净值曲线
- `monthly_returns.png`: 月度收益分布
- `trade_analysis.png`: 交易分析
- `strategy_comparison.png`: 策略对比

## 策略说明

1. **趋势跟踪**: 基于均线交叉，顺势交易
2. **均值回归**: 基于布林带，价格偏离后回归
3. **动量策略**: 基于价格动量和RSI
4. **MACD策略**: 基于MACD指标交叉
5. **复合策略**: 多策略投票，综合决策

## 注意事项

- 回测结果不代表未来收益
- 历史表现好的策略可能失效
- 投资有风险，入市需谨慎
- 建议先用小资金实盘验证
