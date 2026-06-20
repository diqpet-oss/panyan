 #!/usr/bin/env bash
 # 盘眼 后端启动脚本
 set -e
 cd "$(dirname "$0")"
 
 echo "=== 盘眼 (PanYan) 后端 ==="
 echo "启动 FastAPI 服务..."
 exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 9090 --reload --log-level info
