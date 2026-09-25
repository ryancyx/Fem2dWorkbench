$ErrorActionPreference = "Stop"

$provider = (Read-Host "Provider (openai/deepseek)").Trim().ToLowerInvariant()
if ($provider -notin @("openai", "deepseek")) {
    throw "Provider must be openai or deepseek."
}

if ($provider -eq "openai") {
    $defaultBaseUrl = "https://api.openai.com/v1"
    $modelHint = "OpenAI model with Structured Outputs support"
} else {
    $defaultBaseUrl = "https://api.deepseek.com"
    $modelHint = "DeepSeek model with JSON Output support"
}

$model = (Read-Host "Model ($modelHint)").Trim()
if (-not $model) {
    throw "Model must not be empty."
}

$baseUrl = (Read-Host "Base URL [$defaultBaseUrl]").Trim()
if (-not $baseUrl) {
    $baseUrl = $defaultBaseUrl
}

$secureKey = Read-Host "API key (hidden input)" -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if (-not $plainKey) {
        throw "API key must not be empty."
    }
    [Environment]::SetEnvironmentVariable("FEM2D_AGENT_LLM_PROVIDER", $provider, "User")
    [Environment]::SetEnvironmentVariable("FEM2D_AGENT_LLM_MODEL", $model, "User")
    [Environment]::SetEnvironmentVariable("FEM2D_AGENT_LLM_API_KEY", $plainKey, "User")
    [Environment]::SetEnvironmentVariable("FEM2D_AGENT_LLM_BASE_URL", $baseUrl, "User")
} finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $plainKey = $null
    $secureKey = $null
}

Write-Host "Agent LLM provider configuration saved to Windows user environment."
Write-Host "Provider: $provider"
Write-Host "Model: $model"
Write-Host "Base URL: $baseUrl"
Write-Host "API key: configured (hidden)"
