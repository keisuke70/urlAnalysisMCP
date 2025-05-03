# Company Website Analyzer Script

A Python script that analyzes company websites based on a provided list, determines if they are manufacturers, extracts contact information, generates tailored outreach emails using Google Gemini, and outputs the results to a CSV file.

## Features

- Reads a list of company names and URLs from a CSV file.
- Fetches and parses website content.
- Uses Google Gemini to classify companies as manufacturers.
- Uses Google Gemini to summarize company information (for email context).
- Uses Google Gemini to draft tailored outreach email bodies (only for manufacturers).
- Extracts the first found email address from the website.
- Detects the URL of a contact page or form.
- Outputs results (company name, email body, contact URL, email address, errors) to a CSV file.
- Handles rate limiting from the Gemini API with retries.
- Gracefully handles errors during fetching or analysis for individual companies.

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <your-repo-url>
    cd urlAnalysisMCP
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r mcp_server/requirements.txt
    # Or use the Makefile/make.ps1 script
    # make install
    # .\make.ps1 install
    ```

3.  **Set up API Key:**

    - Obtain a Google Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    - Create a file named `.env` in the root directory of the project.
    - Add your API key to the `.env` file:
      ```dotenv
      GEMINI_API_KEY="YOUR-API-KEY-HERE"
      ```
    - **Important:** Ensure `.env` is listed in your `.gitignore` file (it is by default in the provided `.gitignore`).

4.  **Prepare Input File:**
    - Create a CSV file (e.g., `companies.csv`) with the following columns:
      - `CompanyName`: The name of the company.
      - `URL`: The full homepage URL of the company (e.g., `https://www.example.com`).
    - Example `companies.csv`:
      ```csv
      CompanyName,URL
      Nissen Co,"https://nissen-co.co.jp/rivet/"
      Example Corp,"https://example.com"
      Another Company,"https://another-site.org"
      ```

## Usage

Run the script from the command line, providing the input CSV path and optionally an output CSV path.

```bash
python company_analyzer.py --input <path_to_your_input.csv> --output <desired_output_path.csv>

# Example:
python company_analyzer.py --input companies.csv --output analysis_results.csv
```

Alternatively, use the provided Makefiles:

**Using Makefile (Linux/macOS):**

```bash
make analyze INPUT=companies.csv OUTPUT=analysis_results.csv
```

**Using make.ps1 (Windows PowerShell):**

```powershell
.\make.ps1 analyze -Input companies.csv -Output analysis_results.csv
```

The script will process each company in the input file and generate the output CSV (defaulting to output.csv if --output is not specified).

### Output CSV Format

The output CSV file will contain the following columns:

- `company_name`: The name of the company from the input file.
- `mail_body`: The generated email body text (only for manufacturers, otherwise empty). Includes the standard closing block.
- `contact_url`: The URL found for a contact page or form (if detected, otherwise empty).
- `email`: The first email address found on the page (if detected, otherwise empty).
- `error`: Contains an error message if processing failed for that company (e.g., "Failed to fetch...", "Company identified as non-manufacturer", "An unexpected error occurred..."). Empty if processing was successful.

## Development

### Running Tests

Basic tests (including checking Japanese prompt effectiveness if the Gemini API key is set) can be run:

```bash
# Using pytest directly (if installed)
# pytest

# Or run the specific test script
python test_japanese_prompts.py

# Or using the Makefiles
# make test
# .\make.ps1 test
```

### Linting

Check code style and types:

```bash
# make lint
# .\make.ps1 lint
```

### Cleaning

Remove generated files (_.pyc, **pycache**, _.csv, etc.):

```bash
# make clean
# .\make.ps1 clean
```

## Error Handling

- The script requires the GEMINI_API_KEY environment variable to be set for LLM functions. It will exit if not found at startup.
- Network errors during website fetching are caught, logged, and an error message is added to the output row.
- If a company is classified as not a manufacturer, processing stops for that company, and a specific note is added to the error column.
- Errors during LLM calls (other than rate limits) are caught and logged.
- Rate limit errors (429) from the Gemini API are handled with exponential backoff retries up to a limit. If retries fail, an error is logged.
