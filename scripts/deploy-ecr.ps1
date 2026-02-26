# AI Debate - Build & push to ECR
# Usage: .\scripts\deploy-ecr.ps1 [-Region us-east-1] [-RepoName ai-debate]

param(
    [string]$Region   = "us-east-1",
    [string]$RepoName = "ai-debate"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Fetch AWS account ID ---
Write-Host "Fetching AWS account ID..." -ForegroundColor Cyan
$AccountId = $(aws sts get-caller-identity --query Account --output text)
if (-not $AccountId) {exit 1}
Write-Host "  AccountId : $AccountId"
Write-Host "  Region    : $Region"
Write-Host "  Repository: $RepoName"

$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName"

# --- ECR login ---
Write-Host "`nLogging in to ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $Region |
    docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"

# --- Docker build ---
Write-Host "`nBuilding Docker image..." -ForegroundColor Cyan
# Build from repository root (parent of scripts/)
$RepoRoot = Split-Path -Parent $PSScriptRoot
docker build -t $RepoName $RepoRoot

# --- Tag & push ---
Write-Host "`nPushing to ECR..." -ForegroundColor Cyan
docker tag "${RepoName}:latest" "${EcrUri}:latest"
docker push "${EcrUri}:latest"

Write-Host "`nDone!" -ForegroundColor Green
Write-Host "Image URI: ${EcrUri}:latest"
Write-Host "Go to App Runner console and click 'Deploy'."
