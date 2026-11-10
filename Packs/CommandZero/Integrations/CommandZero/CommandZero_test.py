"""
CommandZero Integration Unit Tests
Tests use mocked responses — no real API connection needed.
Real API interaction is tested via Test Playbooks in XSOAR.
"""

import json
import sys
import types
import pytest
from unittest.mock import MagicMock

# ── Stub XSOAR libraries BEFORE importing CommandZero ──────────
# Must happen at module level before any CommandZero import.


class MockBaseClient:
    def __init__(self, base_url="", verify=True, proxy=False, **kwargs):
        self._base_url = base_url
        self._verify = verify
        self._proxy = proxy

    def _http_request(self, *args, **kwargs):
        pass


class MockDemisto:
    @staticmethod
    def params():
        return {}

    @staticmethod
    def args():
        return {}

    @staticmethod
    def command():
        return ""

    @staticmethod
    def debug(msg):
        pass

    @staticmethod
    def info(msg):
        pass

    @staticmethod
    def error(msg):
        pass


class CommandResults:
    def __init__(
        self,
        readable_output="",
        outputs_prefix="",
        outputs_key_field="",
        outputs=None,
        raw_response=None,
        mark_as_note=False,
        entry_type=None,
        scheduled_command=None,
    ):
        self.readable_output = readable_output
        self.outputs_prefix = outputs_prefix
        self.outputs_key_field = outputs_key_field
        self.outputs = outputs or {}
        self.raw_response = raw_response
        self.mark_as_note = mark_as_note
        self.entry_type = entry_type
        self.scheduled_command = scheduled_command


class EntryType:
    NOTE = 1
    ERROR = 4
    WARNING = 11


class ScheduledCommand:
    """Records what the integration asked the server to schedule."""

    def __init__(self, command, next_run_in_seconds, args=None, timeout_in_seconds=None, end_date=None, items_remaining=0):
        self.command = command
        self.next_run_in_seconds = next_run_in_seconds
        self.args = args
        self.timeout_in_seconds = timeout_in_seconds

    @staticmethod
    def raise_error_if_not_supported():
        return None


def arg_to_number(val, arg_name=None, required=False):
    if val is None or val == "":
        return None
    return int(val)


def tableToMarkdown(name, data, headers=None, removeNull=False):
    # Keeps the heading, so tests can assert on it.
    return f"### {name}\n{data}"


def argToBoolean(val):
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes")


def return_results(val):
    pass


def return_error(msg, error=None):
    raise Exception(msg)


class DemistoException(Exception):
    """Mirrors the real one closely enough: carries the failing response."""

    def __init__(self, message, exception=None, res=None):
        super().__init__(message)
        self.res = res


class FakeResponse:
    """Stands in for a requests.Response on an error path."""

    def __init__(self, status_code, body=None, headers=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def json(self):
        if self._body is None:
            raise ValueError("no JSON body")
        return self._body


# Inject demistomock
demisto_mock = types.ModuleType("demistomock")
demisto_mock.params = MockDemisto.params
demisto_mock.args = MockDemisto.args
demisto_mock.command = MockDemisto.command
demisto_mock.debug = MockDemisto.debug
demisto_mock.info = MockDemisto.info
demisto_mock.error = MockDemisto.error
sys.modules["demistomock"] = demisto_mock

# Inject CommonServerPython
common_mock = types.ModuleType("CommonServerPython")
common_mock.BaseClient = MockBaseClient
common_mock.CommandResults = CommandResults
common_mock.tableToMarkdown = tableToMarkdown
common_mock.argToBoolean = argToBoolean
common_mock.arg_to_number = arg_to_number
common_mock.EntryType = EntryType
common_mock.ScheduledCommand = ScheduledCommand
common_mock.return_results = return_results
common_mock.return_error = return_error
common_mock.DemistoException = DemistoException
sys.modules["CommonServerPython"] = common_mock

# Inject CommonServerUserPython
sys.modules["CommonServerUserPython"] = types.ModuleType("CommonServerUserPython")

# Import CommandZero
from CommandZero import run_test_module, Client  # noqa: E402


# ── Tests ───────────────────────────────────────────────────────

ORG_ID = "51c264ff-5a98-4f15-b7e1-07158d35151c"


def healthy_client(organizations=None, org_id=ORG_ID):
    """A client whose health check passes and whose grants are controllable."""
    client = MagicMock(spec=Client)
    client.health_check.return_value = {"status": "ok"}
    client.organization_id = org_id
    if organizations is None:
        organizations = [{"id": ORG_ID, "name": "warniCo"}]
    client.list_organizations.return_value = {"organizations": organizations, "next": "", "warnings": [], "errors": []}
    return client


def test_connection_test_follows_organization_pagination():
    """
    Organizations are paginated, so scanning only the first page could wrongly
    report that a key cannot reach the configured organization.
    """
    client = MagicMock(spec=Client)
    client.health_check.return_value = {"status": "ok"}
    client.organization_id = ORG_ID
    client.list_organizations.side_effect = [
        {"organizations": [{"id": "other-1"}], "next": "cursor-1", "warnings": [], "errors": []},
        {"organizations": [{"id": ORG_ID, "name": "warniCo"}], "next": "", "warnings": [], "errors": []},
    ]

    assert run_test_module(client) == "ok"
    assert client.list_organizations.call_count == 2
    assert client.list_organizations.call_args_list[1][0][0]["next"] == "cursor-1"


def test_organization_paging_stops_at_the_page_cap():
    """A server that always returns a cursor must not loop forever."""
    from CommandZero import fetch_all_organizations, MAX_ORG_PAGES

    client = MagicMock(spec=Client)
    client.list_organizations.return_value = {
        "organizations": [{"id": "org-x"}],
        "next": "always-more",
        "warnings": [],
        "errors": [],
    }

    organizations = fetch_all_organizations(client)
    assert client.list_organizations.call_count == MAX_ORG_PAGES
    assert len(organizations) == MAX_ORG_PAGES


def test_module_returns_ok_when_api_healthy_and_org_reachable():
    """
    test-module returns 'ok' when the API is healthy and the configured
    organization is among those the key can reach — makes the Test button go
    green in XSOAR.
    """
    result = run_test_module(healthy_client())
    assert result == "ok"


def test_module_fails_when_key_cannot_reach_the_configured_org():
    """
    A valid key does not imply access to the configured organization. Catching
    it here beats a 403 on every later command.
    """
    client = healthy_client(organizations=[{"id": "aaaaaaaa-0000-0000-0000-000000000000", "name": "Other Co"}])

    result = run_test_module(client)
    assert result.startswith("Connection failed")
    assert ORG_ID in result
    assert "Other Co" in result
    assert "aaaaaaaa-0000-0000-0000-000000000000" in result


def test_module_reports_when_the_key_reaches_no_organizations():
    client = healthy_client(organizations=[])
    result = run_test_module(client)
    assert result.startswith("Connection failed")
    assert "none" in result


def test_module_truncates_a_long_organization_list():
    """A key with broad grants must not produce an unreadable error."""
    from CommandZero import MAX_ORGS_IN_ERROR

    client = healthy_client(organizations=[{"id": f"org-{n}", "name": f"Org {n}"} for n in range(12)])

    result = run_test_module(client)
    assert "and 7 more" in result
    assert result.count("Org ") == MAX_ORGS_IN_ERROR


def test_module_does_not_check_orgs_when_the_api_is_unhealthy():
    """No point listing organizations if the service is already failing."""
    client = healthy_client()
    client.health_check.return_value = {"status": "error"}

    run_test_module(client)
    client.list_organizations.assert_not_called()


def test_module_returns_failure_when_api_unhealthy():
    """
    test-module returns a failure message if the API
    returns anything other than status ok.
    """
    client = healthy_client()
    client.health_check.return_value = {"status": "error"}

    result = run_test_module(client)
    assert result.startswith("Connection failed")


def test_module_handles_empty_response():
    """
    test-module should not crash on an empty response.
    """
    client = healthy_client()
    client.health_check.return_value = {}

    result = run_test_module(client)
    assert result.startswith("Connection failed")


def test_get_investigation_returns_data():
    from CommandZero import get_investigation_command, Client

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = {
        "id": "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35",
        "title": "High-Risk Sign-In from Brazil",
        "status": "open",
        "severity": "low",
        "category": "Security Alert",
        "completed": False,
        "verdict": [],
        "summary": "",
        "description": "What users with risky sign-in activity were detected?",
        "startTime": "2024-09-20T18:09:28Z",
        "endTime": "2024-09-27T18:09:28Z",
        "impact": "",
        "confidenceLevel": "",
        "observables": [{"type": "IP_ADDRESS", "value": "203.0.113.190", "origin": ["lead"]}],
        "consoleUrl": "https://ui.cmdzero.io/#/inv-detail?id=50ce9d59",
        "createdTime": "2024-09-27T18:10:00Z",
        "updatedTime": "2025-04-07T15:02:43Z",
    }
    result = get_investigation_command(client, {"investigation_id": "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35"})
    assert result.outputs_prefix == "CommandZero.Investigation"
    assert result.outputs["id"] == "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35"
    assert result.outputs["status"] == "open"
    assert len(result.outputs["observables"]) == 1


def test_get_investigation_requires_id():
    from CommandZero import get_investigation_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(Exception):
        get_investigation_command(client, {})


def test_list_remediation_templates_filter_by_subject_type():
    from CommandZero import list_remediation_templates_command, Client

    client = MagicMock(spec=Client)
    client.list_remediation_templates.return_value = {"remediation-templates": [], "next": "", "warnings": [], "errors": []}
    list_remediation_templates_command(client, {"subject_type": "CROWDSTRIKE_DEVICE_ID", "limit": "50"})
    call_params = client.list_remediation_templates.call_args[0][0]
    assert call_params["subjectType"] == "CROWDSTRIKE_DEVICE_ID"


def test_create_remediation_returns_data():
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.return_value = {
        "id": "8f14e45f-ceea-467f-a123-f6b2c3d4e5f6",
        "status": "pending",
        "templateId": "r-39a26e0p32micg",
        "templateName": "Disable Microsoft Entra User by User Principal Name",
        "subject": {"type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME", "value": "jmaldive@warnicorn.com"},
        "justification": "Test remediation",
        "organizationId": "51c264ff-5a98-4f15-b7e1-07158d35151c",
        "error": "",
        "createdTime": "2026-06-15T18:00:00Z",
        "updatedTime": "2026-06-15T18:00:00Z",
        "createdBy": {"type": "application", "name": "XSOAR Integration"},
    }
    result = create_remediation_command(
        client,
        {
            "template_id": "r-39a26e0p32micg",
            "subject_type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME",
            "subject_value": "jmaldive@warnicorn.com",
            "justification": "Test remediation",
        },
    )
    assert result.outputs_prefix == "CommandZero.Remediation"
    assert result.outputs["id"] == "8f14e45f-ceea-467f-a123-f6b2c3d4e5f6"
    assert result.outputs["status"] == "pending"


def test_create_remediation_requires_all_fields():
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(Exception):
        create_remediation_command(
            client,
            {
                "template_id": "r-39a26e0p32micg",
                # subject_type, subject_value, justification missing
            },
        )


def test_create_remediation_with_postback():
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.return_value = {
        "id": "8f14e45f-ceea-467f-a123-f6b2c3d4e5f6",
        "status": "pending",
        "templateId": "r-39a26e0p32micg",
        "templateName": "Disable User",
        "subject": {"type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME", "value": "test@test.com"},
        "justification": "Test",
        "organizationId": "51c264ff-5a98-4f15-b7e1-07158d35151c",
        "error": "",
        "createdTime": "2026-06-15T18:00:00Z",
        "updatedTime": "2026-06-15T18:00:00Z",
    }
    create_remediation_command(
        client,
        {
            "template_id": "r-39a26e0p32micg",
            "subject_type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME",
            "subject_value": "test@test.com",
            "justification": "Test",
            "postback_url": "https://xsoar.company.com/webhooks/cmdzero",
            "postback_token": "secret",
        },
    )
    body = client.create_remediation.call_args[0][0]
    assert "postback" in body
    assert body["postback"]["url"] == "https://xsoar.company.com/webhooks/cmdzero"


COMPLETED_INVESTIGATION = {
    "id": "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35",
    "title": "Credential compromise for jmaldive@warnicorn.com",
    "status": "completed",
    "completed": True,
    "completedTime": "2026-09-15T12:00:00Z",
    "severity": "high",
    "confidenceLevel": "high",
    "category": "Credential Compromise",
    "verdict": ["Malicious", "Credential Theft"],
    "summary": "## Findings\nThe account was accessed from an unusual ASN.",
    "observables": [
        {"type": "EMAIL_ADDRESS", "value": "jmaldive@warnicorn.com", "origin": ["alert", "subject"]},
        {"type": "IP_ADDRESS", "value": "203.0.113.190", "origin": ["subject"]},
    ],
    "consoleUrl": "https://ui.cmdzero.io/#/inv-detail?id=50ce9d59",
}


# ── UC5: polling ────────────────────────────────────────────────


def test_results_stops_polling_on_completion_and_posts_note():
    from CommandZero import investigation_results_command, Client

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = investigation_results_command(client, {"investigation_id": "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35"})

    assert result.scheduled_command is None
    assert result.mark_as_note is True
    assert "Malicious, Credential Theft" in result.readable_output
    assert result.outputs["id"] == "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35"


def test_results_stops_polling_on_failure_and_warns():
    """A failed investigation is terminal and must be visible, not silent."""
    from CommandZero import investigation_results_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = {
        "id": "inv-1",
        "status": "failed",
        "completed": False,
        "error": "Data source unavailable",
    }

    result = investigation_results_command(client, {"investigation_id": "inv-1"})

    assert result.scheduled_command is None
    assert result.entry_type == EntryType.WARNING
    assert "Failed" in result.readable_output
    assert "Data source unavailable" in result.readable_output


def test_results_can_suppress_the_note():
    from CommandZero import investigation_results_command, Client

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = investigation_results_command(
        client, {"investigation_id": "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35", "post_note": "false"}
    )
    assert result.mark_as_note is False
    assert "Malicious" not in result.readable_output
    assert result.outputs["id"] == "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35"


# ── UC5: note composition ───────────────────────────────────────


def test_note_contains_every_required_writeback_field():
    """OC5 enumerates what the summary must carry."""
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(COMPLETED_INVESTIGATION)

    assert "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35" in note  # investigation ID
    assert "Malicious, Credential Theft" in note  # verdict labels
    assert "high" in note  # severity/confidence
    assert "Credential Compromise" in note  # category
    assert "unusual ASN" in note  # summary
    assert "completed" in note  # status
    assert "https://ui.cmdzero.io" in note  # console URL
    assert "jmaldive@warnicorn.com" in note  # observables
    assert "203.0.113.190" in note


def test_note_demotes_headings_inside_the_api_summary():
    """
    The summary is free-form markdown. Its headings must not outrank the
    note's own sections, or the War Room entry reads as nested backwards.
    """
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(dict(COMPLETED_INVESTIGATION, summary="# Top\nbody\n## Second\nmore"))
    assert "\n#### Top" in note
    assert "\n##### Second" in note
    assert "\n# Top" not in note
    # The summary supplied its own heading, so ours is not repeated.
    assert "### Findings" not in note


def test_note_labels_a_summary_that_has_no_heading_of_its_own():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(dict(COMPLETED_INVESTIGATION, summary="The account was accessed from an unusual ASN."))
    assert "### Findings" in note
    assert "unusual ASN" in note


def test_note_states_when_no_response_action_was_recorded():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(COMPLETED_INVESTIGATION)
    assert "No Command Zero response action was recorded" in note


def test_note_distinguishes_investigate_only_from_a_declined_verdict():
    """
    "submitted for analysis only" and "the verdict did not qualify" are
    materially different statements; the audit record must not blur them.
    """
    from CommandZero import compose_investigation_note

    only = compose_investigation_note(COMPLETED_INVESTIGATION, disposition="investigate-only")
    declined = compose_investigation_note(COMPLETED_INVESTIGATION, disposition="not-qualifying")

    assert "Investigate only" in only
    assert "whatever the verdict" in only
    assert "Investigate only" not in declined
    assert "did not meet the configured criteria" in declined


def test_note_disposition_is_scoped_to_what_the_connector_can_attest():
    """
    The connector knows what it requested, not what Command Zero evaluated
    internally, so every phrasing says "by this integration".
    """
    from CommandZero import NO_RESPONSE_DISPOSITIONS

    for text in NO_RESPONSE_DISPOSITIONS.values():
        assert "this integration" in text


def test_note_ignores_disposition_when_an_action_was_taken():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(
        COMPLETED_INVESTIGATION,
        {"outcome": "executed", "type": "Disable User"},
        disposition="investigate-only",
    )
    assert "Investigate only" not in note
    assert "**Executed.**" in note


def test_note_falls_back_on_an_unknown_disposition():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(COMPLETED_INVESTIGATION, disposition="something-else")
    assert "No Command Zero response action was recorded" in note


def test_note_command_passes_disposition_through():
    from CommandZero import post_investigation_note_command, Client

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = post_investigation_note_command(
        client,
        {
            "investigation_id": "inv-1",
            "response_disposition": "investigate-only",
        },
    )
    assert "Investigate only" in result.readable_output


def test_results_command_passes_disposition_through():
    from CommandZero import investigation_results_command, Client

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = investigation_results_command(
        client,
        {
            "investigation_id": "inv-1",
            "response_disposition": "investigate-only",
        },
    )
    assert "Investigate only" in result.readable_output


def test_note_reports_an_executed_response_action():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(
        COMPLETED_INVESTIGATION,
        {
            "outcome": "executed",
            "type": "Disable User",
            "id": "8f14e45f",
            "status": "success",
            "rollbackTemplateId": "r-6k81klf1p0mgf3",
        },
    )
    assert "**Executed.**" in note
    assert "Disable User" in note
    assert "Rollback available:** yes" in note


def test_note_reports_a_blocked_response_action():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(
        COMPLETED_INVESTIGATION,
        {
            "outcome": "blocked",
            "type": "Disable User",
            "reason": "Auto-execute is not enabled for this action type.",
        },
    )
    assert "Blocked by governance" in note
    assert "Auto-execute is not enabled" in note


def test_note_handles_an_investigation_with_no_verdict():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(dict(COMPLETED_INVESTIGATION, verdict=[], summary="", observables=[]))
    assert "None assigned" in note
    assert "Command Zero Investigation Complete" in note


def test_format_verdict_tolerates_a_bare_string():
    """verdict is string[] in the API, but be defensive about it."""
    from CommandZero import format_verdict

    assert format_verdict({"verdict": "Malicious"}) == "Malicious"
    assert format_verdict({"verdict": ["A", "B"]}) == "A, B"
    assert format_verdict({}) == ""


def test_post_note_command_combines_verdict_and_action():
    from CommandZero import post_investigation_note_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = post_investigation_note_command(
        client,
        {
            "investigation_id": "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35",
            "response_action_outcome": "executed",
            "response_action_type": "Disable User",
            "response_action_id": "8f14e45f",
            "response_action_status": "success",
            "rollback_template_id": "r-6k81klf1p0mgf3",
        },
    )

    assert result.mark_as_note is True
    assert result.entry_type == EntryType.NOTE
    assert "Malicious, Credential Theft" in result.readable_output
    assert "Disable User" in result.readable_output


def test_post_note_command_warns_when_action_was_blocked():
    from CommandZero import post_investigation_note_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = post_investigation_note_command(
        client,
        {
            "investigation_id": "50ce9d59-b0b1-4e35-a3d2-60f4d861fb35",
            "response_action_outcome": "blocked",
            "response_action_reason": "Policy conflict",
        },
    )
    assert result.entry_type == EntryType.WARNING


# ── List commands ───────────────────────────────────────────────
#
# Every list command shares one shape: args map to query parameters, the
# response envelope is unwrapped under a known key, and the pagination cursor
# is re-exposed. Parametrising keeps that contract in one place and means a new
# list command is covered by adding a row rather than another near-copy.

LIST_COMMANDS = [
    # command function, client method, envelope key, context key
    ("list_organizations_command", "list_organizations", "organizations", "Organization"),
    ("list_investigations_command", "list_investigations", "investigations", "Investigation"),
    ("list_remediations_command", "list_remediations", "remediations", "Remediation"),
    ("list_investigation_templates_command", "list_investigation_templates", "investigation-templates", "InvestigationTemplate"),
    ("list_catalog_types_command", "list_catalog_types", "types", "CatalogType"),
    ("list_business_context_command", "list_business_context_uploads", "uploads", "BusinessContextUpload"),
]


def run_list_command(command_name, client_method, envelope, rows, next_token="", args=None):
    import CommandZero

    client = MagicMock(spec=Client)
    getattr(client, client_method).return_value = {envelope: rows, "next": next_token, "warnings": [], "errors": []}
    result = getattr(CommandZero, command_name)(client, args or {})
    return client, result


@pytest.mark.parametrize("command_name,client_method,envelope,context_key", LIST_COMMANDS)
def test_list_command_unwraps_its_envelope(command_name, client_method, envelope, context_key):
    rows = [{"id": "row-1", "name": "First"}]
    _, result = run_list_command(command_name, client_method, envelope, rows)

    assert result.outputs_prefix == "CommandZero"
    assert result.outputs[context_key] == rows
    assert result.outputs_key_field == f"{context_key}.id"


@pytest.mark.parametrize("command_name,client_method,envelope,context_key", LIST_COMMANDS)
def test_list_command_exposes_the_pagination_cursor(command_name, client_method, envelope, context_key):
    _, result = run_list_command(command_name, client_method, envelope, [{"id": "row-1"}], next_token="cursor-2")
    assert result.outputs[f"{context_key}NextToken"] == "cursor-2"

    _, result = run_list_command(command_name, client_method, envelope, [{"id": "row-1"}])
    assert f"{context_key}NextToken" not in result.outputs


@pytest.mark.parametrize("command_name,client_method,envelope,context_key", LIST_COMMANDS)
def test_list_command_forwards_query_parameters(command_name, client_method, envelope, context_key):
    client, _ = run_list_command(
        command_name, client_method, envelope, [], args={"limit": "10", "filter": "name eq 'x'", "next_token": "cursor-1"}
    )

    params = getattr(client, client_method).call_args[0][0]
    assert params == {"limit": "10", "filter": "name eq 'x'", "next": "cursor-1"}


@pytest.mark.parametrize("command_name,client_method,envelope,context_key", LIST_COMMANDS)
def test_list_command_omits_unset_parameters(command_name, client_method, envelope, context_key):
    from CommandZero import DEFAULT_PAGE_SIZE

    client, _ = run_list_command(command_name, client_method, envelope, [])
    params = getattr(client, client_method).call_args[0][0]
    assert params == {"limit": str(DEFAULT_PAGE_SIZE)}


def test_remediation_template_list_filters_by_subject_type():
    """This endpoint takes subjectType rather than a filter expression."""
    from CommandZero import list_remediation_templates_command

    client = MagicMock(spec=Client)
    client.list_remediation_templates.return_value = {"remediation-templates": [], "next": "", "warnings": [], "errors": []}
    list_remediation_templates_command(client, {"subject_type": "CROWDSTRIKE_DEVICE_ID", "limit": "50"})
    assert client.list_remediation_templates.call_args[0][0]["subjectType"] == "CROWDSTRIKE_DEVICE_ID"


# ── Polling commands ────────────────────────────────────────────
#
# The three polling commands share one contract: reschedule while the work is
# in flight, honour the configured timing, stop on a terminal state, and
# require their identifier.

POLLING_COMMANDS = [
    # command function, client getter, id arg, in-flight object, command name
    (
        "investigation_results_command",
        "get_investigation",
        "investigation_id",
        {"id": "x", "status": "investigating", "completed": False},
        "cmdzero-investigation-results",
    ),
    (
        "remediation_results_command",
        "get_remediation",
        "remediation_id",
        {"id": "x", "status": "pending"},
        "cmdzero-remediation-results",
    ),
    (
        "business_context_results_command",
        "get_business_context_upload",
        "upload_id",
        {"id": "x", "status": "processing"},
        "cmdzero-business-context-results",
    ),
]


@pytest.mark.parametrize("command_name,getter,id_arg,in_flight,scheduled_name", POLLING_COMMANDS)
def test_polling_command_reschedules_while_in_flight(command_name, getter, id_arg, in_flight, scheduled_name):
    import CommandZero

    client = MagicMock(spec=Client)
    getattr(client, getter).return_value = in_flight

    result = getattr(CommandZero, command_name)(client, {id_arg: "x"})
    assert result.scheduled_command is not None
    assert result.scheduled_command.command == scheduled_name
    assert "Waiting on" in result.readable_output


@pytest.mark.parametrize("command_name,getter,id_arg,in_flight,scheduled_name", POLLING_COMMANDS)
def test_polling_command_honours_custom_timing(command_name, getter, id_arg, in_flight, scheduled_name):
    import CommandZero

    client = MagicMock(spec=Client)
    getattr(client, getter).return_value = in_flight

    result = getattr(CommandZero, command_name)(client, {id_arg: "x", "interval_in_seconds": "7", "timeout_in_seconds": "99"})
    assert result.scheduled_command.next_run_in_seconds == 7
    assert result.scheduled_command.timeout_in_seconds == 99


@pytest.mark.parametrize("command_name,getter,id_arg,in_flight,scheduled_name", POLLING_COMMANDS)
def test_polling_command_requires_its_identifier(command_name, getter, id_arg, in_flight, scheduled_name):
    import CommandZero

    client = MagicMock(spec=Client)
    with pytest.raises(Exception):
        getattr(CommandZero, command_name)(client, {})


# ── Remediation / investigation correlation ─────────────────────


def test_remediation_create_marks_the_investigation():
    """
    The API gives a Remediation no investigation reference and no investigation
    filter, so the justification marker is the only correlation key available.
    """
    from CommandZero import create_remediation_command, INVESTIGATION_MARKER

    client = MagicMock(spec=Client)
    client.create_remediation.return_value = {"id": "rem-1", "status": "pending"}
    client.get_remediation_template.return_value = {"undoTemplateId": ""}

    create_remediation_command(
        client,
        {
            "template_id": "r-1",
            "subject_type": "EMAIL_ADDRESS",
            "subject_value": "a@b.com",
            "justification": "Confirmed compromise",
            "investigation_id": "inv-9",
        },
    )

    body = client.create_remediation.call_args[0][0]
    assert body["justification"].startswith("Confirmed compromise")
    assert INVESTIGATION_MARKER.format("inv-9") in body["justification"]


def test_remediation_create_without_an_investigation_is_unchanged():
    from CommandZero import create_remediation_command

    client = MagicMock(spec=Client)
    client.create_remediation.return_value = {"id": "rem-1", "status": "pending"}
    client.get_remediation_template.return_value = {"undoTemplateId": ""}

    create_remediation_command(
        client,
        {
            "template_id": "r-1",
            "subject_type": "EMAIL_ADDRESS",
            "subject_value": "a@b.com",
            "justification": "Manual action",
        },
    )
    assert client.create_remediation.call_args[0][0]["justification"] == "Manual action"


def test_marker_survives_an_overlong_justification():
    """The analyst's wording is trimmed before the correlation key is lost."""
    from CommandZero import justification_with_investigation, INVESTIGATION_MARKER, MAX_JUSTIFICATION_LENGTH

    result = justification_with_investigation("x" * 2100, "inv-9")
    assert len(result) <= MAX_JUSTIFICATION_LENGTH
    assert INVESTIGATION_MARKER.format("inv-9") in result


def test_marker_is_not_applied_twice():
    from CommandZero import justification_with_investigation

    once = justification_with_investigation("Reason", "inv-9")
    twice = justification_with_investigation(once, "inv-9")
    assert once == twice


def test_remediation_list_builds_the_correlation_filter():
    from CommandZero import list_remediations_command, INVESTIGATION_MARKER

    client = MagicMock(spec=Client)
    client.list_remediations.return_value = {"remediations": [], "next": "", "warnings": [], "errors": []}

    list_remediations_command(client, {"investigation_id": "inv-9"})
    built = client.list_remediations.call_args[0][0]["filter"]
    assert "contains(justification" in built
    assert INVESTIGATION_MARKER.format("inv-9") in built


def test_remediation_list_rejects_investigation_id_with_filter():
    """Two ways to say the same thing invites a silent contradiction."""
    from CommandZero import list_remediations_command

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="not both"):
        list_remediations_command(client, {"investigation_id": "inv-9", "filter": "status eq 'success'"})


def test_remediation_list_filters_by_subject_type():
    from CommandZero import list_remediations_command

    client = MagicMock(spec=Client)
    client.list_remediations.return_value = {"remediations": [], "next": "", "warnings": [], "errors": []}

    list_remediations_command(client, {"subject_type": "EMAIL_ADDRESS"})
    assert client.list_remediations.call_args[0][0]["filter"] == "subjectType eq 'EMAIL_ADDRESS'"


def test_note_lists_related_remediations_with_their_caveat():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(
        COMPLETED_INVESTIGATION,
        related_remediations=[
            {
                "templateName": "Disable User",
                "status": "success",
                "subject": {"value": "a@b.com"},
                "createdTime": "2026-09-15T11:00:00Z",
            }
        ],
    )
    assert "Other Command Zero actions on this investigation" in note
    assert "Disable User" in note
    assert "raised directly in the Command Zero console may not appear" in note


def test_note_omits_related_remediations_when_there_are_none():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(COMPLETED_INVESTIGATION)
    assert "Other Command Zero actions" not in note


# ── JSON argument parsing ───────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected_len",
    [
        (None, 0),
        ("", 0),
        ('{"system": "Jira"}', 1),  # a bare object is accepted
        ('[{"system": "Jira"}, {}, {"system": ""}]', 1),  # empty entries dropped
        ('[{"system": "A"}, {"system": "B"}]', 2),
    ],
)
def test_third_party_actions_parsing(raw, expected_len):
    from CommandZero import third_party_actions_from_args

    assert len(third_party_actions_from_args({"third_party_actions": raw})) == expected_len


@pytest.mark.parametrize("bad", ["[{'system': 'x'}]", '"a string"', "{not json"])
def test_json_array_args_reject_unparsable_input_clearly(bad):
    """A mangled context value should say what was expected, not raise JSON noise."""
    from CommandZero import third_party_actions_from_args

    with pytest.raises(ValueError, match="must be a JSON array"):
        third_party_actions_from_args({"third_party_actions": bad})


@pytest.mark.parametrize(
    "text,expected",
    [
        ("###### deep", "###### deep"),
        ("# a\n## b", "#### a\n##### b"),
        ("no headings here", "no headings here"),
        ("see issue #42 here", "see issue #42 here"),
    ],
)
def test_demote_markdown_headings(text, expected):
    from CommandZero import demote_markdown_headings

    assert demote_markdown_headings(text) == expected


# ── UC3 / UC6: business context ─────────────────────────────────

GOOD_RECORDS = '[{"email":"user@company.com","department":"Engineering"}]'
GOOD_SCHEMA = '[{"path":"email","type":"EMAIL_ADDRESS"},' '{"path":"department","type":"TEXT"}]'

READY_UPLOAD = {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "HR User Directory",
    "status": "ready",
    "recordCount": 1547,
    "subjectTypes": ["EMAIL_ADDRESS"],
    "error": "",
}


def test_business_context_upload_sends_records_and_schema():
    from CommandZero import upload_business_context_command, Client

    client = MagicMock(spec=Client)
    client.create_business_context_upload.return_value = dict(READY_UPLOAD, status="processing")

    result = upload_business_context_command(
        client,
        {
            "name": "HR User Directory",
            "records": GOOD_RECORDS,
            "schema": GOOD_SCHEMA,
            "description": "Workday export",
        },
    )

    body = client.create_business_context_upload.call_args[0][0]
    assert body["name"] == "HR User Directory"
    assert body["description"] == "Workday export"
    assert len(body["records"]) == 1
    assert len(body["schema"]) == 2
    assert result.outputs["status"] == "processing"


def test_business_context_upload_requires_a_name():
    from CommandZero import upload_business_context_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(Exception):
        upload_business_context_command(client, {"records": GOOD_RECORDS, "schema": GOOD_SCHEMA})


def test_business_context_rejects_a_single_annotation_schema():
    """The API requires at least two annotations; say so before the round trip."""
    from CommandZero import upload_business_context_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="at least 2"):
        upload_business_context_command(
            client,
            {
                "name": "HR",
                "records": GOOD_RECORDS,
                "schema": '[{"path":"email","type":"EMAIL_ADDRESS"}]',
            },
        )


def test_business_context_rejects_records_without_schema():
    from CommandZero import upload_business_context_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="together"):
        upload_business_context_command(client, {"name": "HR", "records": GOOD_RECORDS})


def test_business_context_replace_allows_metadata_only_update():
    """The API permits renaming without resubmitting every record."""
    from CommandZero import replace_business_context_command, Client

    client = MagicMock(spec=Client)
    client.replace_business_context_upload.return_value = READY_UPLOAD

    replace_business_context_command(client, {"upload_id": "up-1", "description": "refreshed"})

    upload_id, body = client.replace_business_context_upload.call_args[0]
    assert upload_id == "up-1"
    assert body == {"description": "refreshed"}
    assert "records" not in body


def test_business_context_replace_sends_records_and_schema_together():
    from CommandZero import replace_business_context_command, Client

    client = MagicMock(spec=Client)
    client.replace_business_context_upload.return_value = READY_UPLOAD

    replace_business_context_command(client, {"upload_id": "up-1", "records": GOOD_RECORDS, "schema": GOOD_SCHEMA})

    _, body = client.replace_business_context_upload.call_args[0]
    assert len(body["records"]) == 1
    assert len(body["schema"]) == 2


def test_business_context_replace_rejects_an_empty_request():
    from CommandZero import replace_business_context_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="Provide records and schema"):
        replace_business_context_command(client, {"upload_id": "up-1"})


def test_business_context_replace_rejects_schema_without_records():
    from CommandZero import replace_business_context_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="together"):
        replace_business_context_command(client, {"upload_id": "up-1", "schema": GOOD_SCHEMA})


def test_business_context_delete_reports_the_consequence():
    from CommandZero import delete_business_context_command, Client

    client = MagicMock(spec=Client)

    result = delete_business_context_command(client, {"upload_id": "up-1"})
    client.delete_business_context_upload.assert_called_once_with("up-1")
    assert result.outputs["deleted"] is True
    assert "already ran keep the context" in result.readable_output


def test_business_context_results_stops_when_ready():
    from CommandZero import business_context_results_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_business_context_upload.return_value = READY_UPLOAD

    result = business_context_results_command(client, {"upload_id": "up-1"})
    assert result.scheduled_command is None
    assert result.entry_type == EntryType.NOTE
    assert "Ready" in result.readable_output


def test_business_context_results_warns_on_failure():
    from CommandZero import business_context_results_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_business_context_upload.return_value = dict(READY_UPLOAD, status="failed", error="Malformed record at index 12")

    result = business_context_results_command(client, {"upload_id": "up-1"})
    assert result.entry_type == EntryType.WARNING
    assert "Failed" in result.readable_output


def test_business_context_json_errors_show_a_worked_example():
    from CommandZero import upload_business_context_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="must be a JSON array"):
        upload_business_context_command(
            client,
            {
                "name": "HR",
                "records": "{'email': 'not json'}",
                "schema": GOOD_SCHEMA,
            },
        )


# ── Remediation completion polling ──────────────────────────────


def test_remediation_results_stops_on_success():
    from CommandZero import remediation_results_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_remediation.return_value = {
        "id": "rem-1",
        "status": "success",
        "templateName": "Disable User",
        "error": "",
        "completedTime": "2026-09-15T12:01:00Z",
    }

    result = remediation_results_command(client, {"remediation_id": "rem-1"})
    assert result.scheduled_command is None
    assert result.entry_type == EntryType.NOTE
    assert "Completed" in result.readable_output
    assert result.outputs["status"] == "success"


def test_remediation_results_warns_on_failure():
    from CommandZero import remediation_results_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_remediation.return_value = {
        "id": "rem-1",
        "status": "failed",
        "templateName": "Disable User",
        "error": "Subject is protected by policy",
    }

    result = remediation_results_command(client, {"remediation_id": "rem-1"})
    assert result.scheduled_command is None
    assert result.entry_type == EntryType.WARNING
    assert "Failed" in result.readable_output


def test_remediation_results_treats_unknown_status_as_terminal():
    """
    status is an open enumeration. An unrecognised value must end the poll
    rather than spin until the timeout.
    """
    from CommandZero import remediation_results_command, Client

    client = MagicMock(spec=Client)
    client.get_remediation.return_value = {"id": "rem-1", "status": "some-future-status"}

    result = remediation_results_command(client, {"remediation_id": "rem-1"})
    assert result.scheduled_command is None
    assert result.outputs["status"] == "some-future-status"


def test_remediation_results_treats_unchanged_as_success():
    """`unchanged` means the subject was already in the desired state."""
    from CommandZero import remediation_results_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_remediation.return_value = {"id": "rem-1", "status": "unchanged"}

    result = remediation_results_command(client, {"remediation_id": "rem-1"})
    assert result.entry_type == EntryType.NOTE


# ── UC2: coordinated native + third-party response ──────────────

THIRD_PARTY = json.dumps(
    [
        {
            "system": "ServiceNow",
            "action": "Incident raised",
            "target": "jmaldive@warnicorn.com",
            "status": "completed",
            "reference": "INC0012345",
        },
        {
            "system": "CrowdStrike",
            "action": "Host contained",
            "target": "LAPTOP-4417",
            "status": "completed",
            "reference": "job-889",
        },
    ]
)


def test_note_reports_native_and_third_party_actions_together():
    """OC2: both action sets tracked together, in one place the analyst reads."""
    from CommandZero import compose_investigation_note, third_party_actions_from_args

    note = compose_investigation_note(
        COMPLETED_INVESTIGATION,
        {"outcome": "executed", "type": "Disable User", "status": "success"},
        third_party_actions_from_args({"third_party_actions": THIRD_PARTY}),
    )
    assert "**Executed.**" in note  # native action
    assert "Disable User" in note
    assert "ServiceNow" in note  # third-party actions
    assert "INC0012345" in note
    assert "CrowdStrike" in note
    assert "LAPTOP-4417" in note
    assert "Executed by this SOAR, not by Command Zero" in note


def test_note_omits_the_third_party_section_when_there_are_none():
    from CommandZero import compose_investigation_note

    note = compose_investigation_note(COMPLETED_INVESTIGATION)
    assert "Third-party response actions" not in note


def test_third_party_actions_reject_unparsable_input_clearly():
    """A mangled context value should say what was expected, not raise JSON noise."""
    from CommandZero import third_party_actions_from_args

    with pytest.raises(ValueError, match="must be a JSON array"):
        third_party_actions_from_args(
            {
                "third_party_actions": "[{'system': 'ServiceNow'}]"  # Python repr
            }
        )
    with pytest.raises(ValueError, match="must be a JSON array"):
        third_party_actions_from_args({"third_party_actions": '"a string"'})


def test_note_warns_when_a_third_party_action_failed():
    """A stack action that did not land must be visible, not buried."""
    from CommandZero import post_investigation_note_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = post_investigation_note_command(
        client,
        {
            "investigation_id": "inv-1",
            "third_party_actions": json.dumps([{"system": "CrowdStrike", "action": "Host contained", "status": "failed"}]),
        },
    )
    assert result.entry_type == EntryType.WARNING
    assert "CrowdStrike" in result.readable_output


def test_note_stays_a_plain_note_when_stack_actions_succeeded():
    from CommandZero import post_investigation_note_command, Client, EntryType

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = post_investigation_note_command(client, {"investigation_id": "inv-1", "third_party_actions": THIRD_PARTY})
    assert result.entry_type == EntryType.NOTE


def test_results_command_also_carries_third_party_actions():
    from CommandZero import investigation_results_command, Client

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = investigation_results_command(client, {"investigation_id": "inv-1", "third_party_actions": THIRD_PARTY})
    assert "ServiceNow" in result.readable_output


def test_response_action_from_args_returns_none_when_nothing_supplied():
    from CommandZero import response_action_from_args

    assert response_action_from_args({"investigation_id": "inv-1"}) is None


def test_create_remediation_surfaces_rollback_handle():
    """undoTemplateId comes from the template, not the Remediation response."""
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.return_value = {
        "id": "8f14e45f-ceea-467f-a123-f6b2c3d4e5f6",
        "status": "pending",
        "templateId": "r-39a26e0p32micg",
        "templateName": "Disable User",
        "subject": {"type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME", "value": "test@test.com"},
        "justification": "Test",
        "error": "",
    }
    client.get_remediation_template.return_value = {"id": "r-39a26e0p32micg", "undoTemplateId": "r-6k81klf1p0mgf3"}

    result = create_remediation_command(
        client,
        {
            "template_id": "r-39a26e0p32micg",
            "subject_type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME",
            "subject_value": "test@test.com",
            "justification": "Test",
        },
    )

    assert result.outputs["governanceOutcome"] == "executed"
    assert result.outputs["rollbackAvailable"] is True
    assert result.outputs["undoTemplateId"] == "r-6k81klf1p0mgf3"


def test_create_remediation_reports_no_rollback_when_not_reversible():
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.return_value = {
        "id": "8f14e45f",
        "status": "pending",
        "templateId": "r-1",
        "templateName": "Notify",
        "subject": {},
        "justification": "Test",
        "error": "",
    }
    client.get_remediation_template.return_value = {"id": "r-1", "undoTemplateId": ""}

    result = create_remediation_command(
        client, {"template_id": "r-1", "subject_type": "EMAIL_ADDRESS", "subject_value": "test@test.com", "justification": "Test"}
    )
    assert result.outputs["rollbackAvailable"] is False
    assert result.outputs["undoTemplateId"] == ""


def test_create_remediation_survives_template_lookup_failure():
    """A failed rollback lookup must not mask a remediation that executed."""
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.return_value = {
        "id": "8f14e45f",
        "status": "pending",
        "templateId": "r-1",
        "templateName": "Disable User",
        "subject": {},
        "justification": "Test",
        "error": "",
    }
    client.get_remediation_template.side_effect = Exception("boom")

    result = create_remediation_command(
        client, {"template_id": "r-1", "subject_type": "EMAIL_ADDRESS", "subject_value": "test@test.com", "justification": "Test"}
    )
    assert result.outputs["id"] == "8f14e45f"
    assert result.outputs["governanceOutcome"] == "executed"
    assert result.outputs["rollbackAvailable"] is False


def test_create_remediation_403_reports_governance_block():
    """403 is a governance decision, not a connector fault — report, don't raise."""
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.side_effect = DemistoException(
        "Forbidden",
        res=FakeResponse(
            403,
            {
                "message": "Automated response actions are not enabled " "for this action type.",
                "status": 403,
                "type": "Forbidden",
                "traceId": "abc123def456",
            },
        ),
    )

    result = create_remediation_command(
        client,
        {
            "template_id": "r-39a26e0p32micg",
            "subject_type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME",
            "subject_value": "test@test.com",
            "justification": "Test",
        },
    )

    assert result.outputs["governanceOutcome"] == "blocked"
    assert result.outputs["governanceHttpStatus"] == 403
    assert "not enabled" in result.outputs["governanceReason"]
    assert result.outputs["traceId"] == "abc123def456"
    assert result.outputs["templateId"] == "r-39a26e0p32micg"


def test_create_remediation_409_reports_conflict():
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.side_effect = DemistoException(
        "Conflict",
        res=FakeResponse(
            409,
            {
                "message": "A conflicting remediation is already in progress.",
                "status": 409,
                "type": "Conflict",
                "traceId": "zzz999",
            },
        ),
    )

    result = create_remediation_command(
        client, {"template_id": "r-1", "subject_type": "EMAIL_ADDRESS", "subject_value": "test@test.com", "justification": "Test"}
    )
    assert result.outputs["governanceOutcome"] == "conflict"
    assert result.outputs["governanceHttpStatus"] == 409
    assert result.outputs["traceId"] == "zzz999"


def test_create_remediation_other_errors_still_raise():
    """Only 403/409 are governance outcomes. A 500 is a real failure."""
    from CommandZero import create_remediation_command, Client

    client = MagicMock(spec=Client)
    client.create_remediation.side_effect = DemistoException(
        "Server error", res=FakeResponse(500, {"message": "boom", "status": 500})
    )

    with pytest.raises(DemistoException):
        create_remediation_command(
            client,
            {"template_id": "r-1", "subject_type": "EMAIL_ADDRESS", "subject_value": "test@test.com", "justification": "Test"},
        )


def test_error_detail_falls_back_to_trace_header():
    """traceId is on the header even when the body is not JSON."""
    from CommandZero import error_detail

    status, message, trace = error_detail(
        DemistoException("Bad Gateway", res=FakeResponse(502, None, {"X-Cmdzero-Traceid": "hdr-trace"}))
    )
    assert status == 502
    assert trace == "hdr-trace"
    assert "Bad Gateway" in message


def test_error_detail_handles_non_http_exception():
    from CommandZero import error_detail

    status, message, trace = error_detail(DemistoException("connection reset"))
    assert status is None
    assert trace == ""
    assert "connection reset" in message


FAKE_INVESTIGATION_RESPONSE = {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "title": "Malicious file detected in email",
    "status": "open",
    "severity": "low",
    "category": "Malware",
    "completed": False,
    "verdict": [],
    "consoleUrl": "https://ui.cmdzero.io/#/inv-detail?id=f47ac10b",
    "organizationId": "51c264ff-5a98-4f15-b7e1-07158d35151c",
    "createdTime": "2026-06-15T18:00:00Z",
    "updatedTime": "2026-06-15T18:00:00Z",
    "type": "alert",
    "tags": [],
    "assignees": [],
    "templateId": "",
}


def test_create_investigation_with_inline_annotations():
    """
    Form 2 — alert_type + alert_data + annotations. alert_type is required
    here: the annotations say where the values are, not what kind of alert it
    is.
    """
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = FAKE_INVESTIGATION_RESPONSE

    result = create_investigation_command(
        client,
        {
            "alert_data": '{"alert_title": "Test", "seen": "2026-06-15T00:00:00Z"}',
            "alert_schema": '[{"path": "alert_title", "type": "ALERT_TITLE"}, ' '{"path": "seen", "type": "ALERT_TIME"}]',
            "alert_type": "EmailMalwareDetected",
            "title": "Test Investigation",
        },
    )

    assert result.outputs["id"] == "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    body = client.create_investigation.call_args[0][0]
    assert body["alertType"] == "EmailMalwareDetected"
    assert isinstance(body["alertSchema"], list)


def test_annotations_without_an_alert_type_are_rejected_locally():
    """
    The API requires alertType alongside an annotation array. Catching it here
    turns a 422 on a live tenant into an explanation at authoring time.
    """
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="alert_type is required"):
        create_investigation_command(
            client,
            {
                "alert_data": '{"alert_title": "Test"}',
                "alert_schema": '[{"path": "alert_title", "type": "ALERT_TITLE"}]',
            },
        )


def test_catalog_type_with_an_alert_type_is_rejected_locally():
    """A catalog entry already defines the alert type; setting both is invalid."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="must not be set"):
        create_investigation_command(
            client,
            {
                "alert_data": '{"playbook_alert_id": "abc123"}',
                "alert_schema": "RECORDED_FUTURE_PLAYBOOK_ALERT",
                "alert_type": "EmailMalwareDetected",
            },
        )


def test_create_investigation_from_alert_type_alone():
    """Form 1 — no schema; Command Zero resolves it from the alert type."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = FAKE_INVESTIGATION_RESPONSE

    create_investigation_command(
        client,
        {
            "alert_data": '{"sender": {"email": "a@b.com"}}',
            "alert_type": "EmailMalwareDetected",
            "title": "Malicious file detected in email",
            "description": "Inbound email carried a known-malicious attachment.",
        },
    )

    body = client.create_investigation.call_args[0][0]
    assert body["alertType"] == "EmailMalwareDetected"
    assert "alertSchema" not in body
    assert body["description"].startswith("Inbound email")


@pytest.mark.parametrize("missing", ["title", "description"])
def test_alert_type_only_form_requires_title_and_description(missing):
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    args = {
        "alert_data": '{"sender": {"email": "a@b.com"}}',
        "alert_type": "EmailMalwareDetected",
        "title": "A title",
        "description": "A description",
    }
    del args[missing]
    with pytest.raises(ValueError, match="both required"):
        create_investigation_command(client, args)


def test_create_investigation_passes_category_and_tags():
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = FAKE_INVESTIGATION_RESPONSE

    create_investigation_command(
        client,
        {
            "alert_data": '{"playbook_alert_id": "abc123"}',
            "alert_schema": "RECORDED_FUTURE_PLAYBOOK_ALERT",
            "category": "Credential Compromise",
            "tags": '["urgent","vip-user"]',
        },
    )
    body = client.create_investigation.call_args[0][0]
    assert body["category"] == "Credential Compromise"
    assert body["tags"] == ["urgent", "vip-user"]


def test_nosettle_is_sent_as_a_query_parameter():
    """Lets a live-tenant exercise avoid report generation and settlement."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = FAKE_INVESTIGATION_RESPONSE

    create_investigation_command(
        client,
        {
            "alert_data": '{"playbook_alert_id": "abc123"}',
            "alert_schema": "RECORDED_FUTURE_PLAYBOOK_ALERT",
            "nosettle": "true",
        },
    )
    assert client.create_investigation.call_args[0][1] == {"nosettle": "true"}

    create_investigation_command(
        client,
        {
            "alert_data": '{"playbook_alert_id": "abc123"}',
            "alert_schema": "RECORDED_FUTURE_PLAYBOOK_ALERT",
        },
    )
    assert client.create_investigation.call_args[0][1] is None


def test_create_investigation_from_catalog_type_string():
    """Form 2 — alert_data + alert_schema as a catalog type string."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = FAKE_INVESTIGATION_RESPONSE

    result = create_investigation_command(
        client,
        {"alert_data": '{"playbook_alert_id": "abc123", "priority": "high"}', "alert_schema": "RECORDED_FUTURE_PLAYBOOK_ALERT"},
    )

    assert result.outputs["id"] == "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    body = client.create_investigation.call_args[0][0]
    assert body["alertSchema"] == "RECORDED_FUTURE_PLAYBOOK_ALERT"
    assert isinstance(body["alertSchema"], str)


def test_create_investigation_from_template():
    """Form 3 — template_id + leads."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = FAKE_INVESTIGATION_RESPONSE

    result = create_investigation_command(
        client,
        {
            "template_id": "employee-separation-review",
            "leads": '[{"type": "EMAIL_ADDRESS", "value": "user@company.com"}]',
            "title": "Pre-separation review",
        },
    )

    assert result.outputs["id"] == "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    body = client.create_investigation.call_args[0][0]
    assert body["templateId"] == "employee-separation-review"
    assert isinstance(body["leads"], list)


def test_alert_data_needs_a_type_or_a_schema():
    """alert_data alone identifies neither the alert kind nor its shape."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(ValueError, match="alert_type, alert_schema, or both"):
        create_investigation_command(client, {"alert_data": '{"alert_title": "Test"}'})


def test_create_investigation_surfaces_created_action():
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = dict(FAKE_INVESTIGATION_RESPONSE, action="created")

    result = create_investigation_command(
        client, {"alert_data": '{"playbook_alert_id": "abc123"}', "alert_schema": "RECORDED_FUTURE_PLAYBOOK_ALERT"}
    )
    assert result.outputs["action"] == "created"
    assert result.outputs["id"] == "f47ac10b-58cc-4372-a567-0e02b2c3d479"


def test_create_investigation_surfaces_merged_action():
    """A merged alert still has to hand an investigation ID back to the case."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    client.create_investigation.return_value = dict(FAKE_INVESTIGATION_RESPONSE, action="merged")

    result = create_investigation_command(
        client, {"alert_data": '{"playbook_alert_id": "abc123"}', "alert_schema": "RECORDED_FUTURE_PLAYBOOK_ALERT"}
    )
    assert result.outputs["action"] == "merged"
    assert result.outputs["id"] == "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    assert "Merged" in result.readable_output


def test_client_retries_on_rate_limit_and_transient_errors():
    """429 with Retry-After must be retried, not surfaced as a failure."""
    from CommandZero import Client, RETRY_COUNT, RETRY_STATUS_CODES

    client = Client("c0.key", "org-1", "https://example.invalid", True, False)
    client._http_request = MagicMock(return_value={"status": "ok"})

    client.health_check()

    kwargs = client._http_request.call_args[1]
    assert kwargs["retries"] == RETRY_COUNT
    assert 429 in kwargs["status_list_to_retry"]
    assert kwargs["status_list_to_retry"] == RETRY_STATUS_CODES
    assert kwargs["headers"]["Authorization"] == "Bearer c0.key"


def test_create_investigation_requires_alert_data_or_template():
    """Neither alert_data nor template_id should raise."""
    from CommandZero import create_investigation_command, Client

    client = MagicMock(spec=Client)
    with pytest.raises(Exception, match="Either template_id or alert_data"):
        create_investigation_command(client, {"title": "Test"})


# ── Contract checks ─────────────────────────────────────────────
#
# Static consistency between the YAML, the Python and the playbooks. These are
# the mistakes that are invisible in unit tests but cost a round trip to a live
# tenant: a command added to the YAML but never dispatched, an argument
# declared but never read, a playbook calling an argument that does not exist.

import ast  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
PACK = HERE.parent.parent


def load_yaml(path):
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(path.read_text())


def integration_spec():
    return load_yaml(HERE / "CommandZero.yml")


def integration_source():
    return (HERE / "CommandZero.py").read_text()


def declared_commands():
    return {c["name"] for c in integration_spec()["script"]["commands"]}


def dispatched_commands():
    return set(re.findall(r'command == "([^"]+)"', integration_source()))


def _direct_arg_reads(func_node):
    """args.get("literal") written directly inside one function."""
    return {
        node.args[0].value
        for node in ast.walk(func_node)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "args"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }


def _helpers_given_args(func_node):
    """Module functions this one hands `args` to, e.g. paged_list_params(args)."""
    return {
        node.func.id
        for node in ast.walk(func_node)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and any(isinstance(a, ast.Name) and a.id == "args" for a in node.args)
    }


def args_read_by_function():
    """
    Arguments each function reads, following `args` into helper functions so a
    command that delegates its parsing is still credited with those reads.
    """
    tree = ast.parse(integration_source())
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    direct = {name: _direct_arg_reads(node) for name, node in functions.items()}
    helpers = {name: _helpers_given_args(node) & set(functions) for name, node in functions.items()}

    def resolve(name, seen):
        if name in seen:
            return set()
        seen.add(name)
        return direct.get(name, set()).union(*(resolve(h, seen) for h in helpers.get(name, set())) or [set()])

    return {name: resolve(name, set()) for name in functions}


def command_handlers():
    """command name -> handler function, read from main()'s dispatch."""
    return dict(re.findall(r'command == "([^"]+)":\n\s+return_results\(\s*\n?\s*([a-z_]+)\(', integration_source()))


def args_read_in_code():
    """Every args.get("literal") anywhere in the module."""
    return set().union(*args_read_by_function().values())


def test_every_declared_command_is_dispatched():
    """A command in the YAML that main() does not handle fails only at runtime."""
    assert declared_commands() - dispatched_commands() == set()


def test_every_dispatched_command_is_declared():
    assert dispatched_commands() - declared_commands() - {"test-module"} == set()


def test_no_command_reads_an_undeclared_argument():
    """Catches a typo in args.get(), which silently reads None."""
    spec = integration_spec()
    declared = {a["name"] for c in spec["script"]["commands"] for a in c.get("arguments", [])}
    assert args_read_in_code() - declared == set()


def test_no_declared_argument_is_ignored():
    """
    Checked per command, not across the module: the bug that actually bit was
    cmdzero-organization-list declaring a `limit` it never forwarded, while
    other commands read `limit` perfectly well. A module-wide check would have
    seen the name in use somewhere and passed.
    """
    spec = integration_spec()
    handlers = command_handlers()
    reads = args_read_by_function()

    ignored = {}
    for command in spec["script"]["commands"]:
        handler = handlers.get(command["name"])
        assert handler, f"no handler resolved for {command['name']}"
        declared = {a["name"] for a in command.get("arguments", [])}
        missing = declared - reads.get(handler, set())
        if missing:
            ignored[command["name"]] = sorted(missing)

    assert ignored == {}


def test_every_polling_command_declares_itself_as_polling():
    """`polling: true` is what makes XSOAR honour a ScheduledCommand."""
    spec = integration_spec()
    scheduled = set(re.findall(r'command="(cmdzero-[a-z-]+)",\n\s+next_run_in_seconds', integration_source()))
    assert scheduled, "expected to find ScheduledCommand rescheduling targets"
    polling = {c["name"] for c in spec["script"]["commands"] if c.get("polling")}
    assert scheduled <= polling


def test_playbooks_only_call_real_commands_with_real_arguments():
    """
    A playbook referencing a command or argument that does not exist fails at
    run time on a live tenant, which is an expensive way to find a typo.
    """
    spec = integration_spec()
    command_args = {c["name"]: {a["name"] for a in c.get("arguments", [])} for c in spec["script"]["commands"]}

    problems = []
    playbooks = sorted((PACK / "Playbooks").glob("*.yml")) + sorted((PACK / "TestPlaybooks").glob("*.yml"))
    assert playbooks, "no playbooks found to check"

    for path in playbooks:
        pb = load_yaml(path)
        for task_id, task in (pb.get("tasks") or {}).items():
            script = (task.get("task") or {}).get("script") or ""
            if "|||" not in script:
                continue
            _, _, command = script.partition("|||")
            if command not in command_args:
                problems.append(f"{pb['name']} task {task_id}: unknown command {command}")
                continue
            for arg in task.get("scriptarguments") or {}:
                if arg not in command_args[command]:
                    problems.append(f"{pb['name']} task {task_id}: {command} has no argument {arg}")
    assert problems == []


def test_playbook_task_graphs_are_connected():
    """Every branch target exists, and no task is stranded."""
    problems = []
    for path in sorted((PACK / "Playbooks").glob("*.yml")) + sorted((PACK / "TestPlaybooks").glob("*.yml")):
        pb = load_yaml(path)
        tasks = pb.get("tasks") or {}
        ids = set(tasks)
        reachable = set()

        for task_id, task in tasks.items():
            for targets in (task.get("nexttasks") or {}).values():
                for target in targets or []:
                    reachable.add(target)
                    if target not in ids:
                        problems.append(f"{pb['name']} task {task_id} -> missing {target}")
            if task.get("type") == "condition":
                labels = {c["label"] for c in (task.get("conditions") or [])}
                branches = set(task.get("nexttasks", {})) - {"#default#", "#none#"}
                if labels != branches:
                    problems.append(f"{pb['name']} task {task_id}: labels {labels} != branches {branches}")

        stranded = ids - reachable - {pb.get("starttaskid")}
        if stranded:
            problems.append(f"{pb['name']}: unreachable tasks {sorted(stranded)}")
    assert problems == []


# ── Credential handling ─────────────────────────────────────────

SENTINEL_KEY = "c0.SENTINEL-DO-NOT-LEAK-6f1a0c80"


def real_client_with_stubbed_transport(response):
    """A genuine Client, so the key travels the real code path."""
    from CommandZero import Client

    client = Client(SENTINEL_KEY, ORG_ID, "https://example.invalid", True, False)
    client._http_request = MagicMock(return_value=response)
    return client


@pytest.mark.parametrize(
    "command_name,response,args",
    [
        ("list_organizations_command", {"organizations": [{"id": ORG_ID, "name": "warniCo"}], "next": ""}, {}),
        ("list_investigations_command", {"investigations": [{"id": "inv-1"}], "next": ""}, {}),
        ("get_investigation_command", COMPLETED_INVESTIGATION, {"investigation_id": "inv-1"}),
    ],
)
def test_api_key_never_reaches_command_output(command_name, response, args):
    """
    The key must not surface in war room output or context. Driven through a
    real Client so the header path is genuinely exercised.
    """
    import CommandZero

    client = real_client_with_stubbed_transport(response)
    result = getattr(CommandZero, command_name)(client, args)

    rendered = " ".join(str(x) for x in (result.readable_output, result.outputs, result.raw_response))
    assert SENTINEL_KEY not in rendered
    assert "SENTINEL" not in rendered

    # ...but it is on the wire, otherwise the test proves nothing.
    sent = client._http_request.call_args[1]["headers"]["Authorization"]
    assert SENTINEL_KEY in sent


def test_api_key_is_never_logged():
    """demisto.debug output must not carry the key either."""
    import CommandZero

    logged = []
    original = CommandZero.demisto.debug
    CommandZero.demisto.debug = logged.append
    try:
        # A real Client, already scoped to ORG_ID, so run_test_module takes the
        # genuine path rather than a mock's.
        client = real_client_with_stubbed_transport({"status": "ok"})
        client.list_organizations = MagicMock(return_value={"organizations": [{"id": ORG_ID}], "next": ""})
        CommandZero.run_test_module(client)
    finally:
        CommandZero.demisto.debug = original
    assert logged, "expected the schema version to be logged"
    assert not any(SENTINEL_KEY in str(line) for line in logged)


# ── Gaps named in the acceptance criteria matrix ────────────────


def test_note_still_posted_when_a_remediation_never_completes():
    """
    AC 9.1: a response action that does not finish must not cost the analyst
    the verdict. The note reports the last known status instead.
    """
    from CommandZero import post_investigation_note_command, Client

    client = MagicMock(spec=Client)
    client.get_investigation.return_value = COMPLETED_INVESTIGATION

    result = post_investigation_note_command(
        client,
        {
            "investigation_id": "inv-1",
            "response_action_outcome": "executed",
            "response_action_type": "Disable User",
            "response_action_status": "pending",
        },
    )
    assert "Malicious, Credential Theft" in result.readable_output
    assert "pending" in result.readable_output


def test_sync_reports_record_count_and_subject_types():
    """AC 10.6: a sync has to be auditable, so the counts must reach context."""
    from CommandZero import business_context_results_command, Client

    client = MagicMock(spec=Client)
    client.get_business_context_upload.return_value = READY_UPLOAD

    result = business_context_results_command(client, {"upload_id": "up-1"})
    assert result.outputs["recordCount"] == 1547
    assert result.outputs["subjectTypes"] == ["EMAIL_ADDRESS"]
