#!/usr/bin/env bash
# 盘眼 (PanYan) 一键启动脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "=== 盘眼 (PanYan) 启动中 ==="

# 启动后端
echo "[Backend] Starting FastAPI on port 9090..."
cd "$SCRIPT_DIR/backend" && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 9090 --log-level info &
BACKEND_PID=$!
echo "[Backend] PID=$BACKEND_PID"

# 等待后端就绪
for i in $(seq 1 15); do
  if curl -s "http://127.0.0.1:9090/api/v1/health" >/dev/null 2>&1; then
    echo "[Backend] Ready!"
    break
  fi
  sleep 1
done

# 启动前端
echo "[Frontend] Starting Vite on port 3000..."
cd "$SCRIPT_DIR/frontend" && npx vite --host 127.0.0.1 --port 3000 &
FRONTEND_PID=$!
echo "[Frontend] PID=$FRONTEND_PID"

sleep 2
echo ""
echo "=== 盘眼 已启动 ==="
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:9090"
echo "  API:      http://localhost:9090/api/v1/market/overview"
echo "  Press Ctrl+C to stop"

wait
