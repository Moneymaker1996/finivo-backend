<#
PowerShell helper to create a PR for the current repo using the GitHub CLI.

Usage (PowerShell):
  .\scripts\create_pr.ps1

This script will:
  - create a branch named from the PR title
  - commit all local changes
  - push the branch to origin
  - open a draft PR using `gh pr create` with the body loaded from
    `.github/PULL_REQUEST_TEMPLATE/stable-mock-mode.md`

Requirements:
  - git configured with an "origin" remote
  - GitHub CLI `gh` installed and authenticated (gh auth login)
#>

param(
    [string]$BranchName = "stable-mock-mode-integration-test-harness-1.0",
    [string]$CommitMessage = "Stable Mock Mode Integration & Test Harness 1.0 — Finivo Backend MVP",
    [string]$PrTitle = "Stable Mock Mode Integration & Test Harness 1.0 — Finivo Backend MVP",
    [string]$PrBodyPath = ".github/PULL_REQUEST_TEMPLATE/stable-mock-mode.md",
    [switch]$Draft = $true
)

Write-Host "Creating branch: $BranchName"
git checkout -b $BranchName

Write-Host "Staging changes..."
git add -A

Write-Host "Committing..."
git commit -m $CommitMessage

Write-Host "Pushing branch to origin..."
git push -u origin $BranchName

Write-Host "Creating PR (requires gh CLI)..."
$draftArg = if ($Draft) { "--draft" } else { "" }
gh pr create --title "$PrTitle" --body-file $PrBodyPath $draftArg --base main --head $BranchName

Write-Host "Done. If the gh CLI opened an editor or reported an error, follow its messages." 
