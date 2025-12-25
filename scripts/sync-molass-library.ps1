# Synchronize molass-library subtree with upstream joss-paper branch
# This script automates the git subtree sync process

param(
    [switch]$DryRun = $false
)

Write-Host "🔄 Synchronizing molass-library subtree..." -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "molass-library")) {
    Write-Host "❌ Error: molass-library folder not found." -ForegroundColor Red
    Write-Host "   Please run this script from the molass-review repository root." -ForegroundColor Red
    exit 1
}

# Check if molass-upstream remote exists
$remotes = git remote
if ($remotes -notcontains "molass-upstream") {
    Write-Host "📌 Adding molass-upstream remote..." -ForegroundColor Yellow
    if (-not $DryRun) {
        git remote add molass-upstream https://github.com/biosaxs-dev/molass-library.git
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Remote added successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to add remote" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "   [DRY RUN] Would add: git remote add molass-upstream https://github.com/biosaxs-dev/molass-library.git" -ForegroundColor Gray
    }
}

# Fetch latest changes
Write-Host ""
Write-Host "📥 Fetching latest changes from molass-upstream..." -ForegroundColor Yellow
if (-not $DryRun) {
    git fetch molass-upstream
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Fetch completed" -ForegroundColor Green
    } else {
        Write-Host "❌ Fetch failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   [DRY RUN] Would run: git fetch molass-upstream" -ForegroundColor Gray
}

# Check if there are updates available
Write-Host ""
Write-Host "🔍 Checking for updates..." -ForegroundColor Yellow

$currentCommit = git rev-parse HEAD:molass-library 2>$null
$upstreamCommit = git rev-parse molass-upstream/joss-paper^{tree} 2>$null

if ($currentCommit -eq $upstreamCommit) {
    Write-Host "✅ molass-library is already up-to-date!" -ForegroundColor Green
    Write-Host "   No synchronization needed." -ForegroundColor Gray
    exit 0
}

# Pull updates with squash
Write-Host ""
Write-Host "📦 Pulling updates from joss-paper branch..." -ForegroundColor Yellow
if (-not $DryRun) {
    git subtree pull --prefix=molass-library molass-upstream joss-paper --squash
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Synchronization completed successfully!" -ForegroundColor Green
        Write-Host "   molass-library has been updated with latest changes from joss-paper branch." -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "⚠️  Synchronization encountered conflicts or issues." -ForegroundColor Yellow
        Write-Host "   Please resolve conflicts manually and commit." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "   [DRY RUN] Would run: git subtree pull --prefix=molass-library molass-upstream joss-paper --squash" -ForegroundColor Gray
    Write-Host "   Updates are available but not applied (dry run mode)" -ForegroundColor Gray
}

Write-Host ""
