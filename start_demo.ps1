# One-click start for the demo (Windows).
# Run with:  powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

if (-not (Test-Path ".env")) {
    Write-Host "Missing .env file. Copy .env.example to .env and add your Gemini API key."
    exit 1
}

Write-Host "Starting the PhantomNet API..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$here'; python api.py"
Start-Sleep -Seconds 4

Write-Host "Starting the dashboard..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$here'; python -m streamlit run dashboard.py"
Start-Sleep -Seconds 6

Start-Process "http://localhost:8501/?presenter=1"
Write-Host "Done. The API is on http://127.0.0.1:5000 and the dashboard on http://localhost:8501"