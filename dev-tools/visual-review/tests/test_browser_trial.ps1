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

$powershellPath = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
function Invoke-HiddenPowerShellScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InputText,
        [int]$TimeoutMilliseconds = 10000
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $powershellPath
    $startInfo.Arguments = '-NoProfile -NonInteractive -File -'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $timedOut = $false
    $streamTimedOut = $false
    try {
        if (-not $process.Start()) {
            throw "could not start hidden PowerShell child at $powershellPath"
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.StandardInput.WriteLine($InputText)
        $process.StandardInput.Close()

        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            $timedOut = $true
            try {
                $process.Kill()
            }
            catch {
                if (-not $process.HasExited) {
                    throw "timed-out hidden PowerShell child could not be stopped: $($_.Exception.Message)"
                }
            }
            [void]$process.WaitForExit(1000)
        }

        $stdoutCompleted = $stdoutTask.Wait(1000)
        $stderrCompleted = $stderrTask.Wait(1000)
        $streamTimedOut = -not ($stdoutCompleted -and $stderrCompleted)
        $stdout = if ($stdoutCompleted) { $stdoutTask.GetAwaiter().GetResult() } else { '<stdout read timed out>' }
        $stderr = if ($stderrCompleted) { $stderrTask.GetAwaiter().GetResult() } else { '<stderr read timed out>' }
        $exitCode = if ($timedOut -or $streamTimedOut) { $null } else { $process.ExitCode }
        return [pscustomobject]@{
            stdout = $stdout
            stderr = $stderr
            exit_code = $exitCode
            timed_out = $timedOut -or $streamTimedOut
        }
    }
    finally {
        $process.Dispose()
    }
}

$positiveInput = @'
$ErrorActionPreference = 'Stop'
$source = Get-Content -LiteralPath '__TRIAL_PATH__' -Raw
$trial = [scriptblock]::Create($source)
. $trial -Library
$plan = Invoke-BrowserTrial -BrowserPath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ProfilePath 'C:\Temp\pr127-gallery-stdin-control' -DebugPort 9234 -Mode Plan -ProfileExists { $false } -ProcessStarter { throw 'stdin control must not launch a browser' }
if ($plan.mode -ne 'plan' -or $plan.launch -ne $false) { throw 'stdin control did not produce a non-launch plan' }
Write-Output 'VALID_STDIN_SENTINEL'
'@.Replace('__TRIAL_PATH__', $trialPath)
$positiveResult = Invoke-HiddenPowerShellScript -InputText $positiveInput
if ($positiveResult.timed_out -or $positiveResult.exit_code -ne 0 -or
    -not ($positiveResult.stdout -match '(?m)^VALID_STDIN_SENTINEL\s*$') -or
    $positiveResult.stderr) {
    throw 'valid stdin control did not execute successfully'
}

$sentinelInput = @'
$ErrorActionPreference = 'Stop'
$source = Get-Content -LiteralPath '__TRIAL_PATH__' -Raw
$trial = [scriptblock]::Create($source)
& $trial -BrowserPath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ProfilePath '' -DebugPort 9234
Write-Output 'FAIL_CLOSED_SENTINEL'
'@.Replace('__TRIAL_PATH__', $trialPath)
$sentinelResult = Invoke-HiddenPowerShellScript -InputText $sentinelInput
if ($sentinelResult.timed_out -or $sentinelResult.exit_code -eq 0) {
    throw 'invalid stdin invocation returned a zero exit status'
}
if ($sentinelResult.stdout -match 'FAIL_CLOSED_SENTINEL' -or
    $sentinelResult.stderr -match 'FAIL_CLOSED_SENTINEL') {
    throw 'invalid stdin invocation allowed a following statement to run'
}

$bindingInput = @'
$ErrorActionPreference = 'Stop'
$source = Get-Content -LiteralPath '__TRIAL_PATH__' -Raw
$trial = [scriptblock]::Create($source)
& $trial -BrowserPath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ProfilePath 'C:\Temp\pr127-gallery-binding' -DebugPort nope
Write-Output 'BINDING_SENTINEL'
'@.Replace('__TRIAL_PATH__', $trialPath)
$bindingResult = Invoke-HiddenPowerShellScript -InputText $bindingInput
if ($bindingResult.timed_out -or $bindingResult.exit_code -eq 0) {
    throw 'nonnumeric debug port returned a zero exit status'
}
if ($bindingResult.stdout -match 'BINDING_SENTINEL' -or
    $bindingResult.stderr -match 'BINDING_SENTINEL') {
    throw 'nonnumeric debug port allowed a following statement to run'
}

Write-Output 'browser trial fail-closed stdin check passed'
