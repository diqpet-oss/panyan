# 盘眼 · GitHub 部署与每日更新说明

## 一、目录结构

- `reports/` — 盯盘页、主力资金监控、工具中心、盘眼报告、Python 脚本、持仓 CSV
- `.github/workflows/daily-update.yml` — 每日自动更新工作流
- `requirements.txt` — Python 依赖（akshare/pandas/numpy）

## 二、首次发布（本地执行一次）

```bash
cd "/Users/wang/Documents/盘眼（股票分析系统）"
git remote add origin https://github.com/diqpet-oss/panyan.git
git add .
git commit -m "init: 盘眼股票分析系统"
git branch -M main
git push -u origin main
```

## 三、开启 GitHub Pages（可选，纯静态展示）

1. 仓库 → Settings → Pages
2. Source 选 `Deploy from a branch`，Branch 选 `main` / `/(root)`
3. 保存后，访问 `https://diqpet-oss.github.io/panyan/`

> 实时行情/分时/资金流是浏览器端直连腾讯/东财接口，静态托管下也会自动刷新，无需服务器。

## 四、每日自动更新

- 工作流已设为每个交易日北京时间 15:15 自动运行 `reports/主力资金监控.py`
- 它会重新抓取五路口径数据、写入 `主力资金监控_YYYYMMDD.json/.md`、并把最新面板注入 `reports/老顾盯盘.html`，然后自动提交回仓库
- 也可以在仓库 Actions 页手动点 `Run workflow` 触发

## 五、说明与限制

- 主力资金五路口径为日/季频数据（两融 T+1、股东户数/基金季度、龙虎榜盘后），每日收盘后更新一次即可
- 完整的盘眼五工具报告（Kronos/dSA/Vibe/TA-CN/TradingAgents）目前仍在本地 Mac 生成，需要 DeepSeek API 与本地 Python 环境；可后续再纳入 Actions
- 东财/新浪可能对 GitHub Actions 的服务器 IP 有偶发限流，如遇失败可稍后重跑
