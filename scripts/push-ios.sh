#!/usr/bin/env bash
# 把 HGhub 源码 + iOS 构建工作流推送到目标仓库
# 用法: bash scripts/push-ios.sh git@github.com:<账号>/<仓库>.git
# 前提: 目标仓库已添加 deploy key（hghub-ios-deploy）且勾选 Write access

set -euo pipefail
REPO="${1:?请传入目标仓库 SSH 地址，例如 git@github.com:user/hghub.git}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="$HOME/.ssh/hghub_deploy_ed25519"

[[ -f "$KEY" ]] || { echo "缺少部署私钥: $KEY" >&2; exit 1; }
cd "$ROOT"

# 走 443 端口，绕开本机 22 端口被拦的问题；DNS 不通时经 HTTP 代理中转
GIT_SSH_COMMAND="ssh -i '$KEY' -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
  -o ProxyCommand=\"'/c/Program Files/Git/mingw64/bin/connect.exe' -H ${HTTPS_PROXY:-http://127.0.0.1:51038} %h %p\" \
  -o Hostname=ssh.github.com -o Port=443" \
  git push "$REPO" HEAD:refs/heads/main --force
