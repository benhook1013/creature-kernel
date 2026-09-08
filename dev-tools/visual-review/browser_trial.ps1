[CmdletBinding()]
param(
    [string]$BrowserPath,
    [string]$ProfilePath,
    [string]$DebugPort = '0',
    [string]$Mode = 'Plan',
    [switch]$Library
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Assert-NativeWindowsLiteralPath {
    param(
        [string]$Value,
        [string]$Name,
        [switch]$Profile
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Name is required and must be a non-empty native Windows path"
    }
    if ($Value -match '[*?\[\]"]') {
        throw "$Name must be an explicit literal path without wildcards or quotes"
    }
    if ($Value -match '^\\\\') {
        throw "$Name must not be a UNC or WSL path"
    }
    if ($Value -notmatch '^[A-Za-z]:[\\/]') {
        throw "$Name must be an absolute native Windows path such as C:\Temp\name"
    }
    if ($Value -match '(^|[\\/])\.\.?([\\/]|$)') {
        throw "$Name must not contain relative path components"
    }
    if ($Profile -and $Value -match '^[A-Za-z]:[\\/]$') {
        throw "$Name must identify a new profile directory, not a drive root"
    }
}

function ConvertTo-WindowsArgument {
    param([string]$Value)

    if ($Value -notmatch '\s') {
        return $Value
    }
    $escaped = $Value -replace '(\\*)$', '$1$1'
    return '"' + $escaped + '"'
}

function ConvertTo-WindowsArgumentLine {
    param([string[]]$Arguments)

    return (($Arguments | ForEach-Object {
        ConvertTo-WindowsArgument -Value $_
    }) -join ' ')
}

function ConvertTo-WindowsCommandLine {
    param(
        [string]$Executable,
        [string[]]$Arguments
    )

    $argumentLine = ConvertTo-WindowsArgumentLine -Arguments $Arguments
    return ((ConvertTo-WindowsArgument -Value $Executable) + ' ' + $argumentLine)
}

function Invoke-BrowserTrial {
    [CmdletBinding()]
    param(
        [string]$BrowserPath,
        [string]$ProfilePath,
        [int]$DebugPort = 0,
        [ValidateSet('Plan', 'Launch')]
        [string]$Mode = 'Plan',
        [scriptblock]$ProcessStarter,
        [scriptblock]$ProfileExists,
        [scriptblock]$ExecutableExists
    )

    Assert-NativeWindowsLiteralPath -Value $BrowserPath -Name 'BrowserPath'
    if ($BrowserPath -notmatch '(?i)\.exe$') {
        throw 'BrowserPath must name an explicit .exe file'
    }
    Assert-NativeWindowsLiteralPath -Value $ProfilePath -Name 'ProfilePath' -Profile
    if ($DebugPort -lt 1 -or $DebugPort -gt 65535) {
        throw 'DebugPort must be an integer from 1 through 65535'
    }

    if ($null -eq $ProfileExists) {
        $ProfileExists = {
            param([string]$Path)
            Test-Path -LiteralPath $Path
        }
    }
    if (& $ProfileExists $ProfilePath) {
        throw "ProfilePath already exists; provide a fresh task-owned directory: $ProfilePath"
    }

    $arguments = @(
        '--headless=new'
        '--noerrdialogs'
        '--no-first-run'
        '--no-default-browser-check'
        '--remote-debugging-address=127.0.0.1'
        "--remote-debugging-port=$DebugPort"
        "--user-data-dir=$ProfilePath"
        'about:blank'
    )
    $argumentLine = ConvertTo-WindowsArgumentLine -Arguments $arguments
    $command = ConvertTo-WindowsCommandLine -Executable $BrowserPath -Arguments $arguments
    $plan = [ordered]@{
        mode = 'plan'
        browser = $BrowserPath
        profile = $ProfilePath
        cdp_port = $DebugPort
        arguments = $arguments
        argument_line = $argumentLine
        command = $command
        launch = $false
    }

    if ($Mode -eq 'Plan') {
        return [pscustomobject]$plan
    }

    if ($null -eq $ExecutableExists) {
        $ExecutableExists = {
            param([string]$Path)
            Test-Path -LiteralPath $Path -PathType Leaf
        }
    }
    if (-not (& $ExecutableExists $BrowserPath)) {
        throw "BrowserPath does not exist as a file: $BrowserPath"
    }
    if ($null -eq $ProcessStarter) {
        $ProcessStarter = {
            param(
                [string]$Executable,
                [string]$ArgumentLine
            )
            Start-Process -FilePath $Executable -ArgumentList $ArgumentLine -PassThru
        }
    }

    $handoff = @(& $ProcessStarter $BrowserPath $argumentLine)
    if ($handoff.Count -ne 1 -or $null -eq $handoff[0]) {
        throw 'Browser launch did not return exactly one owned process handle'
    }
    $idProperty = $handoff[0].PSObject.Properties['Id']
    $processId = 0
    if ($null -eq $idProperty -or -not [int]::TryParse([string]$idProperty.Value, [ref]$processId) -or $processId -lt 1) {
        throw 'Browser launch returned no valid process ID; refusing an unowned handoff'
    }

    $receipt = [ordered]@{
        mode = 'launch'
        browser = $BrowserPath
        profile = $ProfilePath
        cdp_port = $DebugPort
        arguments = $arguments
        argument_line = $argumentLine
        command = $command
        pid = $processId
        ownership = [ordered]@{
            owner = 'visual-review browser_trial.ps1 task'
            pid = $processId
            cleanup = 'Before termination, verify the current PID, executable, and profile against this receipt; do not terminate by PID alone.'
        }
    }
    return [pscustomobject]$receipt
}

if (-not $Library -and $MyInvocation.InvocationName -ne '.') {
    & {
        try {
            Invoke-BrowserTrial -BrowserPath $BrowserPath -ProfilePath $ProfilePath -DebugPort $DebugPort -Mode $Mode |
                ConvertTo-Json -Depth 6
        }
        catch {
            Write-Error $_ -ErrorAction Continue
            $Host.SetShouldExit(1)
        }
    }
}
