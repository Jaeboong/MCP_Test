# Playwright MCP CLI (Local Test)

Minimal MCP server + CLI for testing Playwright automation from terminal input.

## Setup
```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Run
```bash
python cli.py
```

## Example Commands
- terminal 1
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" `
>>   --remote-debugging-port=9222 `
>>   --user-data-dir="C:\ssafy\MCP\chrome_cdp_profile"
>> 
```
- terminal 2
```
python cli.py
```

## Natural Language (GPT-5-mini)
Set an API key in `.env`:
```text
OPENAI_API_KEY=your_key_here
```
Then type a natural language request instead of a command, e.g.:
```text
Search for bottled water on Coupang
```
