$ErrorActionPreference = "Stop"

$requiredNames = @(
    "FEM2D_AGENT_LLM_PROVIDER",
    "FEM2D_AGENT_LLM_MODEL",
    "FEM2D_AGENT_LLM_API_KEY",
    "FEM2D_AGENT_LLM_BASE_URL"
)

foreach ($name in $requiredNames) {
    $currentValue = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not $currentValue) {
        $userValue = [Environment]::GetEnvironmentVariable($name, "User")
        if ($userValue) {
            [Environment]::SetEnvironmentVariable($name, $userValue, "Process")
        }
    }
}

$missingNames = @(
    $requiredNames | Where-Object {
        -not [Environment]::GetEnvironmentVariable($_, "Process")
    }
)
if ($missingNames.Count -gt 0) {
    throw "Missing real Agent API configuration: $($missingNames -join ', ')"
}

$env:FEM2D_AGENT_RUN_REAL_API = "1"
& "$PSScriptRoot\codex_pytest.ps1" tests\e2e -q
exit $LASTEXITCODE
