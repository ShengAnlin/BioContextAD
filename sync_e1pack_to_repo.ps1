# sync_e1pack_to_repo.ps1
# ------------------------------------------------------------
# 把 e1_pack 工作目录的最新实验内容 (60 题数据 / v2 prompt /
# results + raw cache) 同步到 BioContextAD git 仓库。
#
# 干的事:
#   1. 备份 BioContextAD 里会被覆盖的旧文件到 _backup_YYYYMMDD/
#   2. Copy e1_pack 的最新文件过去
#   3. 不执行 git commit / push,留给用户人工确认
#
# 用法:
#   PS> cd E:\BioContextAD\BioContextAD
#   PS> .\sync_e1pack_to_repo.ps1
#
# 默认路径 (按本仓库实际情况调整):
#   $Source = E:\BiomakerAD\e1_pack
#   $Target = E:\BioContextAD\BioContextAD (脚本当前所在目录)
# ------------------------------------------------------------

param(
    [string]$Source = "E:\BiomakerAD\e1_pack",
    [string]$Target = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "[step] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[ ok ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[err ] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  BioContextAD <- e1_pack sync" -ForegroundColor Cyan
Write-Host "  Source: $Source" -ForegroundColor Cyan
Write-Host "  Target: $Target" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- sanity check ---
if (-not (Test-Path $Source)) {
    Write-Err "Source not found: $Source"
    exit 1
}
if (-not (Test-Path "$Target\.git")) {
    Write-Err "Target is not a git repo (no .git folder): $Target"
    exit 1
}

# --- backup dir ---
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = Join-Path $Target "_backup_$stamp"
New-Item -ItemType Directory -Path $backup | Out-Null
Write-Ok "backup dir: $backup"

function Backup-IfExists($relpath) {
    $abs = Join-Path $Target $relpath
    if (Test-Path $abs) {
        $dst = Join-Path $backup $relpath
        $dstDir = Split-Path $dst -Parent
        if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
        Copy-Item $abs $dst -Recurse -Force
        Write-Host "       backed up: $relpath" -ForegroundColor DarkGray
    }
}

function Sync-File($relSrc, $relDst) {
    $src = Join-Path $Source $relSrc
    $dst = Join-Path $Target $relDst
    if (-not (Test-Path $src)) {
        Write-Warn "source missing, skip: $relSrc"
        return
    }
    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    Backup-IfExists $relDst
    Copy-Item $src $dst -Force
    Write-Ok  "synced: $relSrc -> $relDst"
}

function Sync-Dir($relSrc, $relDst) {
    $src = Join-Path $Source $relSrc
    $dst = Join-Path $Target $relDst
    if (-not (Test-Path $src)) {
        Write-Warn "source missing, skip dir: $relSrc"
        return
    }
    if (Test-Path $dst) {
        Backup-IfExists $relDst
    }
    if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
    Copy-Item "$src\*" $dst -Recurse -Force
    $n = (Get-ChildItem $dst -Recurse -File).Count
    Write-Ok  "synced dir: $relSrc -> $relDst ($n files)"
}

# --- data ---
Write-Step "syncing data/"
Sync-File "data\eval_questions.jsonl"        "data\eval_questions.jsonl"
Sync-File "data\eval_questions_hard.jsonl"   "data\eval_questions_hard.jsonl"
Sync-File "data\evidence_pairs.jsonl"        "data\evidence_pairs.jsonl"

# --- prompts (v2 evidence prompt overwrites v1; router unchanged) ---
Write-Step "syncing prompts/"
Sync-File "prompts\router_prompt.md"     "prompts\router_prompt.md"
Sync-File "prompts\evidence_prompt.md"   "prompts\evidence_prompt.md"

# --- results: csv / json / md / figs ---
Write-Step "syncing results/ (csv, json, md, figs)"
$resultsSrc = Join-Path $Source "results"
if (Test-Path $resultsSrc) {
    foreach ($pattern in @("*.csv", "*.json", "*.md")) {
        Get-ChildItem $resultsSrc -Filter $pattern -File -ErrorAction SilentlyContinue | ForEach-Object {
            Sync-File "results\$($_.Name)" "results\$($_.Name)"
        }
    }
    if (Test-Path (Join-Path $resultsSrc "figs")) {
        Sync-Dir "results\figs" "results\figs"
    }
} else {
    Write-Warn "no results/ in source"
}

# --- results/raw: 180+ json cache files ---
Write-Step "syncing results/raw/ (API cache)"
$rawSrc = Join-Path $Source "results\raw"
if (Test-Path $rawSrc) {
    Sync-Dir "results\raw" "results\raw"
} else {
    Write-Warn "no results/raw/ in source"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Sync complete." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps (do these BEFORE git commit):"
Write-Host "  1. python scripts\audit_cache.py        # scan cache for sensitive strings"
Write-Host "  2. git status                            # eyeball the diff"
Write-Host "  3. git add -A"
Write-Host "  4. git commit -F _meta\commit_message.txt"
Write-Host "  5. git push"
Write-Host ""
Write-Host "If anything looks wrong, restore from: $backup"
