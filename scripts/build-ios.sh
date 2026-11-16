#!/usr/bin/env bash
# HGhub iOS 构建脚本 —— 必须在 macOS 上运行（Tauri 的 ios 命令仅支持 macOS）
# 用法：
#   chmod +x scripts/build-ios.sh
#   ./scripts/build-ios.sh                 # 默认 debugging 导出（需签名材料）
#   ./scripts/build-ios.sh release-testing # TestFlight
#   ./scripts/build-ios.sh app-store-connect
#   ./scripts/build-ios.sh sim             # 不签名，产出模拟器 .app（无 Apple 开发者账号也能出）

set -euo pipefail

MODE="${1:-debugging}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: Tauri iOS 构建仅支持 macOS，当前系统为 $(uname -s)" >&2
  exit 1
fi

echo "==> [1/6] 检查 Xcode 工具链"
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install || true
  echo "请先安装 Xcode 后重新运行本脚本" >&2
  exit 1
fi
xcodebuild -version

echo "==> [2/6] 检查 Node / pnpm / Rust"
command -v node >/dev/null || { echo "缺少 Node.js 22" >&2; exit 1; }
command -v pnpm >/dev/null || npm install -g pnpm@10.20.0
command -v rustup >/dev/null || { echo "缺少 rustup" >&2; exit 1; }
node -v && pnpm -v && rustc -V

echo "==> [3/6] 添加 iOS Rust 编译目标"
rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios

echo "==> [4/6] 安装前端依赖"
pnpm install --frozen-lockfile

echo "==> [5/6] 准备 Xcode 工程（本机生成的文件已随仓库提供）"
if [[ ! -f src-tauri/gen/apple/HGhub.xcodeproj/project.pbxproj ]]; then
  python3 scripts/generate-ios-project.py
fi
# Tauri 在 ios build 时会重新渲染 project.yml 并调用 xcodegen
if ! command -v xcodegen >/dev/null 2>&1; then
  echo "缺少 xcodegen，尝试通过 Homebrew 安装..."
  brew install xcodegen
fi

echo "==> [6/6] 构建"
IOS_APP_DIR="src-tauri/gen/apple/build/arm64-sim/debug"
case "$MODE" in
  sim)
    pnpm tauri ios build --target aarch64-sim --ci
    echo "模拟器 App: $IOS_APP_DIR"
    ;;
  debugging|release-testing|app-store-connect)
    pnpm tauri ios build --ci --export-method "$MODE"
    ;;
  *)
    echo "未知模式: $MODE（可选 sim / debugging / release-testing / app-store-connect）" >&2
    exit 1
    ;;
esac

echo "==> 产物"
find src-tauri/gen/apple -type f \( -name '*.ipa' -o -name '*.app' \) -print
