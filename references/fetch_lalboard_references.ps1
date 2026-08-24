[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$referenceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-Commit([string]$Path) {
    $safe = ($Path -replace '\\', '/')
    $commit = & git -c "safe.directory=$safe" -C $Path rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw "Cannot read Git checkout: $Path" }
    return $commit.Trim()
}

function Ensure-Checkout(
    [string]$Name,
    [string]$Repository,
    [string]$Ref,
    [string]$Commit
) {
    $target = Join-Path $referenceRoot $Name
    # A freshly cloned parent repository creates an empty directory for an
    # uninitialised gitlink. Test for nested Git metadata, not only the folder.
    $gitMetadata = Join-Path $target '.git'
    if (-not (Test-Path -LiteralPath $gitMetadata)) {
        & git clone --branch $Ref --depth 1 $Repository $target
        if ($LASTEXITCODE -ne 0) { throw "Clone failed: $Repository" }
    }

    $actual = Get-Commit $target
    if ($actual -ne $Commit) {
        throw "Commit mismatch at $target`nexpected: $Commit`nactual:   $actual"
    }
    Write-Host "OK $Name @ $actual"
}

Ensure-Checkout 'lalboard-v2.5.1' `
    'https://github.com/JesusFreke/lalboard.git' `
    'v2.5.1' `
    '1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a'

Ensure-Checkout 'lalboard-v2.5.1/stls' `
    'https://github.com/JesusFreke/lalboard_stls.git' `
    'v2.5.1' `
    '282d61ae3a4d06d4dba2590779023b716da62b45'

Ensure-Checkout 'lalboard' `
    'https://github.com/JesusFreke/lalboard.git' `
    'main' `
    'eddf521062c8e6eb5e67b05d071c60f093652c0a'

Ensure-Checkout 'lalboard-stls-main' `
    'https://github.com/JesusFreke/lalboard_stls.git' `
    'main' `
    'cfd0534cea86e86224ba42f4a193078c626f1d7f'

$sourcePath = Join-Path $referenceRoot 'lalboard-v2.5.1'
$safeSourcePath = ($sourcePath -replace '\\', '/')
$gitlinkLine = & git -c "safe.directory=$safeSourcePath" -C $sourcePath ls-tree HEAD stls
if ($LASTEXITCODE -ne 0 -or
    $gitlinkLine -notmatch '282d61ae3a4d06d4dba2590779023b716da62b45') {
    throw "The v2.5.1 source stls gitlink is not the locked output commit."
}

$mainSourcePath = Join-Path $referenceRoot 'lalboard'
$safeMainSourcePath = ($mainSourcePath -replace '\\', '/')
$mainGitlinkLine = & git -c "safe.directory=$safeMainSourcePath" -C $mainSourcePath ls-tree HEAD stls
if ($LASTEXITCODE -ne 0 -or
    $mainGitlinkLine -notmatch 'cfd0534cea86e86224ba42f4a193078c626f1d7f') {
    throw "The retained main source stls gitlink is not the locked main output commit."
}

$lockPath = Join-Path $referenceRoot 'reference-lock.json'
$lock = Get-Content -Raw -LiteralPath $lockPath | ConvertFrom-Json
$hashRoots = @{
    'source_v2.5.1' = Join-Path $referenceRoot 'lalboard-v2.5.1'
    'output_files_identical_at_282d61a_and_cfd0534' = Join-Path $referenceRoot 'lalboard-v2.5.1/stls'
}

foreach ($groupName in $hashRoots.Keys) {
    $group = $lock.sha256.$groupName
    foreach ($property in $group.PSObject.Properties) {
        $path = Join-Path $hashRoots[$groupName] $property.Name
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        if ($actual -ne $property.Value) {
            throw "SHA-256 mismatch: $path`nexpected: $($property.Value)`nactual:   $actual"
        }
    }
}

# The analysis uses only these five output files. Verify the separately retained
# later main output snapshot is byte-identical for those files, without making
# the broader claim that the two commits are wholly identical.
$mainOutputRoot = Join-Path $referenceRoot 'lalboard-stls-main'
$outputHashes = $lock.sha256.output_files_identical_at_282d61a_and_cfd0534
foreach ($property in $outputHashes.PSObject.Properties) {
    $path = Join-Path $mainOutputRoot $property.Name
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    if ($actual -ne $property.Value) {
        throw "Later-output SHA-256 mismatch: $path`nexpected: $($property.Value)`nactual:   $actual"
    }
}

Write-Host 'All locked commits and analysis-file hashes verified.'
