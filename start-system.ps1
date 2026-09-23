
# Start the CargoHUB WMS API. Run from the repo root or from anywhere -
# we change into api/ so the providers / models / processors namespace
# packages resolve and the absolute ROOT_PATH in data_provider.py finds data/.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptDir "api")

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python main.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 main.py
} else {
    throw "Python was not found in PATH."
}