"""
CSV Reference Fixer

Handles the logic for finding and fixing broken CSV file references in test cases.
"""

import re
from typing import Dict, List, Any, Optional, Tuple


class CSVFixer:
    """Handles fixing broken CSV references in test case fields."""

    @staticmethod
    def find_broken_csv_references(text: Optional[str]) -> List[Tuple[str, str]]:
        """
        Find broken CSV references in text.

        Args:
            text: Text to search for broken CSV references

        Returns:
            List of tuples: (broken_pattern, fixed_pattern)
            Broken format: ![filename.csv](url) or fully escaped markdown
            Fixed format: [filename.csv](url)
        """
        if not text:
            return []

        broken_refs = []
        
        # Pattern 1: Match unescaped broken references: ![filename.csv](url)
        pattern1 = r'(?<!\\)!\[([^\]]+\.csv[^\]]*)\]\(([^\)]+)\)'
        
        # Pattern 2: Match escaped broken references: \![filename.csv](url)
        # (where ! is escaped but brackets/parens are not)
        pattern2 = r'\\!\[([^\]]+\.csv[^\]]*)\]\(([^\)]+)\)'
        
        # Pattern 3: Match fully escaped markdown: \!\[filename\.csv\]\(url\)
        # This handles cases where all markdown syntax is escaped
        # Match: backslash-exclamation-backslash-bracket, then filename with .csv, 
        # then backslash-bracket-backslash-paren, then URL, then backslash-paren
        # Use a more flexible pattern that allows escaped chars in filename/URL
        pattern3 = r'\\!\\\[(.*?\.csv.*?)\\\]\\\((.*?)\\\)'

        # Check for unescaped broken references
        matches = re.finditer(pattern1, text)
        for match in matches:
            filename = match.group(1)
            url = match.group(2)
            broken_pattern = match.group(0)
            fixed_pattern = f"[{filename}]({url})"
            broken_refs.append((broken_pattern, fixed_pattern))

        # Check for escaped ! but unescaped brackets
        matches = re.finditer(pattern2, text)
        for match in matches:
            filename = match.group(1)
            url = match.group(2)
            broken_pattern = match.group(0)  # Includes the backslash before !
            fixed_pattern = f"[{filename}]({url})"
            broken_refs.append((broken_pattern, fixed_pattern))

        # Check for fully escaped markdown (all syntax escaped)
        matches = re.finditer(pattern3, text)
        for match in matches:
            # The filename and URL have escaped characters that need to be unescaped
            filename_raw = match.group(1)
            url_raw = match.group(2)
            # Unescape common escaped characters in filename
            # Order matters: do \\\\ first, then other escapes
            filename = filename_raw.replace('\\\\', '\\').replace('\\_', '_').replace('\\(', '(').replace('\\)', ')').replace('\\.', '.')
            # Unescape URL - handle all escaped characters including those in the path
            url = url_raw.replace('\\\\', '\\').replace('\\_', '_').replace('\\(', '(').replace('\\)', ')').replace('\\.', '.').replace('\\/', '/')
            broken_pattern = match.group(0)  # Full escaped pattern
            fixed_pattern = f"[{filename}]({url})"
            broken_refs.append((broken_pattern, fixed_pattern))

        return broken_refs

    @staticmethod
    def fix_text(text: Optional[str]) -> Optional[str]:
        """
        Fix broken CSV references in text by removing ! prefix.

        Args:
            text: Text that may contain broken CSV references

        Returns:
            Fixed text if changes were made, None otherwise
        """
        if not text:
            return None

        broken_refs = CSVFixer.find_broken_csv_references(text)
        if not broken_refs:
            return None

        fixed_text = text
        for broken, fixed in broken_refs:
            fixed_text = fixed_text.replace(broken, fixed)

        return fixed_text if fixed_text != text else None

    @staticmethod
    def analyze_test_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a test case and return fields that need to be updated.

        Args:
            test_case: Test case dictionary from the API

        Returns:
            Dictionary with only the fields that need fixing
        """
        updates = {}

        # Check description
        description = test_case.get("description")
        fixed_description = CSVFixer.fix_text(description)
        if fixed_description:
            updates["description"] = fixed_description

        # Check preconditions
        preconditions = test_case.get("preconditions")
        fixed_preconditions = CSVFixer.fix_text(preconditions)
        if fixed_preconditions:
            updates["preconditions"] = fixed_preconditions

        # Check postconditions
        postconditions = test_case.get("postconditions")
        fixed_postconditions = CSVFixer.fix_text(postconditions)
        if fixed_postconditions:
            updates["postconditions"] = fixed_postconditions

        # Check steps
        steps = test_case.get("steps", [])
        if steps:
            fixed_steps = []
            steps_need_update = False

            for step in steps:
                # Build the step update object with only fields that need to be sent
                fixed_step = {}
                step_updated = False

                # Include position (required for step identification)
                if "position" in step:
                    fixed_step["position"] = step["position"]
                
                # Include hash if it exists (may be required for step updates)
                if "hash" in step:
                    fixed_step["hash"] = step["hash"]

                # Check action field
                action = step.get("action")
                fixed_action = CSVFixer.fix_text(action)
                if fixed_action:
                    fixed_step["action"] = fixed_action
                    step_updated = True
                elif action is not None:
                    fixed_step["action"] = action

                # Check expected_result field
                expected_result = step.get("expected_result")
                fixed_expected_result = CSVFixer.fix_text(expected_result)
                if fixed_expected_result:
                    fixed_step["expected_result"] = fixed_expected_result
                    step_updated = True
                elif expected_result is not None:
                    fixed_step["expected_result"] = expected_result

                # Check data field
                data = step.get("data")
                fixed_data = CSVFixer.fix_text(data)
                if fixed_data:
                    fixed_step["data"] = fixed_data
                    step_updated = True
                elif data is not None:
                    fixed_step["data"] = data

                if step_updated:
                    steps_need_update = True

                # Always include the step in the array to maintain structure
                fixed_steps.append(fixed_step)

            if steps_need_update:
                updates["steps"] = fixed_steps

        # Check custom_fields
        # Note: API expects "custom_field" (singular) as an object with field IDs as keys
        custom_fields = test_case.get("custom_fields", [])
        if custom_fields:
            custom_field_updates = {}
            custom_fields_need_update = False

            for field in custom_fields:
                field_id = field.get("id")
                value = field.get("value")
                fixed_value = CSVFixer.fix_text(value)
                if fixed_value and field_id is not None:
                    # API expects field ID as string key
                    custom_field_updates[str(field_id)] = fixed_value
                    custom_fields_need_update = True

            if custom_fields_need_update:
                updates["custom_field"] = custom_field_updates

        return updates
