# Qase Migration Scripts

Python scripts for migrating and fixing Qase test cases.

## Available Scripts

- **fix_csv_references.py**: Fixes broken CSV file references in test cases
- **field_migration.py**: Generic script to migrate content from any system field to any custom field
- **link_jira_issues.py**: Extracts JIRA issue IDs from test case fields and links them to Qase test cases

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
  "project_code": "YOUR_PROJECT_CODE",
  "source_field": "preconditions",
  "destination_field": "Preconditions",
  "destination_field_id": null
}
```

You can use `config.json.example` as a template.

### Configuration Options

- `api_token`: Your Qase API token (required)
- `project_code`: Your Qase project code (required)
- `source_field`: Name of the source system field (e.g., 'preconditions', 'description'). Can also be provided via `--source-field` command-line argument.
- `destination_field`: Name of the destination custom field (e.g., 'Preconditions'). Can also be provided via `--destination-field` command-line argument.
- `destination_field_id`: Optional custom field ID for the destination field. If not provided, the script will search for the field by name. Set to `null` to use name-based search. Can also be provided via `--destination-field-id` command-line argument.

## Usage

### Fix CSV References

```bash
# Dry run to preview changes
python fix_csv_references.py --dry-run

# Actually fix the issues
python fix_csv_references.py
```

### Migrate Field Content

You can configure the source and destination fields either in `config.json` or via command-line arguments. Command-line arguments override config file values.

**Using config.json (recommended for repeated use):**

```bash
# With fields configured in config.json, just run:
python field_migration.py --dry-run

# Actually perform the migration
python field_migration.py
```

**Using command-line arguments:**

```bash
# Example: Migrate Pre-conditions to Preconditions custom field
# Dry run to preview changes
python field_migration.py --source-field preconditions --destination-field Preconditions --dry-run

# Actually perform the migration
python field_migration.py --source-field preconditions --destination-field Preconditions

# Example: Migrate Description to a custom field
python field_migration.py --source-field description --destination-field "Test Description" --dry-run
```

## Command-line Options

Both scripts support the following options:

```bash
# Use command-line arguments instead of config file
python field_migration.py --token YOUR_TOKEN --project YOUR_PROJECT --source-field preconditions --destination-field Preconditions --dry-run

# Specify custom field ID via command line (for field_migration.py)
python field_migration.py --source-field preconditions --destination-field Preconditions --destination-field-id 123 --dry-run

# Verbose mode for detailed output
python field_migration.py --source-field preconditions --destination-field Preconditions --dry-run --verbose
```

### field_migration.py Specific Options

- `--source-field`: Name of the source system field (e.g., 'preconditions', 'description', 'postconditions'). Required if not set in config.json.
- `--destination-field`: Name of the destination custom field (e.g., 'Preconditions', 'Test Description'). Required if not set in config.json.
- `--destination-field-id`: Optional custom field ID for the destination field (overrides config file and name search). If not provided, the script will search for the field by name.

### Supported Source Fields

The script supports the following system fields (case-insensitive):
- `preconditions` or `pre-conditions`
- `description`
- `postconditions` or `post-conditions`

### Link JIRA Issues

The `link_jira_issues.py` script extracts JIRA issue IDs from test case fields and attaches them as external issues in Qase.

**Usage:**

```bash
# Dry run to preview what would be linked
python link_jira_issues.py --dry-run

# Actually link JIRA issues
python link_jira_issues.py

# Specify JIRA type and batch size
python link_jira_issues.py --type jira-cloud --batch-size 50

# Verbose mode to see details for each case
python link_jira_issues.py --verbose
```

**Configuration:**

The script can use configuration from `config.json`:

```json
{
  "api_token": "your-qase-api-token",
  "project_code": "YOUR_PROJECT_CODE",
  "tests": {
    "external_issues": {
      "enable": true,
      "type": "jira-cloud",
      "batch_size": 50
    }
  }
}
```

**How it works:**

1. Fetches all test cases from the specified Qase project
2. Extracts JIRA issue IDs (pattern: `PROJECT-123`) from the **refs** field only
3. Attaches JIRA issues to test cases in batches using the Qase External Issues API

**Command-line Options:**

- `--type`: JIRA instance type (`jira-cloud` or `jira-server`, default: `jira-cloud`)
- `--batch-size`: Number of cases per batch (default: 50)
- `--dry-run`: Preview changes without making API calls
- `--verbose`: Show detailed information about each test case

For more details, see `JIRA_EXTERNAL_ISSUES_BREAKDOWN.md`.
