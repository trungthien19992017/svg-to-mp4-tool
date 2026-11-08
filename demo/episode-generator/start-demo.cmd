@echo off
cd /d "%~dp0"
echo Production Kit Demo - independent of Studio
echo Open http://127.0.0.1:5198 after the server starts.
echo Press Ctrl+C to stop this demo only.
python -m http.server 5198 --bind 127.0.0.1 --directory "%~dp0generated"
pause
