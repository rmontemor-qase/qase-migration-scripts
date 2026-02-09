"""
Qase API Client

Handles all API interactions with the Qase API.
"""

import requests
from typing import Dict, List, Any, Optional


class QaseAPI:
    """Client for interacting with the Qase API."""

    def __init__(self, api_token: str, project_code: str, base_url: str = "https://api.qase.io/v1"):
        """
        Initialize the Qase API client.

        Args:
            api_token: Qase API token
            project_code: Project code (e.g., 'CR')
            base_url: Base URL for the API (default: https://api.qase.io/v1)
        """
        self.api_token = api_token
        self.project_code = project_code
        self.base_url = base_url
        self.headers = {
            "Token": api_token,
            "accept": "application/json",
            "content-type": "application/json"
        }
        self.max_limit = 100

    def get_all_test_cases(self) -> List[Dict[str, Any]]:
        """
        Fetch all test cases from the project using pagination.

        Returns:
            List of all test case dictionaries
        """
        all_cases = []
        offset = 0
        limit = self.max_limit

        print(f"Fetching test cases from project '{self.project_code}'...")

        while True:
            url = f"{self.base_url}/case/{self.project_code}"
            params = {"limit": limit, "offset": offset}

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()

                if not data.get("status"):
                    print(f"Error: API returned status false")
                    break

                result = data.get("result", {})
                entities = result.get("entities", [])
                total = result.get("total", 0)
                count = result.get("count", 0)

                all_cases.extend(entities)
                print(f"Fetched {len(entities)} cases (offset: {offset}, total: {total})")

                # Check if we've fetched all cases
                if offset + count >= total or len(entities) == 0:
                    break

                offset += count

            except requests.exceptions.RequestException as e:
                print(f"Error fetching test cases: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response: {e.response.text}")
                break

        print(f"Total test cases fetched: {len(all_cases)}")
        return all_cases

    def get_system_fields(self) -> List[Dict[str, Any]]:
        """
        Fetch all system field definitions.

        Returns:
            List of system field dictionaries
        """
        url = f"{self.base_url}/system_field"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                print(f"Error: API returned status false")
                return []

            result = data.get("result", [])
            return result
        except requests.exceptions.RequestException as e:
            print(f"Error fetching system fields: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return []

    def get_custom_fields(self) -> List[Dict[str, Any]]:
        """
        Fetch all custom field definitions from the workspace using pagination.

        Returns:
            List of custom field dictionaries
        """
        all_fields = []
        offset = 0
        limit = self.max_limit

        print(f"Fetching custom fields from workspace...")

        while True:
            url = f"{self.base_url}/custom_field"
            params = {"limit": limit, "offset": offset}

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()

                if not data.get("status"):
                    print(f"Error: API returned status false")
                    break

                result = data.get("result", {})
                entities = result.get("entities", [])
                total = result.get("total", 0)
                count = result.get("count", 0)

                all_fields.extend(entities)
                print(f"Fetched {len(entities)} custom fields (offset: {offset}, total: {total})")

                # Check if we've fetched all fields
                if offset + count >= total or len(entities) == 0:
                    break

                offset += count

            except requests.exceptions.RequestException as e:
                print(f"Error fetching custom fields: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response: {e.response.text}")
                break

        print(f"Total custom fields fetched: {len(all_fields)}")
        return all_fields

    def update_test_case(self, case_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update a test case with the provided updates.

        Args:
            case_id: ID of the test case to update
            updates: Dictionary containing fields to update

        Returns:
            True if update was successful, False otherwise
        """
        url = f"{self.base_url}/case/{self.project_code}/{case_id}"

        try:
            response = requests.patch(url, headers=self.headers, json=updates)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error updating case {case_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return False
