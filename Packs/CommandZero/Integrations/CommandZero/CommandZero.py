import json
import re
import demistomock as demisto
from CommonServerPython import *

""" CONSTANTS """
CMDZERO_BASE_URL = "https://api.cmdzero.io/public/v1"

# The published API schema this integration is built against. The API exposes no
# version signal at runtime, so a mismatch cannot yet be detected automatically;
# it is surfaced here, in the instance description, and in the documentation.
CMDZERO_API_SCHEMA_VERSION = "2026-03-12"

DEFAULT_PAGE_SIZE = 50

# Cap how many organizations are named when the configured one is not among
# them, so a key with broad grants does not produce an unreadable error.
MAX_ORGS_IN_ERROR = 5

# Paging for the connection test's organization lookup. The API caps limit at
# 10000, so one page covers every realistic case; the cursor is still followed,
# and the page cap is a safety net rather than a limit we expect to reach.
# Note the filter vocabulary does not include `id`, so the configured
# organization cannot be looked up directly — it has to be found in the list.
ORG_PAGE_SIZE = 10000
MAX_ORG_PAGES = 10

# The API documents a Retry-After header on 429. urllib3 honours it on 429 and
# 503; the backoff factor covers the transient 5xx cases that do not carry one.
RETRY_COUNT = 3
RETRY_BACKOFF_FACTOR = 1
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]

# Governance outcomes carried alongside a remediation. Response action
# governance is enforced server-side; the connector reports what happened.
GOVERNANCE_EXECUTED = "executed"
GOVERNANCE_BLOCKED = "blocked"
GOVERNANCE_CONFLICT = "conflict"

# Third-party action statuses that should make the note stand out. The values
# are the playbook author's own, so this matches loosely rather than enforcing
# a vocabulary we do not own.
THIRD_PARTY_FAILURE_STATUSES = (
    "failed",
    "error",
    "blocked",
    "pending review",
    "not found",
)

# Why no response action was taken. Deliberately worded as statements about
# what this integration did, since that is all the connector can attest to.
NO_RESPONSE_DISPOSITIONS = {
    "investigate-only": (
        "**Investigate only.** This alert was submitted for analysis. No "
        "Command Zero response action was requested by this integration, "
        "whatever the verdict."
    ),
    "not-qualifying": (
        "**No action taken.** The verdict did not meet the configured criteria "
        "for a response action, so none was requested by this integration."
    ),
    "not-configured": (
        "**No action taken.** The verdict qualified for a response action, but "
        "no Command Zero response action is configured for this playbook, so "
        "none was requested by this integration."
    ),
    None: ("No Command Zero response action was recorded for this investigation. " "No action was executed by this integration."),
}

# Polling. `completed` on the Investigation is the authoritative "verdict is
# ready" signal; `failed` is terminal but unsuccessful.
DEFAULT_POLL_INTERVAL = 60
DEFAULT_POLL_TIMEOUT = 3600
TERMINAL_FAILURE_STATUSES = ("failed",)

# Remediations are queued and usually finish inside a minute, so they are
# polled faster and given up on sooner than investigations. `status` is an open
# enumeration, so anything that is not `pending` is treated as terminal — an
# unrecognised value must end the poll rather than run it to timeout.
DEFAULT_REMEDIATION_POLL_INTERVAL = 15
DEFAULT_REMEDIATION_POLL_TIMEOUT = 600
REMEDIATION_PENDING_STATUS = "pending"
REMEDIATION_FAILURE_STATUSES = ("failed", "not_found", "interrupted")

# Business context uploads process asynchronously and large ones can take
# several minutes, so they are polled more patiently than remediations.
DEFAULT_CONTEXT_POLL_INTERVAL = 30
DEFAULT_CONTEXT_POLL_TIMEOUT = 1800
CONTEXT_PROCESSING_STATUS = "processing"
CONTEXT_FAILURE_STATUSES = ("failed",)

# The API requires at least two schema annotations on a business context
# upload, one of which must map to a subject type.
MIN_CONTEXT_SCHEMA_ANNOTATIONS = 2

# A Remediation carries no reference to the investigation that motivated it,
# and `listRemediations` offers no investigation filter — see the gap noted in
# the pack assessment. `justification` is free text that we author and that the
# API does allow filtering on, so a marker embedded there is the only
# correlation key available. It finds remediations created through this
# convention; anything raised directly in the console will not carry it.
INVESTIGATION_MARKER = "[cmd0-investigation:{}]"
MAX_JUSTIFICATION_LENGTH = 2000


class Client(BaseClient):
    def __init__(self, api_key, organization_id, base_url, verify, proxy):
        super().__init__(base_url=base_url, verify=verify, proxy=proxy)
        self._organization_id = organization_id
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @property
    def organization_id(self):
        return self._organization_id

    def _request(self, method, url_suffix, **kwargs):
        return self._http_request(
            method=method,
            url_suffix=url_suffix,
            headers=self._headers,
            retries=RETRY_COUNT,
            status_list_to_retry=RETRY_STATUS_CODES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            **kwargs,
        )

    def health_check(self):
        return self._request("GET", "/ok")

    def list_organizations(self, params=None):
        return self._request("GET", "/organizations", params=params)

    def list_investigations(self, params=None):
        return self._request("GET", f"/organizations/{self._organization_id}/investigations", params=params)

    def get_investigation(self, investigation_id):
        return self._request("GET", f"/organizations/{self._organization_id}/investigations/{investigation_id}")

    def list_remediation_templates(self, params=None):
        return self._request("GET", f"/organizations/{self._organization_id}/remediation-templates", params=params)

    def get_remediation_template(self, template_id):
        return self._request("GET", f"/organizations/{self._organization_id}/remediation-templates/{template_id}")

    def get_remediation(self, remediation_id):
        return self._request("GET", f"/organizations/{self._organization_id}/remediations/{remediation_id}")

    def list_remediations(self, params=None):
        return self._request("GET", f"/organizations/{self._organization_id}/remediations", params=params)

    def list_investigation_templates(self, params=None):
        return self._request("GET", f"/organizations/{self._organization_id}/investigation-templates", params=params)

    def list_catalog_types(self, params=None):
        return self._request("GET", f"/organizations/{self._organization_id}/catalog/types", params=params)

    def create_remediation(self, body):
        return self._request("POST", f"/organizations/{self._organization_id}/remediations", json_data=body)

    def create_investigation(self, body, params=None):
        return self._request("POST", f"/organizations/{self._organization_id}/investigations", params=params, json_data=body)

    def list_business_context_uploads(self, params=None):
        return self._request("GET", f"/organizations/{self._organization_id}/business-context/uploads", params=params)

    def get_business_context_upload(self, upload_id):
        return self._request("GET", f"/organizations/{self._organization_id}" f"/business-context/uploads/{upload_id}")

    def create_business_context_upload(self, body):
        return self._request("POST", f"/organizations/{self._organization_id}/business-context/uploads", json_data=body)

    def replace_business_context_upload(self, upload_id, body):
        return self._request(
            "PUT", f"/organizations/{self._organization_id}" f"/business-context/uploads/{upload_id}", json_data=body
        )

    def delete_business_context_upload(self, upload_id):
        # 204 with no body, so do not ask for JSON back.
        return self._request(
            "DELETE",
            f"/organizations/{self._organization_id}" f"/business-context/uploads/{upload_id}",
            resp_type="response",
            ok_codes=(200, 204),
        )


""" HELPERS """


def error_detail(exc):
    """
    Pull the API's structured Error body out of a DemistoException.
    Returns (status_code, message, trace_id); any of them may be empty when
    the exception did not originate from an HTTP response.
    """
    response = getattr(exc, "res", None)
    status_code = getattr(response, "status_code", None)
    message = str(exc)
    trace_id = ""

    if response is not None:
        try:
            body = response.json()
            message = body.get("message") or message
            trace_id = body.get("traceId") or ""
        except Exception:
            pass
        if not trace_id:
            try:
                trace_id = response.headers.get("X-Cmdzero-Traceid", "")
            except Exception:
                trace_id = ""

    return status_code, message, trace_id


def fetch_all_organizations(client):
    """
    Every organization the API key can reach, following pagination. Used by the
    connection test, where scanning only the first page could wrongly report
    that a key has no access to the configured organization.
    """
    organizations: list[dict] = []
    params: dict = {"limit": ORG_PAGE_SIZE}

    for _ in range(MAX_ORG_PAGES):
        result = client.list_organizations(params)
        organizations.extend(result.get("organizations") or [])

        cursor = result.get("next")
        if not cursor:
            break
        params = {"limit": ORG_PAGE_SIZE, "next": cursor}

    return organizations


def justification_with_investigation(justification, investigation_id):
    """
    Tag the justification so the remediation can later be found for this
    investigation. The marker is appended rather than replacing anything, and
    the analyst's own wording is trimmed first if the field would overflow —
    losing the correlation key would defeat the point.
    """
    if not investigation_id:
        return justification

    marker = INVESTIGATION_MARKER.format(investigation_id)
    if marker in justification:
        return justification

    combined = f"{justification} {marker}".strip()
    if len(combined) > MAX_JUSTIFICATION_LENGTH:
        keep = MAX_JUSTIFICATION_LENGTH - len(marker) - 2
        combined = f"{justification[:max(keep, 0)].rstrip()}… {marker}"
    return combined


def remediation_filter_for_investigation(investigation_id):
    marker = INVESTIGATION_MARKER.format(investigation_id)
    return f"contains(justification, '{marker}')"


def lookup_undo_template_id(client, template_id):
    """
    Rollback availability lives on the RemediationTemplate, not on the
    Remediation response, so it needs a second call. A failure here must not
    mask a remediation that already executed.
    """
    try:
        template = client.get_remediation_template(template_id)
    except Exception as e:
        demisto.debug(f"Could not resolve undoTemplateId for {template_id}: {e}")
        return ""
    return template.get("undoTemplateId", "")


""" WRITE-BACK COMPOSITION """

# The connector writes investigation outcomes to the War Room as a note. It
# deliberately does NOT set incident, alert, or investigation fields — severity,
# status and confidence stay under the analyst's control. Because the output is
# markdown rather than a field write, this composer is identical on XSOAR and
# XSIAM; only the entry it is attached to differs.


def demote_markdown_headings(text, floor=4):
    """
    The API summary is free-form markdown and may carry its own top-level
    headings. Demote them so they nest under the note's sections rather than
    outranking them, while keeping their relative hierarchy intact.
    """

    def _demote(match):
        level = min(len(match.group(1)) + floor - 1, 6)
        return "#" * level + " "

    return re.sub(r"^(#{1,6})\s+", _demote, text, flags=re.MULTILINE)


def format_verdict(investigation):
    """`verdict` is an open array of labels, not a single enumerated value."""
    verdict = investigation.get("verdict") or []
    if isinstance(verdict, str):
        return verdict
    return ", ".join(str(v) for v in verdict if v)


def compose_response_action_section(response_action, disposition=None):
    """
    Renders what happened to the response action, if anything did. When nothing
    did, the note says *why* — an investigation submitted for analysis only is
    a different statement from one whose verdict did not qualify, and the audit
    record should not blur them.

    Every phrasing is scoped to "this integration": the connector can attest to
    what it requested, not to what Command Zero evaluated internally.
    """
    if not response_action:
        return "### Response action\n\n" + NO_RESPONSE_DISPOSITIONS.get(disposition, NO_RESPONSE_DISPOSITIONS[None]) + "\n"

    outcome = response_action.get("outcome") or ""
    lines = ["### Response action\n"]

    if outcome == GOVERNANCE_BLOCKED:
        lines.append("**Blocked by governance — not executed.**\n")
    elif outcome == GOVERNANCE_CONFLICT:
        lines.append("**Conflicted with another action — not executed.**\n")
    elif outcome == GOVERNANCE_EXECUTED:
        lines.append("**Executed.**\n")

    for label, key in (
        ("Action", "type"),
        ("Remediation ID", "id"),
        ("Execution status", "status"),
        ("Reason", "reason"),
    ):
        value = response_action.get(key)
        if value:
            lines.append(f"- **{label}:** {value}")

    rollback = response_action.get("rollbackTemplateId")
    if rollback:
        lines.append(f"- **Rollback available:** yes (template `{rollback}`)")
    elif outcome == GOVERNANCE_EXECUTED:
        lines.append("- **Rollback available:** no")

    return "\n".join(lines) + "\n"


def compose_third_party_section(third_party_actions):
    """
    Actions taken in the customer's own stack, orchestrated by the playbook
    rather than by Command Zero. Reported alongside the native action so the
    analyst sees the whole containment picture in one place.
    """
    if not third_party_actions:
        return ""

    rows = [
        {
            "System": action.get("system"),
            "Action": action.get("action"),
            "Target": action.get("target"),
            "Status": action.get("status"),
            "Reference": action.get("reference"),
        }
        for action in third_party_actions
    ]

    return (
        tableToMarkdown(
            "Third-party response actions",
            rows,
            headers=["System", "Action", "Target", "Status", "Reference"],
        )
        + "\n_Executed by this SOAR, not by Command Zero._\n"
    )


def third_party_actions_failed(third_party_actions):
    return any(str(action.get("status", "")).lower() in THIRD_PARTY_FAILURE_STATUSES for action in third_party_actions or [])


def compose_related_remediations_section(remediations):
    """
    Command Zero remediations already recorded against this investigation,
    found via the justification marker. Distinct from the action this playbook
    took: these may predate the run or have been raised by someone else.
    """
    if not remediations:
        return ""

    rows = [
        {
            "Action": r.get("templateName"),
            "Subject": (r.get("subject") or {}).get("value"),
            "Status": r.get("status"),
            "Created": r.get("createdTime"),
        }
        for r in remediations
    ]

    return (
        tableToMarkdown(
            "Other Command Zero actions on this investigation",
            rows,
            headers=["Action", "Subject", "Status", "Created"],
        )
        + "\n_Found by correlation on the justification marker, so actions "
        "raised directly in the Command Zero console may not appear._\n"
    )


def compose_investigation_note(
    investigation, response_action=None, third_party_actions=None, disposition=None, related_remediations=None
):
    """
    Build the War Room note for a completed investigation. Returns markdown.
    """
    verdict = format_verdict(investigation)
    failed = investigation.get("status") in TERMINAL_FAILURE_STATUSES

    if failed:
        heading = "## ⚠️ Command Zero Investigation Failed"
    elif verdict:
        heading = f"## Command Zero Investigation Complete — {verdict}"
    else:
        heading = "## Command Zero Investigation Complete"

    facts = [
        ("Investigation ID", investigation.get("id")),
        ("Title", investigation.get("title")),
        ("Verdict", verdict or "None assigned"),
        ("Severity", investigation.get("severity")),
        ("Confidence", investigation.get("confidenceLevel")),
        ("Status", investigation.get("status")),
        ("Category", investigation.get("category")),
        ("Completed", investigation.get("completedTime")),
    ]
    fact_lines = [f"- **{label}:** {value}" for label, value in facts if value]

    console_url = investigation.get("consoleUrl")
    if console_url:
        fact_lines.append(f"- **Console:** [Open in Command Zero]({console_url})")

    sections = [heading, "", "\n".join(fact_lines), ""]

    summary = investigation.get("summary")
    if summary:
        # Skip our own label when the summary already opens with a heading,
        # otherwise the note reads "Findings" twice in a row.
        if not summary.lstrip().startswith("#"):
            sections += ["### Findings", ""]
        sections += [demote_markdown_headings(summary), ""]

    observables = investigation.get("observables") or []
    if observables:
        rows = [
            {
                "Type": o.get("type"),
                "Value": o.get("value"),
                "Origin": ", ".join(o.get("origin") or []),
            }
            for o in observables
        ]
        sections += [
            tableToMarkdown("Observables", rows, headers=["Type", "Value", "Origin"]),
            "",
        ]

    sections += [compose_response_action_section(response_action, disposition)]

    third_party = compose_third_party_section(third_party_actions)
    if third_party:
        sections += ["", third_party]

    related = compose_related_remediations_section(related_remediations)
    if related:
        sections += ["", related]

    error = investigation.get("error")
    if error:
        sections += ["", f"**Error:** {error}"]

    return "\n".join(sections)


def parse_json_array_arg(raw, arg_name, example):
    """
    Playbooks pass structured arguments as JSON strings. On a parse failure,
    show a worked example rather than letting a raw decode error surface —
    context stringification is an easy thing to get subtly wrong.
    """
    if not raw:
        return []

    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        raise ValueError(f"{arg_name} must be a JSON array. For example: {example}")

    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        raise ValueError(f"{arg_name} must be a JSON array of objects.")

    return value


def third_party_actions_from_args(args):
    """
    Supplied by the playbook as a JSON array, so one note can report every
    containment step taken across the stack — ticketing, on-call, network.
    """
    actions = parse_json_array_arg(
        args.get("third_party_actions"),
        "third_party_actions",
        '[{"system":"ServiceNow","action":"Incident raised",'
        '"target":"user@company.com","status":"completed",'
        '"reference":"INC0012345"}]',
    )
    return [action for action in actions if isinstance(action, dict) and any(action.values())]


def related_remediations_from_args(args):
    """Remediations already recorded against this investigation."""
    return parse_json_array_arg(
        args.get("related_remediations"),
        "related_remediations",
        '[{"templateName":"Disable User","status":"success"}]',
    )


def response_action_from_args(args):
    """
    Response action details are supplied by the playbook from the outputs of
    cmdzero-remediation-create, so the note can report the native action
    alongside the verdict. Returns None when the playbook passed nothing.
    """
    action = {
        "outcome": args.get("response_action_outcome"),
        "type": args.get("response_action_type"),
        "id": args.get("response_action_id"),
        "status": args.get("response_action_status"),
        "reason": args.get("response_action_reason"),
        "rollbackTemplateId": args.get("rollback_template_id"),
    }
    return action if any(action.values()) else None


""" COMMAND FUNCTIONS """


def run_test_module(client):
    demisto.debug(f"Command Zero API schema version targeted: {CMDZERO_API_SCHEMA_VERSION}")

    result = client.health_check()
    if result.get("status") != "ok":
        return (
            "Connection failed: the Command Zero API did not report a healthy "
            "status. Verify the Base URL is correct and reachable."
        )

    # An API key may be granted access to several organizations, so a valid key
    # does not imply access to the one configured here. Checking now turns a
    # 403 on every subsequent command into one clear message at setup time.
    organizations = fetch_all_organizations(client)
    configured = client.organization_id

    if not any(org.get("id") == configured for org in organizations):
        available = ", ".join(f"{org.get('name')} ({org.get('id')})" for org in organizations[:MAX_ORGS_IN_ERROR])
        if len(organizations) > MAX_ORGS_IN_ERROR:
            available += f", and {len(organizations) - MAX_ORGS_IN_ERROR} more"

        return (
            f"Connection failed: the API key is valid, but it does not have "
            f"access to organization '{configured}'. Organizations available "
            f"to this key: {available or 'none'}."
        )

    return "ok"


def list_organizations_command(client, args):
    limit = args.get("limit", str(DEFAULT_PAGE_SIZE))
    filter_expr = args.get("filter")
    next_token = args.get("next_token")

    params: dict = {"limit": limit}
    if filter_expr:
        params["filter"] = filter_expr
    if next_token:
        params["next"] = next_token

    result = client.list_organizations(params)
    organizations = result.get("organizations") or []

    readable_output = tableToMarkdown(
        f"Command Zero Organizations ({len(organizations)} results)", organizations, headers=["id", "name", "role", "createdTime"]
    )

    # Same shape as the other list commands, so the pagination cursor has
    # somewhere to live. The context path stays CommandZero.Organization.
    outputs: dict = {"Organization": organizations}
    if result.get("next"):
        outputs["OrganizationNextToken"] = result["next"]

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero",
        outputs_key_field="Organization.id",
        outputs=outputs,
        raw_response=result,
    )


def list_remediation_templates_command(client, args):
    limit = args.get("limit", str(DEFAULT_PAGE_SIZE))
    next_token = args.get("next_token")
    subject_type = args.get("subject_type")

    params: dict = {"limit": limit}
    if next_token:
        params["next"] = next_token
    if subject_type:
        params["subjectType"] = subject_type

    result = client.list_remediation_templates(params)
    templates = result.get("remediation-templates", [])

    readable_output = tableToMarkdown(
        f"Command Zero Remediation Templates ({len(templates)} results)",
        templates,
        headers=["id", "name", "displayName", "subjectType", "undoTemplateId"],
    )

    outputs: dict = {"RemediationTemplate": templates}
    if result.get("next"):
        outputs["RemediationTemplateNextToken"] = result["next"]

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero",
        outputs_key_field="RemediationTemplate.id",
        outputs=outputs,
        raw_response=result,
    )


def list_investigations_command(client, args):
    limit = args.get("limit", str(DEFAULT_PAGE_SIZE))
    filter_expr = args.get("filter")
    next_token = args.get("next_token")

    params: dict = {"limit": limit}
    if filter_expr:
        params["filter"] = filter_expr
    if next_token:
        params["next"] = next_token

    result = client.list_investigations(params)
    investigations = result.get("investigations", [])

    readable_output = tableToMarkdown(
        f"Command Zero Investigations ({len(investigations)} results)",
        investigations,
        headers=["id", "title", "status", "severity", "category", "completed"],
    )

    outputs: dict = {"Investigation": investigations}
    if result.get("next"):
        outputs["InvestigationNextToken"] = result["next"]

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero",
        outputs_key_field="Investigation.id",
        outputs=outputs,
        raw_response=result,
    )


def get_investigation_command(client, args):
    investigation_id = args.get("investigation_id")
    if not investigation_id:
        raise ValueError("investigation_id is required")

    result = client.get_investigation(investigation_id)

    readable_output = tableToMarkdown(
        "Command Zero Investigation",
        result,
        headers=["id", "title", "status", "severity", "category", "completed", "verdict", "consoleUrl"],
    )

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero.Investigation",
        outputs_key_field="id",
        outputs=result,
        raw_response=result,
    )


def investigation_results_command(client, args):
    """
    Generic-polling command: waits for the verdict, then writes the outcome to
    the War Room as a note. Nothing inbound to XSOAR is required.
    """
    investigation_id = args.get("investigation_id")
    if not investigation_id:
        raise ValueError("investigation_id is required")

    investigation = client.get_investigation(investigation_id)
    status = investigation.get("status") or "investigating"
    completed = investigation.get("completed")

    if not completed and status not in TERMINAL_FAILURE_STATUSES:
        interval = arg_to_number(args.get("interval_in_seconds")) or DEFAULT_POLL_INTERVAL
        timeout = arg_to_number(args.get("timeout_in_seconds")) or DEFAULT_POLL_TIMEOUT

        ScheduledCommand.raise_error_if_not_supported()
        scheduled_command = ScheduledCommand(
            command="cmdzero-investigation-results",
            next_run_in_seconds=interval,
            args=args,
            timeout_in_seconds=timeout,
        )

        return CommandResults(
            readable_output=(f"Waiting on Command Zero investigation {investigation_id} " f"(status: {status})."),
            scheduled_command=scheduled_command,
            outputs_prefix="CommandZero.Investigation",
            outputs_key_field="id",
            outputs=investigation,
            raw_response=investigation,
        )

    post_note = argToBoolean(args.get("post_note", "true"))
    response_action = response_action_from_args(args)
    third_party_actions = third_party_actions_from_args(args)
    disposition = args.get("response_disposition")
    related = related_remediations_from_args(args)

    if post_note:
        readable_output = compose_investigation_note(investigation, response_action, third_party_actions, disposition, related)
    else:
        readable_output = f"Command Zero investigation {investigation_id} finished " f"with status {status}."

    return CommandResults(
        readable_output=readable_output,
        mark_as_note=post_note,
        entry_type=(EntryType.WARNING if status in TERMINAL_FAILURE_STATUSES else EntryType.NOTE),
        outputs_prefix="CommandZero.Investigation",
        outputs_key_field="id",
        outputs=investigation,
        raw_response=investigation,
    )


def post_investigation_note_command(client, args):
    """
    Writes the investigation outcome to the War Room on demand. Used after a
    response action so the note can report the verdict and the action together.
    """
    investigation_id = args.get("investigation_id")
    if not investigation_id:
        raise ValueError("investigation_id is required")

    investigation = client.get_investigation(investigation_id)
    response_action = response_action_from_args(args)
    third_party_actions = third_party_actions_from_args(args)

    blocked = response_action and response_action.get("outcome") in (GOVERNANCE_BLOCKED, GOVERNANCE_CONFLICT)
    failed = investigation.get("status") in TERMINAL_FAILURE_STATUSES
    stack_failed = third_party_actions_failed(third_party_actions)

    return CommandResults(
        readable_output=compose_investigation_note(
            investigation,
            response_action,
            third_party_actions,
            args.get("response_disposition"),
            related_remediations_from_args(args),
        ),
        mark_as_note=True,
        entry_type=(EntryType.WARNING if (blocked or failed or stack_failed) else EntryType.NOTE),
        outputs_prefix="CommandZero.Investigation",
        outputs_key_field="id",
        outputs=investigation,
        raw_response=investigation,
    )


def create_remediation_command(client, args):
    template_id = args.get("template_id")
    subject_type = args.get("subject_type")
    subject_value = args.get("subject_value")
    justification = args.get("justification")

    if not template_id:
        raise ValueError("template_id is required")
    if not subject_type:
        raise ValueError("subject_type is required")
    if not subject_value:
        raise ValueError("subject_value is required")
    if not justification:
        raise ValueError("justification is required")

    body = {
        "templateId": template_id,
        "subject": {"type": subject_type, "value": subject_value},
        "justification": justification_with_investigation(justification, args.get("investigation_id")),
    }

    # optional postback
    postback_url = args.get("postback_url")
    postback_token = args.get("postback_token")
    if postback_url:
        postback: dict = {"url": postback_url}
        if postback_token:
            postback["token"] = postback_token
        body["postback"] = postback

    try:
        result = client.create_remediation(body)
    except DemistoException as e:
        status_code, message, trace_id = error_detail(e)
        if status_code in (403, 409):
            # Governance declined the action. The playbook must be able to
            # carry this into the write-back rather than failing outright.
            return governance_refusal_results(status_code, message, trace_id, body)
        raise

    undo_template_id = lookup_undo_template_id(client, template_id)

    outputs = dict(result)
    outputs["governanceOutcome"] = GOVERNANCE_EXECUTED
    outputs["undoTemplateId"] = undo_template_id
    outputs["rollbackAvailable"] = bool(undo_template_id)

    readable_output = tableToMarkdown(
        "Command Zero Remediation Created",
        outputs,
        headers=["id", "status", "templateName", "justification", "rollbackAvailable", "undoTemplateId"],
    )

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero.Remediation",
        outputs_key_field="id",
        outputs=outputs,
        raw_response=result,
    )


def remediation_results_command(client, args):
    """
    Waits for a queued remediation to finish, so the outcome reported is the
    real one rather than `pending`. Separate from cmdzero-remediation-create
    because a polling command re-runs itself — creating remediations on a loop
    is not something to risk.
    """
    remediation_id = args.get("remediation_id")
    if not remediation_id:
        raise ValueError("remediation_id is required")

    remediation = client.get_remediation(remediation_id)
    status = remediation.get("status") or ""

    if status == REMEDIATION_PENDING_STATUS:
        interval = arg_to_number(args.get("interval_in_seconds")) or DEFAULT_REMEDIATION_POLL_INTERVAL
        timeout = arg_to_number(args.get("timeout_in_seconds")) or DEFAULT_REMEDIATION_POLL_TIMEOUT

        ScheduledCommand.raise_error_if_not_supported()
        scheduled_command = ScheduledCommand(
            command="cmdzero-remediation-results",
            next_run_in_seconds=interval,
            args=args,
            timeout_in_seconds=timeout,
        )

        return CommandResults(
            readable_output=(f"Waiting on Command Zero remediation {remediation_id} " f"(status: {status})."),
            scheduled_command=scheduled_command,
            outputs_prefix="CommandZero.Remediation",
            outputs_key_field="id",
            outputs=remediation,
            raw_response=remediation,
        )

    failed = status in REMEDIATION_FAILURE_STATUSES
    heading = "Command Zero Remediation Failed" if failed else "Command Zero Remediation Completed"

    readable_output = tableToMarkdown(heading, remediation, headers=["id", "status", "templateName", "error", "completedTime"])

    return CommandResults(
        readable_output=readable_output,
        entry_type=EntryType.WARNING if failed else EntryType.NOTE,
        outputs_prefix="CommandZero.Remediation",
        outputs_key_field="id",
        outputs=remediation,
        raw_response=remediation,
    )


def governance_refusal_results(status_code, message, trace_id, body):
    """
    403 means a governance rule blocked the action; 409 means it conflicts with
    another action. Neither is a connector fault, so both are reported as a
    result the playbook can branch on and forward to the case.
    """
    outcome = GOVERNANCE_CONFLICT if status_code == 409 else GOVERNANCE_BLOCKED

    outputs = {
        "templateId": body.get("templateId"),
        "subject": body.get("subject"),
        "justification": body.get("justification"),
        "governanceOutcome": outcome,
        "governanceHttpStatus": status_code,
        "governanceReason": message,
        "traceId": trace_id,
    }

    heading = "Command Zero Remediation Conflict" if outcome == GOVERNANCE_CONFLICT else "Command Zero Remediation Blocked"
    readable_output = tableToMarkdown(
        heading, outputs, headers=["templateId", "governanceOutcome", "governanceHttpStatus", "governanceReason", "traceId"]
    )

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero.Remediation",
        outputs_key_field="id",
        outputs=outputs,
        raw_response={"status": status_code, "message": message, "traceId": trace_id},
    )


def alert_submission_body(alert_data, alert_schema, alert_type, title, description):
    """
    Build the alert half of a submission, enforcing the API's three forms
    locally so a malformed shape fails here with an explanation rather than as
    a 422 from the server.

      1. alertType + alertData                      — schema resolved from the
                                                      type; title and
                                                      description required
      2. alertType + alertData + alertSchema array  — schema supplied inline
      3. alertData + alertSchema catalog string     — alertType must NOT be set

    The choice between 2 and 3 matters: a catalog type says "this payload has
    the shape Command Zero already knows for that alert", which only holds if
    the data has not been reshaped on the way here. Annotations say "here is
    where the values are in *my* shape". See the pack documentation.
    """
    parsed_data = json.loads(alert_data) if isinstance(alert_data, str) else alert_data

    schema = alert_schema
    if isinstance(schema, str):
        schema = schema.strip()
        if schema.startswith("["):
            schema = parse_json_array_arg(schema, "alert_schema", '[{"path":"sender.email","type":"EMAIL_ADDRESS"}]')

    body: dict = {"alertData": parsed_data}

    if isinstance(schema, list) and schema:
        # Form 2 — inline annotations.
        if not alert_type:
            raise ValueError(
                "alert_type is required when alert_schema is a list of "
                "annotations. It tells Command Zero which kind of alert this "
                "is; the annotations only say where the values live."
            )
        body["alertType"] = alert_type
        body["alertSchema"] = schema

    elif schema:
        # Form 3 — a known catalog type.
        if alert_type:
            raise ValueError(
                "alert_type must not be set when alert_schema is a catalog "
                "type string. The catalog entry already defines the alert "
                "type. Supply annotations instead if your data has been "
                "reshaped and no longer matches that catalog entry."
            )
        body["alertSchema"] = schema

    else:
        # Form 1 — no schema, resolved from the alert type.
        if not alert_type:
            raise ValueError(
                "Provide alert_type, alert_schema, or both. Use alert_type "
                "alone when Command Zero already knows the alert type, "
                "alert_schema as a catalog type string when the payload "
                "matches a known catalog entry unchanged, or alert_type with "
                "alert_schema annotations to map your own shape."
            )
        if not title or not description:
            raise ValueError(
                "title and description are both required when submitting " "alert_type and alert_data without an alert_schema."
            )
        body["alertType"] = alert_type

    if title:
        body["title"] = title
    if description:
        body["description"] = description

    return body


def create_investigation_command(client, args):
    template_id = args.get("template_id")
    alert_data = args.get("alert_data")
    alert_schema = args.get("alert_schema")
    title = args.get("title")
    postback_url = args.get("postback_url")
    postback_token = args.get("postback_token")

    body: dict = {}

    if template_id:
        # Form 3 — template + leads
        leads_raw = args.get("leads", "[]")
        leads = json.loads(leads_raw) if isinstance(leads_raw, str) else leads_raw
        body["templateId"] = template_id
        body["leads"] = leads
        if title:
            body["title"] = title
        start_time = args.get("start_time")
        end_time = args.get("end_time")
        if start_time:
            body["startTime"] = start_time
        if end_time:
            body["endTime"] = end_time

    elif alert_data:
        body.update(
            alert_submission_body(
                alert_data,
                alert_schema,
                args.get("alert_type"),
                title,
                args.get("description"),
            )
        )
        if args.get("category"):
            body["category"] = args["category"]
        if args.get("tags"):
            body["tags"] = parse_json_array_arg(args["tags"], "tags", '["urgent","vip-user"]')

    else:
        raise ValueError("Either template_id or alert_data must be provided.")

    if postback_url:
        postback: dict = {"url": postback_url}
        if postback_token:
            postback["token"] = postback_token
        body["postback"] = postback

    # nosettle suppresses report generation and settlement notifications,
    # which is what you want when exercising the integration against a real
    # tenant rather than running a real investigation.
    params = None
    if argToBoolean(args.get("nosettle", "false")):
        params = {"nosettle": "true"}

    result = client.create_investigation(body, params)

    # `merged` means the alert joined an existing investigation rather than
    # starting a new one. Either way the caller gets an investigation ID back.
    action = result.get("action") or "created"
    heading = (
        "Command Zero Alert Merged Into Existing Investigation" if action == "merged" else "Command Zero Investigation Created"
    )

    readable_output = tableToMarkdown(heading, result, headers=["id", "action", "title", "status", "severity", "consoleUrl"])

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero.Investigation",
        outputs_key_field="id",
        outputs=result,
        raw_response=result,
    )


def paged_list_params(args):
    """The list endpoints share one parameter shape."""
    params: dict = {"limit": args.get("limit", str(DEFAULT_PAGE_SIZE))}
    if args.get("filter"):
        params["filter"] = args["filter"]
    if args.get("next_token"):
        params["next"] = args["next_token"]
    return params


def list_remediations_command(client, args):
    params = paged_list_params(args)

    investigation_id = args.get("investigation_id")
    if investigation_id:
        if params.get("filter"):
            raise ValueError(
                "Provide either investigation_id or filter, not both. " "investigation_id builds the filter for you."
            )
        params["filter"] = remediation_filter_for_investigation(investigation_id)
    elif args.get("subject_type"):
        params["filter"] = f"subjectType eq '{args['subject_type']}'"

    result = client.list_remediations(params)
    remediations = result.get("remediations") or []

    readable_output = tableToMarkdown(
        f"Command Zero Remediations ({len(remediations)} results)",
        remediations,
        headers=["id", "templateName", "subject", "status", "error", "createdTime"],
    )

    outputs: dict = {"Remediation": remediations}
    if result.get("next"):
        outputs["RemediationNextToken"] = result["next"]

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero",
        outputs_key_field="Remediation.id",
        outputs=outputs,
        raw_response=result,
    )


def list_investigation_templates_command(client, args):
    result = client.list_investigation_templates(paged_list_params(args))
    templates = result.get("investigation-templates") or []

    readable_output = tableToMarkdown(
        f"Command Zero Investigation Templates ({len(templates)} results)",
        templates,
        headers=["id", "name", "title", "scenario", "leadTypes", "severity"],
    )

    outputs: dict = {"InvestigationTemplate": templates}
    if result.get("next"):
        outputs["InvestigationTemplateNextToken"] = result["next"]

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero",
        outputs_key_field="InvestigationTemplate.id",
        outputs=outputs,
        raw_response=result,
    )


def list_catalog_types_command(client, args):
    result = client.list_catalog_types(paged_list_params(args))
    types = result.get("types") or []

    readable_output = tableToMarkdown(
        f"Command Zero Catalog Types ({len(types)} results)", types, headers=["id", "name", "description", "isAlert", "examples"]
    )

    outputs: dict = {"CatalogType": types}
    if result.get("next"):
        outputs["CatalogTypeNextToken"] = result["next"]

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero",
        outputs_key_field="CatalogType.id",
        outputs=outputs,
        raw_response=result,
    )


""" BUSINESS CONTEXT """

RECORDS_EXAMPLE = '[{"email":"user@company.com","department":"Engineering","vip":true}]'
SCHEMA_EXAMPLE = '[{"path":"email","type":"EMAIL_ADDRESS"},{"path":"department","type":"TEXT"}]'


def context_records_and_schema(args, required):
    """
    Records and schema travel together: the API accepts a metadata-only update,
    but rejects one of the pair without the other.
    """
    records = parse_json_array_arg(args.get("records"), "records", RECORDS_EXAMPLE)
    schema = parse_json_array_arg(args.get("schema"), "schema", SCHEMA_EXAMPLE)

    if not required and not records and not schema:
        return None, None

    if bool(records) != bool(schema):
        raise ValueError(
            "records and schema must be supplied together. Provide both to "
            "replace the data, or neither to update only name and description."
        )

    if not records:
        raise ValueError("records must contain at least one object.")

    if len(schema) < MIN_CONTEXT_SCHEMA_ANNOTATIONS:
        raise ValueError(
            f"schema must contain at least {MIN_CONTEXT_SCHEMA_ANNOTATIONS} "
            "annotations, at least one of which maps to a subject type such "
            "as EMAIL_ADDRESS or HOST_NAME."
        )

    return records, schema


def business_context_upload_results(upload, heading, entry_type=None):
    return CommandResults(
        readable_output=tableToMarkdown(
            heading, upload, headers=["id", "name", "status", "recordCount", "subjectTypes", "error"]
        ),
        entry_type=entry_type or EntryType.NOTE,
        outputs_prefix="CommandZero.BusinessContextUpload",
        outputs_key_field="id",
        outputs=upload,
        raw_response=upload,
    )


def list_business_context_command(client, args):
    limit = args.get("limit", str(DEFAULT_PAGE_SIZE))
    filter_expr = args.get("filter")
    next_token = args.get("next_token")

    params: dict = {"limit": limit}
    if filter_expr:
        params["filter"] = filter_expr
    if next_token:
        params["next"] = next_token

    result = client.list_business_context_uploads(params)
    uploads = result.get("uploads") or []

    readable_output = tableToMarkdown(
        f"Command Zero Business Context Uploads ({len(uploads)} results)",
        uploads,
        headers=["id", "name", "status", "recordCount", "subjectTypes", "updatedTime"],
    )

    outputs: dict = {"BusinessContextUpload": uploads}
    if result.get("next"):
        outputs["BusinessContextUploadNextToken"] = result["next"]

    return CommandResults(
        readable_output=readable_output,
        outputs_prefix="CommandZero",
        outputs_key_field="BusinessContextUpload.id",
        outputs=outputs,
        raw_response=result,
    )


def get_business_context_command(client, args):
    upload_id = args.get("upload_id")
    if not upload_id:
        raise ValueError("upload_id is required")

    upload = client.get_business_context_upload(upload_id)
    return business_context_upload_results(upload, "Command Zero Business Context Upload")


def upload_business_context_command(client, args):
    name = args.get("name")
    if not name:
        raise ValueError("name is required")

    records, schema = context_records_and_schema(args, required=True)

    body: dict = {"name": name, "records": records, "schema": schema}
    description = args.get("description")
    if description:
        body["description"] = description

    upload = client.create_business_context_upload(body)
    return business_context_upload_results(upload, "Command Zero Business Context Uploaded")


def replace_business_context_command(client, args):
    upload_id = args.get("upload_id")
    if not upload_id:
        raise ValueError("upload_id is required")

    records, schema = context_records_and_schema(args, required=False)

    body: dict = {}
    if records:
        # A replace is a full replacement of the records, never a merge.
        body["records"] = records
        body["schema"] = schema
    # Written out rather than looped so the argument reads stay visible to the
    # YAML/code contract test.
    if args.get("name"):
        body["name"] = args["name"]
    if args.get("description"):
        body["description"] = args["description"]

    if not body:
        raise ValueError("Provide records and schema to replace the data, or a name or " "description to update the metadata.")

    upload = client.replace_business_context_upload(upload_id, body)
    return business_context_upload_results(upload, "Command Zero Business Context Replaced")


def delete_business_context_command(client, args):
    upload_id = args.get("upload_id")
    if not upload_id:
        raise ValueError("upload_id is required")

    client.delete_business_context_upload(upload_id)

    return CommandResults(
        readable_output=(
            f"Business context upload {upload_id} deleted. Investigations that "
            "already ran keep the context they had; new investigations will "
            "not see it."
        ),
        outputs_prefix="CommandZero.BusinessContextUpload",
        outputs_key_field="id",
        outputs={"id": upload_id, "deleted": True},
    )


def business_context_results_command(client, args):
    """
    Uploads are processed asynchronously and are not applied to investigations
    until processing completes, so a sync that reports success on the POST
    alone would be reporting too early.
    """
    upload_id = args.get("upload_id")
    if not upload_id:
        raise ValueError("upload_id is required")

    upload = client.get_business_context_upload(upload_id)
    status = upload.get("status") or ""

    if status == CONTEXT_PROCESSING_STATUS:
        interval = arg_to_number(args.get("interval_in_seconds")) or DEFAULT_CONTEXT_POLL_INTERVAL
        timeout = arg_to_number(args.get("timeout_in_seconds")) or DEFAULT_CONTEXT_POLL_TIMEOUT

        ScheduledCommand.raise_error_if_not_supported()
        scheduled_command = ScheduledCommand(
            command="cmdzero-business-context-results",
            next_run_in_seconds=interval,
            args=args,
            timeout_in_seconds=timeout,
        )

        return CommandResults(
            readable_output=(f"Waiting on Command Zero business context upload " f"{upload_id} (status: {status})."),
            scheduled_command=scheduled_command,
            outputs_prefix="CommandZero.BusinessContextUpload",
            outputs_key_field="id",
            outputs=upload,
            raw_response=upload,
        )

    failed = status in CONTEXT_FAILURE_STATUSES
    return business_context_upload_results(
        upload,
        "Command Zero Business Context Upload Failed" if failed else "Command Zero Business Context Upload Ready",
        entry_type=EntryType.WARNING if failed else EntryType.NOTE,
    )


""" MAIN """


def main():
    params = demisto.params()
    command = demisto.command()
    demisto.debug(f"Command being called is {command}")

    try:
        api_key = params.get("api_key")
        organization_id = params.get("organization_id")
        base_url = params.get("base_url") or CMDZERO_BASE_URL
        verify = not params.get("insecure", False)
        proxy = params.get("proxy", False)

        client = Client(
            api_key=api_key,
            organization_id=organization_id,
            base_url=base_url,
            verify=verify,
            proxy=proxy,
        )

        if command == "test-module":
            return_results(run_test_module(client))
        elif command == "cmdzero-organization-list":
            return_results(list_organizations_command(client, demisto.args()))
        elif command == "cmdzero-investigation-list":
            return_results(list_investigations_command(client, demisto.args()))
        elif command == "cmdzero-investigation-get":
            return_results(get_investigation_command(client, demisto.args()))
        elif command == "cmdzero-investigation-results":
            return_results(investigation_results_command(client, demisto.args()))
        elif command == "cmdzero-investigation-note":
            return_results(post_investigation_note_command(client, demisto.args()))
        elif command == "cmdzero-remediation-template-list":
            return_results(list_remediation_templates_command(client, demisto.args()))
        elif command == "cmdzero-remediation-create":
            return_results(create_remediation_command(client, demisto.args()))
        elif command == "cmdzero-remediation-results":
            return_results(remediation_results_command(client, demisto.args()))
        elif command == "cmdzero-remediation-list":
            return_results(list_remediations_command(client, demisto.args()))
        elif command == "cmdzero-investigation-template-list":
            return_results(list_investigation_templates_command(client, demisto.args()))
        elif command == "cmdzero-catalog-type-list":
            return_results(list_catalog_types_command(client, demisto.args()))
        elif command == "cmdzero-business-context-list":
            return_results(list_business_context_command(client, demisto.args()))
        elif command == "cmdzero-business-context-get":
            return_results(get_business_context_command(client, demisto.args()))
        elif command == "cmdzero-business-context-upload":
            return_results(upload_business_context_command(client, demisto.args()))
        elif command == "cmdzero-business-context-replace":
            return_results(replace_business_context_command(client, demisto.args()))
        elif command == "cmdzero-business-context-delete":
            return_results(delete_business_context_command(client, demisto.args()))
        elif command == "cmdzero-business-context-results":
            return_results(business_context_results_command(client, demisto.args()))
        elif command == "cmdzero-investigation-create":
            return_results(create_investigation_command(client, demisto.args()))
        else:
            raise NotImplementedError(f"Command '{command}' not implemented yet.")

    except Exception as e:
        return_error(f"Failed to execute {command} command. Error: {str(e)}")


if __name__ in ("__main__", "__builtin__", "builtins"):
    main()
