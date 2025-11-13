#!/bin/bash
# GitHub Bridge 서버 실행 스크립트 (Linux/Mac)
cd "$(dirname "$0")/../.."
python -m uvicorn package.github_bridge.main:app --host 0.0.0.0 --port 8787

