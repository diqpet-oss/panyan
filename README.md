# 盘眼 PanYan — 五工具统一实时分析系统

实时股票行情监控与分析平台，整合六大金融数据源，提供技术分析、知识库分析和明日走势预测。

## 功能特性

- 📊 **实时行情面板** — 6 大指数 + 自选股实时报价，WebSocket 推送
- 🔧 **多源数据总线** — 腾讯行情、东方财富、AKShare、宝信、mootdx、Yahoo Finance，自动故障切换
- 📈 **技术分析引擎** — MA/MACD/RSI/布林带/ATR/K线形态识别/支撑阻力/50 因子评分
- 🧠 **知识库分析** — 9 大投资框架，40+ 经典书籍，行为偏差检测，历史教训
- 🔮 **明日预判** — 多空信号拆解 + 概率情景分析
- 🖥️ **暗色主题 UI** — React 19 + SVG K线图，响应式布局

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python 3.9+ / FastAPI / WebSocket |
| 前端 | React 19 / TypeScript 5.7 / Vite 6 |
| 数据 | AKShare / Tushare / Baostock / efinance / yfinance / mootdx |
| 存储 | SQLite（自选股持久化） |

## 快速启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt

cd ../frontend
npm install
```

### 2. 一键启动

```bash
chmod +x start_all.sh
./start_all.sh
```

### 3. 分别启动

**后端** (端口 9090)：
```bash
cd backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 9090
```

**前端** (端口 3000)：
```bash
cd frontend
npx vite --host 127.0.0.1 --port 3000
```

然后打开 http://localhost:3000

## API 接口

| 端点 | 说明 |
|------|------|
| `GET /api/v1/health` | 健康检查 |
| `GET /api/v1/market/overview` | 全市场快照（指数+股票+健康+告警） |
| `GET /api/v1/stock/{code}` | 单只股票实时行情 |
| `GET /api/v1/stock/search/{keyword}` | 搜索股票（代码/名称/拼音） |
| `GET /api/v1/analysis/{code}` | 综合技术分析 |
| `GET /api/v1/analysis/{code}/predict` | 明日走势预测 |
| `GET /api/v1/analysis/{code}/kline` | K线数据（含MA5/10/20） |
| `GET /api/v1/knowledge/analyze/{code}` | 知识库多维分析 |
| `GET /api/v1/knowledge/book-list` | 推荐书单 |
| `GET /api/v1/watchlist` | 获取自选股 |
| `POST /api/v1/watchlist/add` | 添加自选股 |
| `POST /api/v1/watchlist/remove` | 移除自选股 |
| `WS /ws` | WebSocket 实时推送 |

## 项目结构

```
盘眼（股票分析系统）/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── analysis.py      # 技术分析引擎
│   │   ├── quote.py          # 多源数据总线
│   │   ├── knowledge_base.py # 知识库引擎
│   │   ├── models.py         # Pydantic 数据模型
│   │   ├── config.py         # 系统配置
│   │   └── db.py             # SQLite 持久化
│   ├── data/                 # 数据库文件
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/       # 9 个 React 组件
│   └── package.json
├── start_all.sh              # 一键启动
└── README.md
```

## 免责声明

本系统仅供学习研究使用。所有分析结果基于历史数据和技术指标，不构成投资建议。股市有风险，投资需谨慎。
