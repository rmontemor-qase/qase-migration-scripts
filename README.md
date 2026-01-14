# Qase CSV Reference Migration Script

A Python script to automatically fix broken CSV file references in Qase test cases.

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd qase-migration-scripts
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `config.json` file in the project root:

```json
{
  "api_token": "your-qase-api-token",
  "project_code": "YOUR_PROJECT_CODE"
}
```

You can use `config.json.example` as a template.

## Usage

```bash
# Dry run to preview changes
python fix_csv_references.py --dry-run

# Actually fix the issues
python fix_csv_references.py
```

## Command-line Options

```bash
# Use command-line arguments instead of config file
python fix_csv_references.py --token YOUR_TOKEN --project YOUR_PROJECT --dry-run

# Verbose mode for detailed output
python fix_csv_references.py --dry-run --verbose
```
