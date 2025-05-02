# URL Analysis MCP Server

A local MCP server that analyzes company websites and generates tailored outreach emails.

## Features

- Fetches and analyzes company websites
- Determines if a company is a manufacturer
- Extracts email addresses from websites
- Detects contact pages/forms
- Generates tailored outreach emails based on company type

## Installation

```bash
# Clone the repository
git clone https://github.com/keisuke70/urlAnalysisMCP.git
cd urlAnalysisMCP

# Install dependencies
pip install -r mcp_server/requirements.txt
```

### Quickstart
```bash
# 👉 Obtain an API key from Google AI Studio
export GEMINI_API_KEY="YOUR-KEY-HERE"
python -m mcp_server.server    # → http://localhost:8000/tools
```

**Note:** The server will start without an API key, but any LLM calls will raise a clear error message indicating that the `GEMINI_API_KEY` environment variable is not set.

## Usage

### Example RPC call
```bash
curl -X POST http://localhost:8000/execute \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,
          "method":"analyze_company",
          "params":{"url":"https://www.toyota-global.com"}}'
```

### Response Format

The server returns JSON in the following format:

```json
{
  "manufacturer": true|false,
  "email": "example@domain.com"|null,
  "contact": true|false,
  "contact_url": "https://example.com/contact"|null,
  "mail_body": "Generated email content..."
}
```

## Development

### Running Tests

```bash
# Run tests without hitting the LLM
pytest mcp_server/tests/
```

## Error Handling

- The server always returns a valid JSON response with all four keys
- On fatal errors, it sets `manufacturer=false`, `email=null`, `contact=false`, `mail_body=""`
- Rate limit errors (429) from the LLM are handled with exponential backoff retry
