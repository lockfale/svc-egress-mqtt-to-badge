# Enable debug output
$DebugPreference = "Continue"

# 1. Get CodeArtifact token
Write-Debug "Getting CodeArtifact token..."
$env:CODEARTIFACT_AUTH_TOKEN = aws --profile ckc-bot-api codeartifact get-authorization-token `
    --domain lockfale `
    --domain-owner 059039070213 `
    --query authorizationToken `
    --output text
Write-Debug "Token obtained successfully"
$env:CODEARTIFACT_TOKEN=$env:CODEARTIFACT_AUTH_TOKEN
Write-Debug "Token: $env:CODEARTIFACT_AUTH_TOKEN"


# 2. Get CodeArtifact repository URL
Write-Debug "Getting repository URL..."
$env:CODEARTIFACT_REPO_URL = aws --profile ckc-bot-api codeartifact get-repository-endpoint `
    --domain lockfale `
    --domain-owner 059039070213 `
    --repository lockfale `
    --format pypi `
    --query repositoryEndpoint `
    --output text
Write-Debug "Repository URL: $env:CODEARTIFACT_REPO_URL"

# 3. Configure Poetry to use CodeArtifact
Write-Debug "Configuring Poetry repository..."
poetry config repositories.lockfale $env:CODEARTIFACT_REPO_URL
Write-Debug "Configuring Poetry credentials..."
$env:POETRY_HTTP_BASIC_LOCKFALE_USERNAME=echo aws
$env:POETRY_HTTP_BASIC_LOCKFALE_PASSWORD=$env:CODEARTIFACT_AUTH_TOKEN

# for whatever reason... this would not work...
# poetry config http-basic.lockfale "aws" "$env:CODEARTIFACT_AUTH_TOKEN"
