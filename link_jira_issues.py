#!/usr/bin/env python3
"""
Qase Migration Script: Link JIRA Issues to Test Cases

This script:
1. Fetches all test cases from a Qase project
2. Extracts JIRA issue IDs from the refs field in test cases
3. Attaches JIRA issues to test cases using the Qase External Issues API
"""

import json
import os
import argparse
import re
from typing import Dict, List, Any, Optional, Set


class JIRAIssueExtractor:
    """Handles extraction of JIRA issue IDs from test case fields."""

    @staticmethod
    def _extract_jira_issue_ids(text: Optional[str]) -> List[str]:
        """
        Extract JIRA issue IDs from text.
        JIRA issue IDs typically follow the pattern: PROJECT-123, ABC-456, etc.

        Args:
            text: Text to search for JIRA issue IDs

        Returns:
            List of unique JIRA issue IDs found
        """
        if not text:
            return []

        jira_ids = []
        # Pattern to match JIRA issue IDs: one or more uppercase letters,
        # followed by dash and numbers
        jira_pattern = re.compile(r'\b([A-Z][A-Z0-9]+-\d+)\b')

        # Extract JIRA IDs from the text (handles URLs and plain issue IDs)
        matches = jira_pattern.findall(text)
        jira_ids.extend(matches)

        # Return unique IDs, preserving order
        seen = set()
        unique_ids = []
        for jira_id in jira_ids:
            if jira_id not in seen:
                seen.add(jira_id)
                unique_ids.append(jira_id)

        return unique_ids

    @staticmethod
    def extract_from_test_case(test_case: Dict[str, Any], refs_field_id: Optional[int] = None, debug: bool = False) -> List[str]:
        """
        Extract JIRA issue IDs from the refs field in a test case.

        Args:
            test_case: Test case dictionary from the API
            refs_field_id: Custom field ID for the refs field (if stored as custom field)
            debug: If True, print debug information

        Returns:
            List of unique JIRA issue IDs found in the refs field
        """
        refs = None
        refs_source = None
        
        # First try to get from custom field if field ID is provided
        if refs_field_id is not None:
            custom_fields = test_case.get("custom_fields", [])
            if debug:
                print(f"    Checking custom fields (looking for ID {refs_field_id})...")
                print(f"    Custom fields found: {len(custom_fields)}")
            for field in custom_fields:
                field_id = field.get("id")
                if field_id == refs_field_id:
                    refs = field.get("value")
                    refs_source = f"custom_field[{field_id}]"
                    if debug:
                        print(f"    Found refs in custom field ID {field_id}: {repr(refs)}")
                    break
        
        # Fallback to system fields if not found in custom fields
        if not refs:
            refs = test_case.get("refs")
            if refs:
                refs_source = "system_field[refs]"
            else:
                refs = test_case.get("references")
                if refs:
                    refs_source = "system_field[references]"
            
            if debug and refs:
                print(f"    Found refs in system field: {repr(refs)}")
        
        if not refs:
            if debug:
                print(f"    No refs field found")
            return []

        if debug:
            print(f"    Refs source: {refs_source}")
            print(f"    Refs type: {type(refs).__name__}")
            print(f"    Refs value: {repr(refs)}")

        # Handle refs as a list of strings (as per Qase API)
        if isinstance(refs, list):
            refs_list = refs
            if debug:
                print(f"    Refs is a list with {len(refs_list)} items")
        elif isinstance(refs, str):
            # If refs is a single string, treat it as a list with one item
            refs_list = [refs]
            if debug:
                print(f"    Refs is a string, converting to list")
        else:
            if debug:
                print(f"    Refs type {type(refs).__name__} not supported, returning empty")
            return []

        # Extract JIRA IDs from each ref string
        jira_ids = []
        for idx, ref in enumerate(refs_list):
            if isinstance(ref, str):
                if debug:
                    print(f"    Processing ref[{idx}]: {repr(ref)}")
                extracted = JIRAIssueExtractor._extract_jira_issue_ids(ref)
                if debug and extracted:
                    print(f"      Extracted JIRA IDs: {extracted}")
                jira_ids.extend(extracted)
            elif debug:
                print(f"    Skipping ref[{idx}]: not a string (type: {type(ref).__name__})")

        # Return unique IDs, preserving order
        seen = set()
        unique_ids = []
        for jira_id in jira_ids:
            if jira_id not in seen:
                seen.add(jira_id)
                unique_ids.append(jira_id)

        if debug:
            print(f"    Final unique JIRA IDs: {unique_ids}")

        return unique_ids


class QaseJIRALinker:
    """Main class for linking JIRA issues to Qase test cases."""

    def __init__(
        self,
        api_token: str,
        project_code: str,
        external_issue_type: str = "jira-cloud",
        batch_size: int = 50,
        refs_field_name: str = "refs",
        refs_field_id: Optional[int] = None
    ):
        """
        Initialize the JIRA linker.

        Args:
            api_token: Qase API token
            project_code: Project code (e.g., 'CR')
            external_issue_type: Type of JIRA instance ('jira-cloud' or 'jira-server')
            batch_size: Number of cases to process in each API batch
            refs_field_name: Name of the refs field to search for (default: "refs")
            refs_field_id: Direct field ID for refs field (if provided, skips search by name)
        """
        from qase_api import QaseAPI
        self.api = QaseAPI(api_token, project_code)
        self.extractor = JIRAIssueExtractor()
        self.external_issue_type = external_issue_type
        self.batch_size = batch_size
        self.refs_field_name = refs_field_name
        self.refs_field_id = refs_field_id

    def find_refs_field_id(self) -> Optional[int]:
        """
        Find the custom field ID for the refs field.
        If refs_field_id is already set, uses that. Otherwise searches custom fields by name.

        Returns:
            Field ID if found, None otherwise
        """
        # If field ID was provided directly, use it
        if self.refs_field_id is not None:
            print(f"Using provided refs field ID: {self.refs_field_id}")
            return self.refs_field_id

        print(f"Fetching custom field definitions to find '{self.refs_field_name}' field...")
        custom_fields = self.api.get_custom_fields()

        if not custom_fields:
            print("Warning: No custom fields found. Will try system fields.")
            return None

        print(f"Found {len(custom_fields)} custom fields")
        
        # Try exact match first, then case-insensitive, and also try "references"
        search_names = [self.refs_field_name, "references", "refs"]
        
        # Debug: Show all custom field names
        print("\nAvailable custom fields:")
        for field in custom_fields[:20]:  # Show first 20
            title = field.get("title", "")
            field_id = field.get("id")
            field_type = field.get("type", "")
            print(f"  - '{title}' (ID: {field_id}, Type: {field_type})")
        if len(custom_fields) > 20:
            print(f"  ... and {len(custom_fields) - 20} more fields")
        
        for field in custom_fields:
            title = field.get("title", "")
            field_id = field.get("id")
            
            # Check if title matches any of our search names
            if title and field_id:
                for search_name in search_names:
                    if title == search_name or title.lower() == search_name.lower():
                        self.refs_field_id = field_id
                        print(f"\n✓ Found '{title}' custom field with ID: {field_id}")
                        return field_id

        print(f"\nWarning: '{self.refs_field_name}' field not found in custom fields. Will try system fields.")
        return None

    def process_all_cases(self, dry_run: bool = False, verbose: bool = False) -> Dict[str, int]:
        """
        Process all test cases and attach JIRA issues.

        Args:
            dry_run: If True, don't make actual API calls
            verbose: If True, show detailed information about each case

        Returns:
            Dictionary with statistics about the linking process
        """
        # First, find the refs field ID from custom fields
        self.find_refs_field_id()

        test_cases = self.api.get_all_test_cases()
        stats = {
            "total": len(test_cases),
            "with_jira_issues": 0,
            "total_jira_issues": 0,  # Total occurrences (may include duplicates across cases)
            "unique_jira_issues": set(),  # Unique JIRA issue IDs across all cases
            "cases_attached": 0,
            "batches_attached": 0,
            "errors": 0,
            "cases_with_refs": 0,
            "cases_without_refs": 0
        }

        print(f"\nAnalyzing {stats['total']} test cases for JIRA issues in refs field...")
        print(f"Using refs field ID: {self.refs_field_id}")

        # Collect all cases with JIRA issues
        jira_links = []
        
        # Debug: Sample a few test cases to see their structure
        if verbose and test_cases:
            print("\n=== Sample test case structure (first case) ===")
            sample_case = test_cases[0]
            print(f"Case ID: {sample_case.get('id')}")
            print(f"Case Code: {sample_case.get('code')}")
            print(f"Available fields: {list(sample_case.keys())}")
            print(f"Custom fields count: {len(sample_case.get('custom_fields', []))}")
            if sample_case.get('custom_fields'):
                print("Custom fields:")
                for cf in sample_case.get('custom_fields', [])[:5]:  # Show first 5
                    print(f"  - ID: {cf.get('id')}, Value: {repr(cf.get('value'))[:100]}")
            print(f"System 'refs' field: {repr(sample_case.get('refs'))}")
            print(f"System 'references' field: {repr(sample_case.get('references'))}")
            print("=" * 60)

        for test_case in test_cases:
            case_id = test_case.get("id")
            case_code = test_case.get("code", "")
            title = test_case.get("title", "Untitled")

            # Debug: Check if refs field exists
            refs_found = False
            refs_value = None
            
            if self.refs_field_id is not None:
                custom_fields = test_case.get("custom_fields", [])
                for field in custom_fields:
                    if field.get("id") == self.refs_field_id:
                        refs_value = field.get("value")
                        refs_found = True
                        break
            
            if not refs_found:
                refs_value = test_case.get("refs") or test_case.get("references")
                if refs_value:
                    refs_found = True
            
            if refs_found:
                stats["cases_with_refs"] += 1
            else:
                stats["cases_without_refs"] += 1

            jira_ids = self.extractor.extract_from_test_case(test_case, self.refs_field_id, debug=verbose)

            if jira_ids:
                stats["with_jira_issues"] += 1
                stats["total_jira_issues"] += len(jira_ids)
                stats["unique_jira_issues"].update(jira_ids)  # Add to set of unique issues
                jira_links.append({
                    "case_id": case_id,
                    "external_issues": jira_ids
                })

                if verbose:
                    print(f"Case {case_code} ({case_id}): '{title}'")
                    print(f"  Refs field ID: {self.refs_field_id}")
                    print(f"  Refs value: {repr(refs_value)}")
                    print(f"  Refs type: {type(refs_value).__name__}")
                    print(f"  Found JIRA issues: {jira_ids}")
            elif verbose and refs_found:
                # Show cases that have refs but no JIRA IDs found
                print(f"Case {case_code} ({case_id}): '{title}'")
                print(f"  Has refs field: Yes")
                print(f"  Refs value: {repr(refs_value)}")
                print(f"  Refs type: {type(refs_value).__name__}")
                print(f"  No JIRA issues found in refs")

        print(f"\n=== Analysis Summary ===")
        print(f"Total test cases: {stats['total']}")
        print(f"Cases with refs field: {stats['cases_with_refs']}")
        print(f"Cases without refs field: {stats['cases_without_refs']}")
        print(f"Cases with JIRA issues found: {stats['with_jira_issues']}")
        print(f"Total JIRA issue occurrences: {stats['total_jira_issues']} (counts duplicates across cases)")
        print(f"Unique JIRA issues: {len(stats['unique_jira_issues'])} (distinct issue IDs)")
        if stats['with_jira_issues'] > 0:
            avg_issues_per_case = stats['total_jira_issues'] / stats['with_jira_issues']
            print(f"Average JIRA issues per case: {avg_issues_per_case:.2f}")

        if not jira_links:
            print("\nNo JIRA issues found in any test cases.")
            return stats

        # Attach JIRA issues in batches
        if not dry_run:
            print(f"\nAttaching JIRA issues in batches of {self.batch_size}...")
            total_attached = 0
            total_failed = 0
            failed_batches = []  # Store failed batches for retry

            for i in range(0, len(jira_links), self.batch_size):
                batch = jira_links[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1

                try:
                    if self.api.attach_external_issues(self.external_issue_type, batch):
                        total_attached += len(batch)
                        stats["cases_attached"] += len(batch)
                        stats["batches_attached"] += 1
                        print(f"  ✓ Successfully attached batch {batch_num} ({len(batch)} cases)")
                    else:
                        # Batch failed - store for individual retry
                        failed_batches.append((batch_num, batch))
                        print(f"  ✗ Failed to attach batch {batch_num} ({len(batch)} cases) - will retry individually")
                except Exception as e:
                    # Batch failed with exception - store for individual retry
                    failed_batches.append((batch_num, batch))
                    print(f"  ✗ Exception attaching batch {batch_num}: {e} - will retry individually")

            # Retry failed batches as individual cases
            if failed_batches:
                print(f"\nRetrying {len(failed_batches)} failed batches as individual cases...")
                for batch_num, batch in failed_batches:
                    for link in batch:
                        case_id = link.get("case_id")
                        jira_issues = link.get("external_issues", [])
                        try:
                            if self.api.attach_external_issues(self.external_issue_type, [link]):
                                total_attached += 1
                                stats["cases_attached"] += 1
                                if verbose:
                                    print(f"    ✓ Case {case_id}: Successfully attached {len(jira_issues)} JIRA issues")
                            else:
                                total_failed += 1
                                stats["errors"] += 1
                                if verbose:
                                    print(f"    ✗ Case {case_id}: Failed to attach {len(jira_issues)} JIRA issues")
                        except Exception as e:
                            total_failed += 1
                            stats["errors"] += 1
                            if verbose:
                                print(f"    ✗ Case {case_id}: Exception - {e}")

            print(f"\nAttachment complete: {total_attached} cases succeeded, {total_failed} cases failed")
        else:
            # Dry run: show what would be attached
            print(f"\n[DRY RUN] Would attach JIRA issues in {len(jira_links) // self.batch_size + 1} batches:")
            for i in range(0, len(jira_links), self.batch_size):
                batch = jira_links[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                print(f"  Batch {batch_num}: {len(batch)} cases")
                if verbose:
                    for link in batch[:5]:  # Show first 5 cases in batch
                        print(f"    Case {link['case_id']}: {link['external_issues']}")
                    if len(batch) > 5:
                        print(f"    ... and {len(batch) - 5} more cases")

        return stats

    def run(self, dry_run: bool = False, verbose: bool = False):
        """
        Main execution method.

        Args:
            dry_run: If True, don't make actual API calls
            verbose: If True, show detailed information about each case
        """
        print("=" * 60)
        print("Qase JIRA Issue Linker")
        print("=" * 60)
        if dry_run:
            print("DRY RUN MODE - No changes will be made")
        if verbose:
            print("VERBOSE MODE - Showing detailed analysis")
        print(f"External issue type: {self.external_issue_type}")
        print(f"Batch size: {self.batch_size}")
        print()

        stats = self.process_all_cases(dry_run=dry_run, verbose=verbose)

        print("\n" + "=" * 60)
        print("Final Summary:")
        print(f"  Total test cases: {stats['total']}")
        print(f"  Cases with refs field: {stats['cases_with_refs']}")
        print(f"  Cases without refs field: {stats['cases_without_refs']}")
        print(f"  Cases with JIRA issues: {stats['with_jira_issues']}")
        print(f"  Total JIRA issue occurrences: {stats['total_jira_issues']} (may include duplicates)")
        print(f"  Unique JIRA issues: {len(stats['unique_jira_issues'])} (distinct issue IDs)")
        if stats['with_jira_issues'] > 0:
            avg_issues_per_case = stats['total_jira_issues'] / stats['with_jira_issues']
            print(f"  Average issues per case: {avg_issues_per_case:.2f}")
        if not dry_run:
            print(f"  Cases attached: {stats['cases_attached']}")
            print(f"  Batches attached: {stats['batches_attached']}")
            print(f"  Errors: {stats['errors']}")
        print("=" * 60)


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Path to the config file

    Returns:
        Dictionary with configuration values

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid or missing required fields
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config file '{config_path}' not found. "
            f"Please create it with 'api_token' and 'project_code' fields."
        )

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Link JIRA issues to Qase test cases by extracting JIRA IDs from test case fields"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)"
    )
    parser.add_argument(
        "--token",
        help="Qase API token (overrides config file)"
    )
    parser.add_argument(
        "--project",
        help="Qase project code (overrides config file)"
    )
    parser.add_argument(
        "--type",
        choices=["jira-cloud", "jira-server"],
        default="jira-cloud",
        help="Type of JIRA instance (default: jira-cloud)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of cases per batch (default: 50)"
    )
    parser.add_argument(
        "--refs-field",
        default=None,
        help="Name of the refs field to search for (default: from config.json or 'refs')"
    )
    parser.add_argument(
        "--refs-field-id",
        type=int,
        help="Direct ID of the refs custom field (if known, skips search by name)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information about each test case"
    )

    args = parser.parse_args()

    # Load config from file
    api_token = args.token
    project_code = args.project
    refs_field_name = args.refs_field
    refs_field_id = args.refs_field_id

    try:
        config = load_config(args.config)
        
        # Load API credentials if not provided via CLI
        api_token = api_token or config.get("api_token")
        project_code = project_code or config.get("project_code")
        
        # Load refs field name from config if not provided via CLI
        # Priority: CLI argument > config.json > default ("refs")
        if not refs_field_name:
            config_refs_field = config.get("jira_refs_field")
            if config_refs_field:
                refs_field_name = config_refs_field
            else:
                refs_field_name = "refs"  # Default fallback
        
        # Load refs field ID from config if not provided via CLI
        if not refs_field_id:
            config_refs_field_id = config.get("jira_refs_field_id")
            if config_refs_field_id:
                refs_field_id = config_refs_field_id
        
        # Also check for external_issues config
        external_issues_config = config.get("tests", {}).get("external_issues", {})
        if not args.type and external_issues_config.get("type"):
            args.type = external_issues_config.get("type")
        if not args.batch_size and external_issues_config.get("batch_size"):
            args.batch_size = external_issues_config.get("batch_size")
    except (FileNotFoundError, ValueError) as e:
        if not api_token or not project_code:
            parser.error(
                f"Either provide --token and --project arguments, "
                f"or create a valid config file. Error: {e}"
            )

    if not api_token:
        parser.error("API token is required (provide via --token or config file)")
    if not project_code:
        parser.error("Project code is required (provide via --project or config file)")

    # Ensure refs_field_name is set (should always be set by now, but safety check)
    if not refs_field_name:
        refs_field_name = "refs"

    linker = QaseJIRALinker(
        api_token=api_token,
        project_code=project_code,
        external_issue_type=args.type,
        batch_size=args.batch_size,
        refs_field_name=refs_field_name,
        refs_field_id=refs_field_id
    )

    linker.run(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
