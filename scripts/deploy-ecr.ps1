# AI Debate - ECR へのビルド & プッシュスクリプト
# 使用方法: .\scripts\deploy-ecr.ps1 [-Region us-east-1] [-RepoName ai-debate]

param(
    [string]$Region   = "us-east-1",
    [string]$RepoName = "ai-debate"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- AWSアカウントIDを自動取得 ---
Write-Host "AWSアカウントIDを取得中..." -ForegroundColor Cyan
$AccountId = (aws sts get-caller-identity --query Account --output text)
if (-not $AccountId) {
    Write-Error "AWS CLIの設定を確認してください（aws configure）"
    exit 1
}
Write-Host "  AccountId : $AccountId"
Write-Host "  Region    : $Region"
Write-Host "  Repository: $RepoName"

$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName"

# --- ECR ログイン ---
Write-Host "`nECRにログイン中..." -ForegroundColor Cyan
aws ecr get-login-password --region $Region |
    docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"

# --- Docker ビルド ---
Write-Host "`nDockerイメージをビルド中..." -ForegroundColor Cyan
# スクリプトの場所からリポジトリルートへ移動してビルド
$RepoRoot = Split-Path -Parent $PSScriptRoot
docker build -t $RepoName $RepoRoot

# --- タグ付け & プッシュ ---
Write-Host "`nECRへプッシュ中..." -ForegroundColor Cyan
docker tag "${RepoName}:latest" "${EcrUri}:latest"
docker push "${EcrUri}:latest"

Write-Host "`n完了!" -ForegroundColor Green
Write-Host "イメージURI: ${EcrUri}:latest"
Write-Host "`nApp Runner コンソールで「新しいデプロイを開始」を実行してください。"
