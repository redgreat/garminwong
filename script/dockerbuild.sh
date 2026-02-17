#!/usr/bin/env bash

# Docker 标签发布脚本 (macOS/Linux 版本)
# 用法: ./script/dockerbuild.sh [版本标签]
# 示例: ./script/dockerbuild.sh v0.0.1

set -euo pipefail

# 颜色定义
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_RED='\033[0;31m'
readonly COLOR_RESET='\033[0m'

# 日志函数
log_info() {
    echo -e "${COLOR_BLUE}➤ $1${COLOR_RESET}"
}

log_success() {
    echo -e "${COLOR_GREEN}✔ $1${COLOR_RESET}"
}

log_warn() {
    echo -e "${COLOR_YELLOW}⚠ $1${COLOR_RESET}"
}

log_error() {
    echo -e "${COLOR_RED}✖ $1${COLOR_RESET}"
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [版本标签]
示例: $0 v0.0.3

参数:
  版本标签        Git 标签版本 (留空则自动计算)
  -h, --help     显示帮助

说明:
  此脚本会自动创建 Git 标签并推送到远程仓库,
  触发 GitHub Actions 自动构建 Docker 镜像并推送到 DockerHub 和 GHCR。
EOF
}

# 显示横幅
show_banner() {
    echo -e "${COLOR_BLUE}$(printf '=%.0s' {1..46})${COLOR_RESET}"
    echo -e "${COLOR_BLUE}Docker Tag 发布脚本${COLOR_RESET}"
    echo -e "${COLOR_BLUE}版本: ${VERSION}${COLOR_RESET}"
    echo -e "${COLOR_BLUE}$(printf '=%.0s' {1..46})${COLOR_RESET}"
}

# 检查 Git 是否安装
ensure_git() {
    if ! command -v git &> /dev/null; then
        log_error "未找到 git 命令,请先安装 Git 并确保在 PATH 中。"
        exit 1
    fi
}

# 获取最新标签(按语义版本排序)
get_latest_tag() {
    local latest_tag
    latest_tag=$(git tag --list 'v*' --sort=-version:refname 2>/dev/null | head -n 1 | tr -d '[:space:]')
    echo "${latest_tag}"
}

# 版本号递增: 优先识别 vMAJOR.MINOR.PATCH,否则对末尾数字增量
bump_version() {
    local tag="$1"
    
    # 如果标签为空,返回默认版本
    if [[ -z "${tag}" ]]; then
        echo "v0.0.1"
        return
    fi
    
    # 尝试匹配语义版本 vX.Y.Z
    if [[ "${tag}" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        local major="${BASH_REMATCH[1]}"
        local minor="${BASH_REMATCH[2]}"
        local patch="${BASH_REMATCH[3]}"
        patch=$((patch + 1))
        echo "v${major}.${minor}.${patch}"
        return
    fi
    
    # 尝试匹配末尾数字
    if [[ "${tag}" =~ ^(.*)([0-9]+)$ ]]; then
        local prefix="${BASH_REMATCH[1]}"
        local number="${BASH_REMATCH[2]}"
        number=$((number + 1))
        echo "${prefix}${number}"
        return
    fi
    
    # 无法识别格式,追加 -1
    echo "${tag}-1"
}

# 主函数
main() {
    local VERSION="${1:-}"
    
    # 处理帮助参数
    if [[ "${VERSION}" == "-h" ]] || [[ "${VERSION}" == "--help" ]]; then
        show_usage
        exit 0
    fi
    
    ensure_git
    
    # 若未提供版本参数,则自动计算
    if [[ -z "${VERSION}" ]]; then
        local latest_tag
        latest_tag=$(get_latest_tag)
        
        if [[ -n "${latest_tag}" ]]; then
            log_info "检测到当前最新标签: ${latest_tag}"
            VERSION=$(bump_version "${latest_tag}")
            log_info "自动计算版本: ${VERSION}"
        else
            log_warn "未发现任何标签,使用默认 v0.0.1"
            VERSION="v0.0.1"
        fi
    fi
    
    show_banner
    
    # 创建 Git 标签
    log_info "创建 Git 标签 ${VERSION}"
    if git rev-parse "${VERSION}" >/dev/null 2>&1; then
        log_warn "标签 ${VERSION} 已存在,跳过创建"
    else
        local current_branch
        current_branch=$(git branch --show-current)
        git tag "${VERSION}"
        log_success "标签 ${VERSION} 创建成功(分支 ${current_branch})"
    fi
    
    # 推送标签到远程
    log_info "推送标签到远程 origin"
    if git push origin "${VERSION}"; then
        log_success "标签 ${VERSION} 推送完成"
        echo ""
        log_info "GitHub Actions 将自动开始构建 Docker 镜像"
        log_info "查看进度: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
    else
        log_error "标签推送失败"
        exit 1
    fi
}

# 错误处理
trap 'log_error "脚本执行失败,退出码: $?"' ERR

# 执行主函数
main "$@"
