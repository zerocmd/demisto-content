Submit alerts to Command Zero for automated investigation, wait for a verdict, and write the findings to the War Room. Execute native Command Zero response actions under server-side governance. Targets Command Zero public API schema version 2026-03-12.

Command Zero runs automated security investigations. This integration submits
alerts from Cortex for investigation, waits for a verdict, writes the findings
to the War Room, and executes native Command Zero response actions under
Command Zero's own governance.

This integration targets Command Zero public API schema version
**2026-03-12**. If your tenant reports a different schema version, check
the release notes for this pack before upgrading.

## What this integration does, and does not, change

The integration **writes investigation outcomes to the War Room as notes**. It
does **not** set incident, alert, or investigation fields — severity, status,
confidence and ownership stay under the analyst's control. Verdict data informs
the analyst; it never silently mutates a case.

## Prerequisites

- A Command Zero tenant, and an application configured by your Command Zero
  administrators with the **Application** role.
- An API key issued to that application. Keys begin with `c0.`.
- The UUID of the organization the instance should work against, shown in the
  Command Zero console alongside the API key. An API key may be granted access
  to more than one organization, so this must name the one you intend to use —
  it is never inferred.
- Outbound HTTPS from Cortex to the Command Zero API. No inbound connectivity
  to Cortex is required — the integration polls for investigation results.

## Configure Command Zero in Cortex

| **Parameter** | **Description** | **Required** |
| --- | --- | --- |
| API Key | Your Command Zero API key, issued to an application with the Application role. Starts with "c0.". | True |
| Organization ID | The UUID of the Command Zero organization this instance works against. Find it in the Command Zero console, shown alongside the API key. An API key may have access to more than one organization, so this must name the one you intend to use. The Test button verifies the key can reach it. | True |
| Base URL | Use the default unless directed otherwise. | False |
| Trust any certificate (not secure) |  | False |
| Use system proxy settings |  | False |

### Setting up an instance

1. Navigate to **Settings** > **Integrations** > **Servers & Services**.
2. Search for **Command Zero**.
3. Click **Add instance** and complete the parameters above.
4. Click **Test**. The test checks three things: that the API is reachable,
   that the API key is valid, and that the key actually has access to the
   **Organization ID** you entered. It does not start an investigation.

If the key is valid but cannot reach the organization, the test names the
organizations the key *can* reach, so you can correct the field.

If the test fails, see [Troubleshooting](#troubleshooting).

## Commands

You can execute these commands from the CLI, as part of an automation, or in a playbook.
After you successfully execute a command, a DBot message appears in the War Room with the command details.

### cmdzero-organization-list

***
List organizations accessible to this API key.

#### Base Command

`cmdzero-organization-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| limit | Maximum number of items to return (1-10000). Default is 50. | Optional |
| filter | OData-style filter expression to narrow results. Supported fields are createdTime, name, role, updatedTime, createdBy/type, createdBy/id, createdBy/name, updatedBy/type, updatedBy/id, and updatedBy/name. Note that id is not filterable. | Optional |
| next_token | Pagination cursor from a previous response. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Organization.id | String | Organization unique identifier. |
| CommandZero.Organization.name | String | Organization display name. |
| CommandZero.Organization.role | String | Application role in this organization. |
| CommandZero.Organization.createdTime | String | When the organization was created. |
| CommandZero.Organization.updatedTime | String | When the organization was last updated. |
| CommandZero.OrganizationNextToken | String | Pagination cursor for the next page of results. |

#### Command example

```!cmdzero-organization-list limit=10 filter="role eq 'responder'"```

#### Human Readable Output

>### Command Zero Organizations (1 results)
>
>|id|name|role|createdTime|
>|---|---|---|---|
>| 9ea486fd-f7c1-420f-901b-89342acfce30 | Example Corp | responder | 2026-01-02T09:14:00Z |
>
### cmdzero-investigation-list

***
List investigations in the organization.

#### Base Command

`cmdzero-investigation-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| limit | Maximum number of results to return. Default is 50. | Optional |
| filter | OData filter expression (e.g. "status eq 'open'"). | Optional |
| next_token | Pagination cursor from a previous response. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Investigation.id | String | Investigation unique identifier. |
| CommandZero.Investigation.title | String | Investigation title. |
| CommandZero.Investigation.status | String | Investigation status. |
| CommandZero.Investigation.severity | String | Investigation severity. |
| CommandZero.Investigation.category | String | Investigation category. |
| CommandZero.Investigation.completed | Boolean | True when verdict is ready. |
| CommandZero.Investigation.verdict | Unknown | Verdict labels. |
| CommandZero.Investigation.consoleUrl | String | Direct link to the investigation in the console. |
| CommandZero.Investigation.createdTime | String | When the investigation was created. |
| CommandZero.InvestigationNextToken | String | Pagination cursor for the next page of results. |

#### Command example

```!cmdzero-investigation-list limit=5 filter="status eq 'completed'"```

#### Human Readable Output

>### Command Zero Investigations (1 results)
>
>|id|title|status|severity|category|completed|
>|---|---|---|---|---|---|
>| f47ac10b-58cc-4372-a567-0e02b2c3d479 | Malicious file detected in email | completed | high | Malware | true |
>
### cmdzero-investigation-get

***
Retrieve a specific investigation by ID.

#### Base Command

`cmdzero-investigation-get`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| investigation_id | The investigation UUID to retrieve. | Required |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Investigation.id | String | Investigation unique identifier. |
| CommandZero.Investigation.title | String | Investigation title. |
| CommandZero.Investigation.status | String | Investigation status. |
| CommandZero.Investigation.severity | String | Investigation severity. |
| CommandZero.Investigation.category | String | Investigation category. |
| CommandZero.Investigation.completed | Boolean | True when verdict is ready. |
| CommandZero.Investigation.verdict | Unknown | Verdict labels. |
| CommandZero.Investigation.summary | String | Markdown findings summary. |
| CommandZero.Investigation.description | String | Investigation description. |
| CommandZero.Investigation.startTime | String | Start of the investigation time window. |
| CommandZero.Investigation.endTime | String | End of the investigation time window. |
| CommandZero.Investigation.impact | String | Assessed impact of the threat. |
| CommandZero.Investigation.confidenceLevel | String | Confidence in the investigation findings. |
| CommandZero.Investigation.observables | Unknown | Observables discovered during investigation. |
| CommandZero.Investigation.consoleUrl | String | Direct link to the investigation in the console. |
| CommandZero.Investigation.createdTime | String | When the investigation was created. |
| CommandZero.Investigation.updatedTime | String | When the investigation was last updated. |

#### Command example

```!cmdzero-investigation-get investigation_id=f47ac10b-58cc-4372-a567-0e02b2c3d479```

#### Human Readable Output

>### Command Zero Investigation
>
>|id|title|status|severity|category|completed|verdict|consoleUrl|
>|---|---|---|---|---|---|---|---|
>| f47ac10b-58cc-4372-a567-0e02b2c3d479 | Malicious file detected in email | completed | high | Malware | true | Malicious | https://ui.cmdzero.io/... |
>
### cmdzero-investigation-results

***
Wait for a Command Zero investigation to reach a verdict, then write the outcome to the War Room as a note. This command polls and does not return until the investigation completes, fails, or the timeout elapses. It does not modify incident, alert, or investigation fields.

#### Base Command

`cmdzero-investigation-results`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| investigation_id | The investigation UUID to wait on. | Required |
| interval_in_seconds | Seconds between polls. Default is 60. | Optional |
| timeout_in_seconds | Seconds before polling gives up. Default is 3600. | Optional |
| post_note | Whether to write the investigation summary to the War Room as a note on completion. Set to false when a later cmdzero-investigation-note call will post a combined note that also covers the response action. Possible values are: true, false. Default is true. | Optional |
| third_party_actions | JSON array of response actions taken in your own stack, so the note covers the whole containment picture. Each entry may contain system, action, target, status, and reference. Example - [{"system":"ServiceNow","action":"Incident raised", "target":"user@company.com","status":"completed","reference":"INC0012345"}]. | Optional |
| response_disposition | Why no response action was taken, when none was. Used to make the note say "submitted for analysis only" rather than "the verdict did not qualify" - two materially different statements. Ignored when a response action is reported. Possible values are: investigate-only, not-qualifying. | Optional |
| related_remediations | JSON array of other Command Zero remediations already recorded against this investigation, listed in the note as context. Map from CommandZero.Remediation after running cmdzero-remediation-list with an investigation_id. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Investigation.id | String | Investigation unique identifier. |
| CommandZero.Investigation.status | String | Investigation status. |
| CommandZero.Investigation.completed | Boolean | True when verdict is ready. |
| CommandZero.Investigation.verdict | Unknown | Verdict labels. |
| CommandZero.Investigation.severity | String | Investigation severity. |
| CommandZero.Investigation.confidenceLevel | String | Confidence in the investigation findings. |
| CommandZero.Investigation.summary | String | Markdown findings summary. |
| CommandZero.Investigation.category | String | Investigation category. |
| CommandZero.Investigation.observables | Unknown | Observables discovered during investigation. |
| CommandZero.Investigation.consoleUrl | String | Direct link to the investigation in the console. |
| CommandZero.Investigation.completedTime | String | When the investigation completed. |

#### Command example

```!cmdzero-investigation-results investigation_id=f47ac10b-58cc-4372-a567-0e02b2c3d479 interval_in_seconds=30 timeout_in_seconds=600```

#### Human Readable Output

While the investigation is still running, the command reschedules itself and
reports progress:

>Waiting on Command Zero investigation f47ac10b-58cc-4372-a567-0e02b2c3d479 (status: investigating).

On completion it posts the summary note described in
[Investigation notes](#investigation-notes).

### cmdzero-investigation-note

***
Write a Command Zero investigation summary to the War Room as a note. Optionally includes the outcome of a response action, so the verdict and the action taken are recorded together. It does not modify incident, alert, or investigation fields.

#### Base Command

`cmdzero-investigation-note`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| investigation_id | The investigation UUID to summarize. | Required |
| response_action_outcome | Governance outcome of the response action. Map from CommandZero.Remediation.governanceOutcome. Possible values are: executed, blocked, conflict. | Optional |
| response_action_type | Name of the response action taken. Map from CommandZero.Remediation.templateName. | Optional |
| response_action_id | Remediation identifier. Map from CommandZero.Remediation.id. | Optional |
| response_action_status | Execution status of the remediation. Map from CommandZero.Remediation.status. | Optional |
| response_action_reason | Reason the action was blocked or conflicted. Map from CommandZero.Remediation.governanceReason. | Optional |
| rollback_template_id | Template that reverses the action. Map from CommandZero.Remediation.undoTemplateId. | Optional |
| third_party_actions | JSON array of response actions taken in your own stack, so the note covers the whole containment picture. Each entry may contain system, action, target, status, and reference. Example - [{"system":"ServiceNow","action":"Incident raised", "target":"user@company.com","status":"completed","reference":"INC0012345"}]. | Optional |
| response_disposition | Why no response action was taken, when none was. Used to make the note say "submitted for analysis only" rather than "the verdict did not qualify" - two materially different statements. Ignored when a response action is reported. Possible values are: investigate-only, not-qualifying. | Optional |
| related_remediations | JSON array of other Command Zero remediations already recorded against this investigation, listed in the note as context. Map from CommandZero.Remediation after running cmdzero-remediation-list with an investigation_id. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Investigation.id | String | Investigation unique identifier. |
| CommandZero.Investigation.verdict | Unknown | Verdict labels. |
| CommandZero.Investigation.severity | String | Investigation severity. |
| CommandZero.Investigation.confidenceLevel | String | Confidence in the investigation findings. |
| CommandZero.Investigation.summary | String | Markdown findings summary. |
| CommandZero.Investigation.consoleUrl | String | Direct link to the investigation in the console. |

#### Command example

```!cmdzero-investigation-note investigation_id=f47ac10b-58cc-4372-a567-0e02b2c3d479 response_action_outcome=executed response_action_type="Disable User" response_action_status=success rollback_template_id=r-6k81klf1p0mgf3 third_party_actions=`[{"system":"ServiceNow","action":"Incident raised","reference":"INC0012345","status":"completed"}]` ```

#### Human Readable Output

See [Investigation notes](#investigation-notes) for the note format, and
[Coordinating with your own response actions](#coordinating-with-your-own-response-actions)
for the `third_party_actions` shape.

### cmdzero-remediation-template-list

***
List available remediation templates for this organization.

#### Base Command

`cmdzero-remediation-template-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| limit | Maximum number of results to return. Default is 50. | Optional |
| next_token | Pagination cursor from a previous response. | Optional |
| subject_type | Filter by subject type (e.g. MICROSOFT_ENTRA_USER_PRINCIPAL_NAME). | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.RemediationTemplate.id | String | Template unique identifier. |
| CommandZero.RemediationTemplate.name | String | Full template name. |
| CommandZero.RemediationTemplate.displayName | String | Short display name for the action. |
| CommandZero.RemediationTemplate.description | String | What this remediation does. |
| CommandZero.RemediationTemplate.subjectType | String | The subject type this template operates on. |
| CommandZero.RemediationTemplate.undoTemplateId | String | Template ID to reverse this action. Empty if not reversible. |
| CommandZero.RemediationTemplate.createdTime | String | When the template was created. |
| CommandZero.RemediationTemplateNextToken | String | Pagination cursor for the next page of results. |

#### Command example

```!cmdzero-remediation-template-list limit=5 subject_type=MICROSOFT_ENTRA_USER_PRINCIPAL_NAME```

#### Human Readable Output

>### Command Zero Remediation Templates (1 results)
>
>|id|name|displayName|subjectType|undoTemplateId|
>|---|---|---|---|---|
>| r-39a26e0p32micg | Disable Microsoft Entra User by User Principal Name | Disable User | MICROSOFT_ENTRA_USER_PRINCIPAL_NAME | r-6k81klf1p0mgf3 |
>
### cmdzero-remediation-create

***
Execute a remediation action against a subject. The template must match the subject type. All native response actions are notify-only by default.

#### Base Command

`cmdzero-remediation-create`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| template_id | Remediation template ID. Use cmdzero-remediation-template-list to find available templates. | Required |
| subject_type | Subject type matching the template (e.g. MICROSOFT_ENTRA_USER_PRINCIPAL_NAME, CROWDSTRIKE_DEVICE_ID). | Required |
| subject_value | The target value (e.g. user@company.com or a device ID). | Required |
| justification | Reason for executing this remediation. Recorded in the Command Zero audit trail. | Required |
| investigation_id | The investigation this action responds to. Recorded in the justification as a correlation marker, which is the only way to find an action by investigation later - the API has no investigation field on a remediation. Strongly recommended. | Optional |
| postback_url | URL to receive notification when remediation completes. | Optional |
| postback_token | Secret token for postback verification. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Remediation.id | String | Remediation unique identifier. |
| CommandZero.Remediation.status | String | Remediation execution status. |
| CommandZero.Remediation.templateId | String | The template ID used. |
| CommandZero.Remediation.templateName | String | The template name at time of execution. |
| CommandZero.Remediation.subject | Unknown | The target subject of the remediation. |
| CommandZero.Remediation.justification | String | Justification provided when created. |
| CommandZero.Remediation.error | String | Error message if failed. Empty if no error. |
| CommandZero.Remediation.governanceOutcome | String | Outcome of the server-side governance evaluation. One of executed, blocked, or conflict. |
| CommandZero.Remediation.governanceHttpStatus | Number | HTTP status returned when governance declined the action. 403 for a policy block, 409 for a conflict. Absent when executed. |
| CommandZero.Remediation.governanceReason | String | Reason the action was blocked or conflicted. Absent when executed. |
| CommandZero.Remediation.traceId | String | Command Zero trace ID for the declined request. Quote this in support requests. |
| CommandZero.Remediation.rollbackAvailable | Boolean | True when this remediation can be reversed. |
| CommandZero.Remediation.undoTemplateId | String | Template ID that reverses this remediation. Empty when the action is not reversible. |
| CommandZero.Remediation.organizationId | String | Organization that owns this remediation. |
| CommandZero.Remediation.createdTime | String | When the remediation was created. |
| CommandZero.Remediation.updatedTime | String | When the remediation was last updated. |

#### Command example

```!cmdzero-remediation-create template_id=r-39a26e0p32micg subject_type=MICROSOFT_ENTRA_USER_PRINCIPAL_NAME subject_value=user@example.com justification="Confirmed credential compromise"```

#### Human Readable Output

When the action is permitted:

>### Command Zero Remediation Created
>
>|id|status|templateName|justification|rollbackAvailable|undoTemplateId|
>|---|---|---|---|---|---|
>| 8f14e45f-ceea-467f-a123-f6b2c3d4e5f6 | pending | Disable User | Confirmed credential compromise | true | r-6k81klf1p0mgf3 |

When governance declines the action, the command returns a **result, not an
error**, so a playbook can record the outcome and continue:

>### Command Zero Remediation Blocked
>
>|templateId|governanceOutcome|governanceHttpStatus|governanceReason|traceId|
>|---|---|---|---|---|
>| r-39a26e0p32micg | blocked | 403 | Automated response actions are not enabled for this action type. | abc123def456 |
>
### cmdzero-remediation-results

***
Wait for a Command Zero remediation to finish and report its outcome. Remediations are queued on creation, so cmdzero-remediation-create usually returns a pending status. Use this to wait for the real result. Most remediations complete within a minute.

#### Base Command

`cmdzero-remediation-results`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| remediation_id | The remediation ID to wait on. Map from CommandZero.Remediation.id. | Required |
| interval_in_seconds | Seconds between polls. Default is 15. | Optional |
| timeout_in_seconds | Seconds before polling gives up. Default is 600. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Remediation.id | String | Remediation unique identifier. |
| CommandZero.Remediation.status | String | Final remediation status. Known values are success, failed, not_found, unchanged, and interrupted. This is an open enumeration. |
| CommandZero.Remediation.templateName | String | The template name at time of execution. |
| CommandZero.Remediation.subject | Unknown | The target subject of the remediation. |
| CommandZero.Remediation.error | String | Error message if failed. Empty if no error. |
| CommandZero.Remediation.result | Unknown | Result of the remediation, when it succeeded. |
| CommandZero.Remediation.completedTime | String | When the remediation completed. |
| CommandZero.Remediation.consoleUrl | String | Direct link to the remediation in the console. |

#### Command example

```!cmdzero-remediation-results remediation_id=8f14e45f-ceea-467f-a123-f6b2c3d4e5f6```

#### Human Readable Output

While the remediation is still queued:

>Waiting on Command Zero remediation 8f14e45f-ceea-467f-a123-f6b2c3d4e5f6 (status: pending).

On completion:

>### Command Zero Remediation Completed
>
>|id|status|templateName|error|completedTime|
>|---|---|---|---|---|
>| 8f14e45f-ceea-467f-a123-f6b2c3d4e5f6 | success | Disable User |  | 2026-01-13T15:02:11Z |
>
### cmdzero-remediation-list

***
List remediations in the organization. Use investigation_id to find the actions recorded against a particular investigation.

#### Base Command

`cmdzero-remediation-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| investigation_id | Find remediations recorded against this investigation. Correlation relies on the marker that cmdzero-remediation-create writes into the justification, so actions raised directly in the Command Zero console will not be found. Cannot be combined with filter. | Optional |
| subject_type | Filter by subject type, for example MICROSOFT_ENTRA_USER_PRINCIPAL_NAME. Ignored when investigation_id or filter is supplied. | Optional |
| limit | Maximum number of items to return (1-10000). Default is 50. | Optional |
| filter | OData-style filter expression to narrow results. Supported fields are completedTime, createdTime, error, justification, organizationId, status, subjectType, templateId, updatedTime, createdBy/type, createdBy/id, createdBy/name, updatedBy/type, updatedBy/id, and updatedBy/name. | Optional |
| next_token | Pagination cursor from a previous response. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Remediation.id | String | Remediation unique identifier. |
| CommandZero.Remediation.templateId | String | The template ID used. |
| CommandZero.Remediation.templateName | String | The template name at time of execution. |
| CommandZero.Remediation.subject | Unknown | The target subject of the remediation. |
| CommandZero.Remediation.status | String | Remediation execution status. |
| CommandZero.Remediation.justification | String | Justification provided when created. |
| CommandZero.Remediation.error | String | Error message if failed. Empty if no error. |
| CommandZero.Remediation.createdTime | String | When the remediation was created. |
| CommandZero.Remediation.consoleUrl | String | Direct link to the remediation in the console. |
| CommandZero.RemediationNextToken | String | Pagination cursor for the next page of results. |

### cmdzero-investigation-template-list

***
List investigation templates available to the organization. Use this to find the template ID for a template-based investigation.

#### Base Command

`cmdzero-investigation-template-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| limit | Maximum number of items to return (1-10000). Default is 50. | Optional |
| filter | OData-style filter expression to narrow results. Supported fields are createdTime, description, name, scenario, sensitivity, severity, slidingDate, title, updatedTime, createdBy/type, createdBy/id, createdBy/name, updatedBy/type, updatedBy/id, and updatedBy/name. | Optional |
| next_token | Pagination cursor from a previous response. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.InvestigationTemplate.id | String | Template unique identifier. |
| CommandZero.InvestigationTemplate.name | String | Template name. |
| CommandZero.InvestigationTemplate.title | String | Default title applied to investigations from this template. |
| CommandZero.InvestigationTemplate.description | String | What this template investigates. |
| CommandZero.InvestigationTemplate.scenario | String | The scenario this template covers. |
| CommandZero.InvestigationTemplate.leadTypes | Unknown | Lead types this template accepts. Supply matching leads to cmdzero-investigation-create. |
| CommandZero.InvestigationTemplate.severity | String | Default severity for investigations from this template. |
| CommandZero.InvestigationTemplateNextToken | String | Pagination cursor for the next page of results. |

### cmdzero-catalog-type-list

***
List types in the Command Zero catalog. Use this to find valid type names when building an alert schema or a business context schema.

#### Base Command

`cmdzero-catalog-type-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| limit | Maximum number of items to return (1-10000). Default is 50. | Optional |
| filter | OData-style filter expression to narrow results. Supported fields are name, description, isAlert, createdTime, updatedTime, createdBy/type, createdBy/name, updatedBy/type, and updatedBy/name. | Optional |
| next_token | Pagination cursor from a previous response. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.CatalogType.id | String | Type unique identifier. |
| CommandZero.CatalogType.name | String | The type name to use in schema annotations, such as EMAIL_ADDRESS. |
| CommandZero.CatalogType.description | String | What this type represents. |
| CommandZero.CatalogType.isAlert | Boolean | True when this type identifies alert metadata. |
| CommandZero.CatalogType.examples | Unknown | Example values for this type. |
| CommandZero.CatalogType.fields | Unknown | Field structure for complex types. |
| CommandZero.CatalogTypeNextToken | String | Pagination cursor for the next page of results. |

### cmdzero-business-context-list

***
List business context uploads for the organization. Returns metadata such as name, status and record count, not the records themselves.

#### Base Command

`cmdzero-business-context-list`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| limit | Maximum number of items to return (1-10000). Default is 50. | Optional |
| filter | OData-style filter expression to narrow results. Supported fields are createdTime, description, name, organizationId, recordCount, status, subjectTypes, updatedTime, createdBy/type, createdBy/id, createdBy/name, updatedBy/type, updatedBy/id, and updatedBy/name. Records themselves are not searchable. | Optional |
| next_token | Pagination cursor from a previous response. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.BusinessContextUpload.id | String | Upload unique identifier. |
| CommandZero.BusinessContextUpload.name | String | Human-readable name for this upload. |
| CommandZero.BusinessContextUpload.status | String | Processing status. One of processing, ready, or failed. |
| CommandZero.BusinessContextUpload.recordCount | Number | Number of records in this upload. |
| CommandZero.BusinessContextUpload.subjectTypes | Unknown | Subject types identified in this upload. |
| CommandZero.BusinessContextUpload.updatedTime | String | When this upload was last updated. |
| CommandZero.BusinessContextUploadNextToken | String | Pagination cursor for the next page of results. |

#### Command example

```!cmdzero-business-context-list limit=5 filter="status eq 'ready'"```

#### Human Readable Output

>### Command Zero Business Context Uploads (1 results)
>
>|id|name|status|recordCount|subjectTypes|updatedTime|
>|---|---|---|---|---|---|
>| f47ac10b-58cc-4372-a567-0e02b2c3d479 | HR User Directory | ready | 1547 | EMAIL_ADDRESS | 2026-01-15T10:02:30Z |
>
### cmdzero-business-context-get

***
Retrieve a single business context upload by ID.

#### Base Command

`cmdzero-business-context-get`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| upload_id | The business context upload ID to retrieve. | Required |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.BusinessContextUpload.id | String | Upload unique identifier. |
| CommandZero.BusinessContextUpload.name | String | Human-readable name for this upload. |
| CommandZero.BusinessContextUpload.description | String | Description of this upload. |
| CommandZero.BusinessContextUpload.status | String | Processing status. One of processing, ready, or failed. Context is only applied to new investigations once the status is ready. |
| CommandZero.BusinessContextUpload.recordCount | Number | Number of records in this upload. |
| CommandZero.BusinessContextUpload.subjectTypes | Unknown | Subject types identified in this upload. |
| CommandZero.BusinessContextUpload.error | String | Error message if processing failed. Empty otherwise. |
| CommandZero.BusinessContextUpload.createdTime | String | When this upload was created. |
| CommandZero.BusinessContextUpload.updatedTime | String | When this upload was last updated. |

#### Command example

```!cmdzero-business-context-get upload_id=f47ac10b-58cc-4372-a567-0e02b2c3d479```

### cmdzero-business-context-upload

***
Upload business context to enrich investigations with information about subjects that cannot be discovered by querying IT systems. Processing is asynchronous; use cmdzero-business-context-results to wait for it.

#### Base Command

`cmdzero-business-context-upload`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| name | A descriptive name identifying the source system and data type, such as "HR User Directory" or "ServiceNow CMDB Servers". | Required |
| records | JSON array of objects holding your context data. Each object should contain at least one field that maps to a subject type in the schema. Example - [{"email":"user@company.com","department":"Engineering","vip":true}]. | Required |
| schema | JSON array of annotations mapping paths in your records to Command Zero catalog types. At least two annotations are required, and at least one must map to a subject type such as EMAIL_ADDRESS or HOST_NAME. Example - [{"path":"email","type":"EMAIL_ADDRESS"},{"path":"department","type":"TEXT"}]. | Required |
| description | Optional description providing additional context. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.BusinessContextUpload.id | String | Upload unique identifier. |
| CommandZero.BusinessContextUpload.name | String | Human-readable name for this upload. |
| CommandZero.BusinessContextUpload.description | String | Description of this upload. |
| CommandZero.BusinessContextUpload.status | String | Processing status. One of processing, ready, or failed. Context is only applied to new investigations once the status is ready. |
| CommandZero.BusinessContextUpload.recordCount | Number | Number of records in this upload. |
| CommandZero.BusinessContextUpload.subjectTypes | Unknown | Subject types identified in this upload. |
| CommandZero.BusinessContextUpload.error | String | Error message if processing failed. Empty otherwise. |
| CommandZero.BusinessContextUpload.createdTime | String | When this upload was created. |
| CommandZero.BusinessContextUpload.updatedTime | String | When this upload was last updated. |

#### Command example

```!cmdzero-business-context-upload name="HR User Directory" records=`[{"email":"user@company.com","department":"Engineering","vip":true}]` schema=`[{"path":"email","type":"EMAIL_ADDRESS"},{"path":"department","type":"TEXT"}]` description="Workday export"```

#### Human Readable Output

>### Command Zero Business Context Uploaded
>
>|id|name|status|recordCount|subjectTypes|error|
>|---|---|---|---|---|---|
>| f47ac10b-58cc-4372-a567-0e02b2c3d479 | HR User Directory | processing | 1 | EMAIL_ADDRESS |  |

The upload is not applied to investigations until its status is `ready`. Follow
with `cmdzero-business-context-results` to wait.

### cmdzero-business-context-replace

***
Replace an existing business context upload. This completely replaces the previous records - it does not merge with existing data. Supply records and schema together to replace the data, or only name and description to update the metadata. The previous version stays active until the new one finishes processing.

#### Base Command

`cmdzero-business-context-replace`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| upload_id | The business context upload ID to replace. | Required |
| records | JSON array of objects holding your context data. Each object should contain at least one field that maps to a subject type in the schema. Example - [{"email":"user@company.com","department":"Engineering","vip":true}]. | Optional |
| schema | JSON array of annotations mapping paths in your records to Command Zero catalog types. At least two annotations are required, and at least one must map to a subject type such as EMAIL_ADDRESS or HOST_NAME. Example - [{"path":"email","type":"EMAIL_ADDRESS"},{"path":"department","type":"TEXT"}]. | Optional |
| name | Updated name. The existing name is kept if omitted. | Optional |
| description | Updated description. The existing description is kept if omitted. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.BusinessContextUpload.id | String | Upload unique identifier. |
| CommandZero.BusinessContextUpload.name | String | Human-readable name for this upload. |
| CommandZero.BusinessContextUpload.description | String | Description of this upload. |
| CommandZero.BusinessContextUpload.status | String | Processing status. One of processing, ready, or failed. Context is only applied to new investigations once the status is ready. |
| CommandZero.BusinessContextUpload.recordCount | Number | Number of records in this upload. |
| CommandZero.BusinessContextUpload.subjectTypes | Unknown | Subject types identified in this upload. |
| CommandZero.BusinessContextUpload.error | String | Error message if processing failed. Empty otherwise. |
| CommandZero.BusinessContextUpload.createdTime | String | When this upload was created. |
| CommandZero.BusinessContextUpload.updatedTime | String | When this upload was last updated. |

#### Command example

```!cmdzero-business-context-replace upload_id=f47ac10b-58cc-4372-a567-0e02b2c3d479 records=`[{"email":"user@company.com","department":"Platform"}]` schema=`[{"path":"email","type":"EMAIL_ADDRESS"},{"path":"department","type":"TEXT"}]` ```

Renaming without resubmitting the records is also allowed:

```!cmdzero-business-context-replace upload_id=f47ac10b-58cc-4372-a567-0e02b2c3d479 description="Refreshed nightly"```

### cmdzero-business-context-delete

***
Permanently delete a business context upload and all its records. This cannot be undone. Investigations that already ran keep the context they had; new investigations will not see it.

#### Base Command

`cmdzero-business-context-delete`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| upload_id | The business context upload ID to delete. | Required |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.BusinessContextUpload.id | String | The deleted upload ID. |
| CommandZero.BusinessContextUpload.deleted | Boolean | True when the upload was deleted. |

#### Command example

```!cmdzero-business-context-delete upload_id=f47ac10b-58cc-4372-a567-0e02b2c3d479```

#### Human Readable Output

>Business context upload f47ac10b-58cc-4372-a567-0e02b2c3d479 deleted. Investigations that already ran keep the context they had; new investigations will not see it.
>
### cmdzero-business-context-results

***
Wait for a business context upload to finish processing. Context is only applied to new investigations once the upload is ready, so a sync that reports success on upload alone reports too early. Large uploads may take several minutes.

#### Base Command

`cmdzero-business-context-results`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| upload_id | The business context upload ID to wait on. Map from CommandZero.BusinessContextUpload.id. | Required |
| interval_in_seconds | Seconds between polls. Default is 30. | Optional |
| timeout_in_seconds | Seconds before polling gives up. Default is 1800. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.BusinessContextUpload.id | String | Upload unique identifier. |
| CommandZero.BusinessContextUpload.name | String | Human-readable name for this upload. |
| CommandZero.BusinessContextUpload.description | String | Description of this upload. |
| CommandZero.BusinessContextUpload.status | String | Processing status. One of processing, ready, or failed. Context is only applied to new investigations once the status is ready. |
| CommandZero.BusinessContextUpload.recordCount | Number | Number of records in this upload. |
| CommandZero.BusinessContextUpload.subjectTypes | Unknown | Subject types identified in this upload. |
| CommandZero.BusinessContextUpload.error | String | Error message if processing failed. Empty otherwise. |
| CommandZero.BusinessContextUpload.createdTime | String | When this upload was created. |
| CommandZero.BusinessContextUpload.updatedTime | String | When this upload was last updated. |

#### Command example

```!cmdzero-business-context-results upload_id=f47ac10b-58cc-4372-a567-0e02b2c3d479```

#### Human Readable Output

While processing:

>Waiting on Command Zero business context upload f47ac10b-58cc-4372-a567-0e02b2c3d479 (status: processing).

On completion:

>### Command Zero Business Context Upload Ready
>
>|id|name|status|recordCount|subjectTypes|error|
>|---|---|---|---|---|---|
>| f47ac10b-58cc-4372-a567-0e02b2c3d479 | HR User Directory | ready | 1547 | EMAIL_ADDRESS |  |
>
### cmdzero-investigation-create

***
Create a Command Zero investigation from alert data or a template. Alert submissions take one of three forms: (1) alert_type + alert_data, where Command Zero resolves the schema from the alert type - title and description are both required; (2) alert_type + alert_data + alert_schema as a JSON array of annotations, where you map your own data shape; (3) alert_data + alert_schema as a known catalog type string, where the payload must already match that catalog entry - alert_type must not be set. Alternatively use template_id with leads. Use cmdzero-investigation-results to wait for the verdict.

#### Base Command

`cmdzero-investigation-create`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| alert_data | JSON object containing the alert data to investigate. Required when not using template_id. | Optional |
| alert_type | The kind of alert this is, for example EmailMalwareDetected. Required when alert_schema is omitted, and when alert_schema is a JSON array of annotations. Must NOT be set when alert_schema is a catalog type string, because the catalog entry already defines it. | Optional |
| alert_schema | Either a JSON array of path/type annotations describing where the values are in your own data (e.g. [{"path":"sender.email","type":"EMAIL_ADDRESS"}]), or a known catalog type string (e.g. RECORDED_FUTURE_PLAYBOOK_ALERT). Use the catalog type only when the payload still matches that entry's expected shape; if the data has been reshaped on its way here, supply annotations instead. Use cmdzero-catalog-type-list to find valid type names. | Optional |
| description | Detailed description of the investigation. Required when submitting alert_type and alert_data without an alert_schema. Otherwise defaults to the alert description. | Optional |
| category | Category of the investigation, such as Phishing, Malware, or Credential Compromise. | Optional |
| tags | JSON array of tags to apply to the investigation. Example - ["urgent","vip-user"]. | Optional |
| nosettle | Prevents automated report generation and settlement notifications when the investigation completes. Use when exercising the integration rather than running a real investigation. Possible values are: true, false. Default is false. | Optional |
| template_id | Investigation template ID for template-based investigations. Use instead of alert_data and alert_schema. | Optional |
| leads | JSON array of lead objects when using template_id. Example - [{"type":"EMAIL_ADDRESS","value":"user@company.com"}]. | Optional |
| title | Investigation title. Optional override. | Optional |
| start_time | ISO 8601 start time for template investigations. | Optional |
| end_time | ISO 8601 end time for template investigations. | Optional |
| postback_url | URL to receive notification when investigation completes. | Optional |
| postback_token | Secret token for postback verification. | Optional |

#### Context Output

| **Path** | **Type** | **Description** |
| --- | --- | --- |
| CommandZero.Investigation.id | String | Investigation unique identifier. |
| CommandZero.Investigation.action | String | Whether a new investigation was started or the alert was merged into an existing one. One of created or merged. |
| CommandZero.Investigation.title | String | Investigation title. |
| CommandZero.Investigation.status | String | Investigation status. |
| CommandZero.Investigation.severity | String | Investigation severity. |
| CommandZero.Investigation.category | String | Investigation category. |
| CommandZero.Investigation.completed | Boolean | True when verdict is ready. |
| CommandZero.Investigation.consoleUrl | String | Direct link to the investigation in the console. |
| CommandZero.Investigation.investigationUrl | String | API URL to retrieve investigation status and results. |
| CommandZero.Investigation.organizationId | String | Organization that owns this investigation. |
| CommandZero.Investigation.createdTime | String | When the investigation was created. |

#### Command example

```!cmdzero-investigation-create alert_type=EmailMalwareDetected alert_data=`{"alert_title":"Malicious file attached to email","sender":{"email":"attacker@example.com"}}` alert_schema=`[{"path":"alert_title","type":"ALERT_TITLE"},{"path":"sender.email","type":"EMAIL_ADDRESS"}]` title="Malicious file detected in email"```

See [Submitting an alert: the three forms](#submitting-an-alert-the-three-forms)
before choosing between a catalog type and annotations.

#### Human Readable Output

>### Command Zero Investigation Created
>
>|id|action|title|status|severity|consoleUrl|
>|---|---|---|---|---|---|
>| f47ac10b-58cc-4372-a567-0e02b2c3d479 | created | Malicious file detected in email | investigating | high | https://ui.cmdzero.io/... |

When Command Zero merges the alert into an existing investigation, `action` is
`merged` and the existing investigation ID is returned. Branch on `action` when
a playbook needs to distinguish the two.

## Investigation notes

On completion, the integration writes a note to the War Room containing the
investigation ID, verdict labels, severity, confidence level, status, category,
the findings summary, the observables, and a link to the investigation in the
Command Zero console. When a response action was attempted, the same note
records what happened to it and whether a rollback is available.

A failed investigation, a blocked response action, or a conflicting response
action is raised to a warning entry so it stands out in the War Room.

If no response action was recorded, the note says so explicitly rather than
leaving it to inference — and says *why*. An alert submitted for analysis only
and an investigation whose verdict did not qualify are different statements, and
the note distinguishes them via the `response_disposition` argument. The
supplied playbooks set this for you.

Each phrasing is scoped to what this integration did. The connector reports the
actions it requested; it does not speak for anything Command Zero may evaluate
internally.

## Response action governance

Response action governance is enforced by Command Zero, not by this
integration. `cmdzero-remediation-create` reports the outcome and does not
attempt to work around a decision:

| Outcome | Meaning | Playbook behaviour |
| --- | --- | --- |
| `executed` | The action was accepted and is running. | Continue. |
| `blocked` | A governance policy refused the action (HTTP 403). | Returned as a result, not an error. Record and continue. |
| `conflict` | The action conflicts with another (HTTP 409). | Returned as a result, not an error. Record and continue. |

Any other failure is raised as an error in the usual way.

### Waiting for a response action to finish

Remediations are **queued on creation**, so `cmdzero-remediation-create`
normally returns a status of `pending`. To report the real outcome rather than
`pending`, follow it with `cmdzero-remediation-results`, which polls until the
remediation reaches a final state. Most complete within a minute; the command
polls every 15 seconds and gives up after 10 minutes by default.

The supplied playbooks already do this, and skip the wait when governance
declined the action — a blocked or conflicting action produces no remediation
to wait for.

`status` is an open enumeration. Known values are `success`, `failed`,
`not_found`, `unchanged` (the subject was already in the desired state), and
`interrupted`. Any unrecognised value is treated as final rather than polled
until timeout.

## Playbooks

| Playbook | Purpose |
| --- | --- |
| **Command Zero - Investigate Alert** | Submits an alert, waits for the verdict, posts the note. No response action is requested. |
| **Command Zero - Investigate and Respond** | As above, and on a qualifying verdict executes a native response action, then posts one note covering the verdict and the action. |
| **Command Zero - Coordinated Response** | A template that adds a hand-off to your own containment tasks, and reports Command Zero's action and your stack's actions in a single note. Copy it before editing. |
| **Command Zero - Sync Business Context** | Pushes business context into Command Zero, replacing the previous upload rather than duplicating it. Run it as a scheduled job. |

`Command Zero - Investigate and Respond` decides whether to respond by checking
whether the `ActionableVerdict` input appears among the investigation's verdict
labels. Command Zero returns `verdict` as an array, so this is a membership
test, not an equality test. Set `RemediationTemplateId` to enable the response
path; leave it empty to post the verdict only.

## Coordinating with your own response actions

Command Zero's verdict can drive containment in your own stack as well as its
own native actions. The integration polls for the verdict, so the playbook that
started the investigation is still running when the verdict lands and can simply
continue into your containment tasks — nothing needs to call into Cortex from
outside, and no inbound connectivity is required.

There are two ways to wire this up.

**Use the template.** Copy `Command Zero - Coordinated Response`, find the task
marked **ADD YOUR CONTAINMENT TASKS HERE**, and insert your own tasks or
sub-playbook after it. Have them write their outcomes to the context key
`ThirdPartyActions`.

**Or drive it yourself.** If you already have orchestration, call
`Command Zero - Investigate and Respond` as a sub-playbook — it returns the
investigation and any native action in context — then post the note yourself
with `cmdzero-investigation-note`.

Either way, actions taken in your stack are reported by passing them to
`third_party_actions` as a JSON array:

```json
[
  {
    "system": "ServiceNow",
    "action": "Incident raised",
    "target": "user@company.com",
    "status": "completed",
    "reference": "INC0012345"
  },
  {
    "system": "CrowdStrike",
    "action": "Host contained",
    "target": "LAPTOP-4417",
    "status": "failed",
    "reference": "job-889"
  }
]
```

All five fields are optional; supply what you have. The note lists these
alongside Command Zero's own action and labels them as executed by the SOAR, so
the audit record stays unambiguous about which platform did what. If any entry
has a status of `failed`, `error`, `blocked`, `pending review`, or `not found`,
the note is raised to a warning entry.

## Terminology

Three vocabularies meet in this integration, and one word means different things
in each. Worth fixing in your head before wiring anything up.

| | Cortex calls it | Command Zero calls it |
| --- | --- | --- |
| The case you are working | an **incident** on Cortex XSOAR, an **alert** on Cortex XSIAM 2.x, an **issue** on XSIAM 3.x | — |
| The detection you submit for analysis | — | an **alert** |
| The analysis and its verdict | — | an **investigation** |

**Every `alert_*` argument in this integration means a Command Zero alert**, not
a Cortex one: `alert_data` is the payload you want investigated, not the case it
came from.

This integration never reads or writes the surrounding case. It does not know
whether it is running on an incident, an alert or an issue, and it does not set
any field on one. **You decide what to submit** by mapping it into `alert_data`;
findings come back as a War Room note.

### What to map into `alert_data`

This is the same decision as
[the catalog type versus annotations choice](#choosing-between-a-catalog-type-and-annotations),
approached from the other end:

- **The original payload, untouched** — on Cortex XSOAR the incident's
  `rawJSON` usually holds it, where the case came from a fetching integration.
  This is the case where naming a **catalog type** is correct.
- **Fields Cortex has mapped, or an object your playbook assembled** — this is
  reshaped data, so describe it with **annotations**.

If you are not certain which you have, you have the second one. Use annotations.

## Submitting an alert: the three forms

Command Zero has to know two things about an alert — **what kind of alert it is**
and **where the important values are inside it**. The three submission forms are
three ways of answering those questions, and choosing the wrong one is the most
likely cause of an investigation that runs but finds nothing useful.

### Form 1 — `alert_type` + `alert_data`

Command Zero resolves the schema from the alert type. Use this when it already
understands the type you are naming.

`title` and `description` are **both required** in this form.

```
!cmdzero-investigation-create alert_type=EmailMalwareDetected alert_data=`{...}` title="..." description="..."
```

### Form 2 — `alert_type` + `alert_data` + `alert_schema` as annotations

You say where the values are, in *your* data's shape. **`alert_type` is still
required** — the annotations describe layout, not what kind of alert it is.

```
!cmdzero-investigation-create alert_type=EmailMalwareDetected alert_data=`{...}` alert_schema=`[{"path":"sender.email","type":"EMAIL_ADDRESS"}]`
```

### Form 3 — `alert_data` + `alert_schema` as a catalog type

The schema is a name Command Zero already holds, such as
`RECORDED_FUTURE_PLAYBOOK_ALERT`. **`alert_type` must not be set** — the catalog
entry already defines it.

```
!cmdzero-investigation-create alert_data=`{...}` alert_schema=RECORDED_FUTURE_PLAYBOOK_ALERT
```

### Choosing between a catalog type and annotations

This is the decision that matters, and it turns on one question: **has the alert
been reshaped on its way here?**

A catalog type is a claim that your payload has the shape Command Zero expects
for that alert source. That holds for a **raw** vendor alert. It often stops
holding by the time an alert reaches a playbook, because a classifier, a mapper,
or an upstream playbook has renamed, flattened or dropped fields.

If the shape has changed and you still name a catalog type, the submission is
accepted — but the paths that entry expects no longer resolve, so observables
are extracted incompletely or not at all. **The failure is quiet**: you get an
investigation with less to work from, not an error.

So:

- **Passing the original, untouched alert** — a raw payload kept on the incident,
  for example — a catalog type is correct and the least work.
- **Passing anything Cortex has mapped or assembled** — use annotations. They
  describe your shape, so it does not matter what changed.

When in doubt, annotations are the safer choice: they are explicit about where
every value lives, and they keep working when the upstream mapping changes.

Use `cmdzero-catalog-type-list` to find valid type names for the `type` field in
your annotations, and to see which catalog entries exist.

## Business context

Business context tells Command Zero what it cannot discover by querying your
systems — which users are executives, which hosts are in PCI scope, who owns
what. Command Zero applies it automatically when investigating a subject the
context covers; there is nothing to call at investigation time.

Getting it there is a sync, and `Command Zero - Sync Business Context` does it
idempotently: it looks for an upload with the same name, replaces it if found,
and creates it only on the first run. Run it as a scheduled job and you keep one
upload that stays current instead of accumulating a new one every night.

Four things to know before you build a sync:

- **A replace is a full replacement, not a merge.** Supply the complete record
  set every run. Anything you leave out is gone.
- **The upload name is the sync key.** Keep it stable across runs, and avoid
  apostrophes — they break the lookup filter.
- **Processing is asynchronous, and context is not applied until it is ready.**
  A sync that stops at the upload call has reported success too early. Use
  `cmdzero-business-context-results` to wait; the supplied playbook does.
  During a replace, the previous version stays active until the new one is
  ready, so there is no window where context disappears.
- **Changes only affect future investigations.** Investigations that already ran
  keep the context they had. The same is true of deletion.

Your schema needs at least two annotations, at least one of which maps to a
subject type such as `EMAIL_ADDRESS` or `HOST_NAME` — that is what ties each
record to the subject it describes:

```json
[
  {"path": "email", "type": "EMAIL_ADDRESS"},
  {"path": "department", "type": "TEXT"},
  {"path": "vip", "type": "TEXT"}
]
```

Records themselves are never searchable through the API. You can filter uploads
by metadata — name, status, record count — but not by what is inside them.

> **Watchlists and Exclusions are not yet available in the Command Zero API.**
> When they are, they belong alongside this. Until then, business context is the
> only context type this pack can synchronise, and the pre-investigation
> Exclusion check described in the product documentation is not something this
> integration can apply.

## Finding actions taken on an investigation

The Command Zero API gives a remediation no reference to the investigation that
motivated it, and `listRemediations` has no investigation filter. `justification`
*is* filterable, so `cmdzero-remediation-create` writes a correlation marker
there when you pass `investigation_id`, and `cmdzero-remediation-list` can then
find those actions with `investigation_id`.

**Pass `investigation_id` whenever you run a response action.** Without it the
action cannot be traced back to its investigation later.

The correlation is only as good as the convention: actions raised directly in
the Command Zero console carry no marker and will not be found. The note says so
wherever it lists them, so nobody reads an empty result as "nothing happened".

## Polling and rate limits

`cmdzero-investigation-results` polls rather than waiting on an inbound
callback, so no inbound connectivity to Cortex is required. Tune
`interval_in_seconds` and `timeout_in_seconds` to the investigation times you
expect; the defaults are 60 seconds and 1 hour.

The integration retries automatically on rate limiting (HTTP 429) and transient
server errors, honouring the `Retry-After` header when Command Zero sends one.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Test fails with an authorization error | The API key is invalid or expired, or was not issued to an application with the Application role. |
| Test reports the key cannot reach the configured organization | The key is valid but has no grants on that organization. The test message lists the organizations it can reach; copy the correct UUID into **Organization ID**. |
| Commands fail with a permission error after a passing test | The key's grants changed after setup. Re-run the test to confirm. |
| `cmdzero-investigation-results` times out | The investigation is still running. Raise `timeout_in_seconds`, or check the investigation in the Command Zero console. |
| A response action never executes | Governance declined it. Check `governanceOutcome` and `governanceReason` in the context or the War Room note, and quote `traceId` to Command Zero support. |
