$ErrorActionPreference = 'Stop'

$trialPath = Join-Path (Get-Location) 'dev-tools\visual-review\browser_trial.ps1'
if (-not (Test-Path -LiteralPath $trialPath -PathType Leaf)) {
    throw "browser_trial.ps1 was not found at $trialPath"
}

$trialSource = Get-Content -LiteralPath $trialPath -Raw
$testBody = @'
$state = [pscustomobject]@{
    launch_calls = 0
    executable = $null
    argument_line = $null
}
$fakeStarter = {
    param(
        [string]$Executable,
        [string]$ArgumentLine
    )
    $state.launch_calls++
    $state.executable = $Executable
    $state.argument_line = $ArgumentLine
    [pscustomobject]@{ Id = 4242 }
}
$profileExists = {
    param([string]$Path)
    $Path -eq 'C:\Temp\pr127-gallery-existing'
}
$executableExists = {
    param([string]$Path)
    $true
}
$browser = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$freshProfile = 'C:\Temp\pr127-gallery-plan-001'

function Assert-RejectedWithoutLaunch {
    param(
        [string]$Label,
        [string]$Profile,
        [int]$Port
    )

    $before = $state.launch_calls
    $rejected = $false
    try {
        Invoke-BrowserTrial -BrowserPath $browser -ProfilePath $Profile -DebugPort $Port -Mode Launch `
            -ProcessStarter $fakeStarter -ProfileExists $profileExists -ExecutableExists $executableExists | Out-Null
    }
    catch {
        $rejected = $true
    }
    if (-not $rejected) {
        throw "$Label was accepted"
    }
    if ($state.launch_calls -ne $before) {
        throw "$Label reached the process starter"
    }
}

Assert-RejectedWithoutLaunch -Label 'empty profile' -Profile '' -Port 9234
Assert-RejectedWithoutLaunch -Label 'port zero' -Profile $freshProfile -Port 0
Assert-RejectedWithoutLaunch -Label 'UNC profile' -Profile '\\wsl.localhost\Ubuntu-22.04\tmp\pr127-gallery-unc' -Port 9234
Assert-RejectedWithoutLaunch -Label 'existing profile' -Profile 'C:\Temp\pr127-gallery-existing' -Port 9234

$planProfile = 'C:\Temp\pr127 gallery plan-001'
$plan = Invoke-BrowserTrial -BrowserPath $browser -ProfilePath $planProfile -DebugPort 9234 `
    -ProcessStarter $fakeStarter -ProfileExists $profileExists -ExecutableExists $executableExists
if ($plan.mode -ne 'plan' -or $plan.launch -ne $false) {
    throw 'the default mode did not return a non-launch plan'
}
if ($state.launch_calls -ne 0) {
    throw 'the default plan invoked the process starter'
}
if ($plan.argument_line -notmatch '"--user-data-dir=C:\\Temp\\pr127 gallery plan-001"') {
    throw 'the default plan did not preserve a spaced profile as one quoted argument'
}

$receipt = Invoke-BrowserTrial -BrowserPath $browser -ProfilePath $planProfile -DebugPort 9234 -Mode Launch `
    -ProcessStarter $fakeStarter -ProfileExists $profileExists -ExecutableExists $executableExists
if ($state.launch_calls -ne 1 -or $receipt.pid -ne 4242) {
    throw 'the mocked launch did not return its owned process receipt'
}
if ($state.argument_line -ne $receipt.argument_line -or
    $state.argument_line -notmatch '"--user-data-dir=C:\\Temp\\pr127 gallery plan-001"') {
    throw 'the mocked launch did not receive the exact quoted plan argument line'
}

Write-Output 'browser trial validation and mocked launch checks passed'
'@

$combined = [scriptblock]::Create($trialSource + "`r`n" + $testBody)
& $combined -Library

$sentinelInput = @'
$ErrorActionPreference = 'Stop'
$source = Get-Content -LiteralPath '__TRIAL_PATH__' -Raw
$trial = [scriptblock]::Create($source)
& $trial -BrowserPath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ProfilePath '' -DebugPort 9234
Write-Output 'FAIL_CLOSED_SENTINEL'
'@.Replace('__TRIAL_PATH__', $trialPath)
$sentinelOutput = $sentinelInput | & powershell.exe -NoProfile -NonInteractive -File - 2>&1
$sentinelExit = $LASTEXITCODE
if ($sentinelExit -eq 0) {
    throw 'invalid stdin invocation returned a zero exit status'
}
if ($sentinelOutput -match 'FAIL_CLOSED_SENTINEL') {
    throw 'invalid stdin invocation allowed a following statement to run'
}

$bindingInput = @'
$ErrorActionPreference = 'Stop'
$source = Get-Content -LiteralPath '__TRIAL_PATH__' -Raw
$trial = [scriptblock]::Create($source)
& $trial -BrowserPath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ProfilePath 'C:\Temp\pr127-gallery-binding' -DebugPort nope
Write-Output 'BINDING_SENTINEL'
'@.Replace('__TRIAL_PATH__', $trialPath)
$bindingOutput = $bindingInput | & powershell.exe -NoProfile -NonInteractive -File - 2>&1
$bindingExit = $LASTEXITCODE
if ($bindingExit -eq 0) {
    throw 'nonnumeric debug port returned a zero exit status'
}
if ($bindingOutput -match 'BINDING_SENTINEL') {
    throw 'nonnumeric debug port allowed a following statement to run'
}

Write-Output 'browser trial fail-closed stdin check passed'
