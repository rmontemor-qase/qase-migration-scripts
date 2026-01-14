#!/usr/bin/env python3
"""
Qase Migration Script: Fix Broken CSV File References

This script:
1. Fetches all test cases from a Qase project
2. Identifies broken CSV references (those with ! prefix in markdown)
3. Fixes them by removing the ! prefix
4. Updates the test cases via PATCH requests
"""

import json
import os
import argparse
from typing import Dict

from qase_api import QaseAPI
from csv_fixer import CSVFixer


class QaseCSVMigration:
    """Main class for migrating and fixing CSV references in Qase test cases."""

    def __init__(self, api_token: str, project_code: str):
        """
        Initialize the migration tool.

        Args:
            api_token: Qase API token
            project_code: Project code (e.g., 'CR')
        """
        self.api = QaseAPI(api_token, project_code)
        self.fixer = CSVFixer()

    def process_all_cases(self, dry_run: bool = False, verbose: bool = False) -> Dict[str, int]:
        """
        Process all test cases and fix broken CSV references.

        Args:
            dry_run: If True, don't make actual updates
            verbose: If True, show detailed information about each case

        Returns:
            Dictionary with statistics about the migration
        """
        test_cases = self.api.get_all_test_cases()
        stats = {
            "total": len(test_cases),
            "needs_fixing": 0,
            "fixed": 0,
            "errors": 0
        }

        print(f"\nAnalyzing {stats['total']} test cases...")

        for test_case in test_cases:
            case_id = test_case.get("id")
            title = test_case.get("title", "Untitled")

            updates = self.fixer.analyze_test_case(test_case)

            if verbose:
                # Show what fields were checked and if they have broken refs
                desc = test_case.get("description", "")
                prec = test_case.get("preconditions", "")
                postc = test_case.get("postconditions", "")
                steps = test_case.get("steps", [])
                custom = test_case.get("custom_fields", [])
                
                desc_broken = self.fixer.find_broken_csv_references(desc)
                prec_broken = self.fixer.find_broken_csv_references(prec)
                postc_broken = self.fixer.find_broken_csv_references(postc)
                steps_broken = sum(len(self.fixer.find_broken_csv_references(s.get("action", "") or s.get("expected_result", "") or s.get("data", ""))) for s in steps)
                custom_broken = sum(len(self.fixer.find_broken_csv_references(f.get("value", ""))) for f in custom)
                
                print(f"Case {case_id} ('{title}'): desc={len(desc_broken)}, prec={len(prec_broken)}, postc={len(postc_broken)}, steps={steps_broken}, custom={custom_broken}")

            if updates:
                stats["needs_fixing"] += 1
                print(f"\nCase {case_id} ('{title}') needs fixing:")
                print(f"  Fields to update: {list(updates.keys())}")

                if not dry_run:
                    if self.api.update_test_case(case_id, updates):
                        stats["fixed"] += 1
                        print(f"  ✓ Successfully updated case {case_id}")
                    else:
                        stats["errors"] += 1
                        print(f"  ✗ Failed to update case {case_id}")
                else:
                    print(f"  [DRY RUN] Would update with: {json.dumps(updates, indent=2)}")
                    stats["fixed"] += 1  # Count as would-be fixed in dry run

        return stats

    def run(self, dry_run: bool = False, verbose: bool = False):
        """
        Main execution method.

        Args:
            dry_run: If True, don't make actual updates
            verbose: If True, show detailed information about each case
        """
        print("=" * 60)
        print("Qase CSV Reference Fixer")
        print("=" * 60)
        if dry_run:
            print("DRY RUN MODE - No changes will be made")
        if verbose:
            print("VERBOSE MODE - Showing detailed analysis")
        print()

        stats = self.process_all_cases(dry_run=dry_run, verbose=verbose)

        print("\n" + "=" * 60)
        print("Summary:")
        print(f"  Total test cases: {stats['total']}")
        print(f"  Cases needing fixes: {stats['needs_fixing']}")
        print(f"  Cases fixed: {stats['fixed']}")
        print(f"  Errors: {stats['errors']}")
        if stats['needs_fixing'] == 0 and stats['total'] > 0:
            print("\n  [INFO] All test cases are already fixed! No broken CSV references found.")
        print("=" * 60)


def load_config(config_path: str = "config.json") -> Dict[str, str]:
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

    if "api_token" not in config:
        raise ValueError("Config file must contain 'api_token' field")
    if "project_code" not in config:
        raise ValueError("Config file must contain 'project_code' field")

    return config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix broken CSV file references in Qase test cases"
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

    # Load config from file if token/project not provided via CLI
    api_token = args.token
    project_code = args.project

    if not api_token or not project_code:
        try:
            config = load_config(args.config)
            api_token = api_token or config.get("api_token")
            project_code = project_code or config.get("project_code")
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

    migration = QaseCSVMigration(
        api_token=api_token,
        project_code=project_code
    )

    migration.run(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
