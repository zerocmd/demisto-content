# Command Zero

Command Zero runs automated security investigations. This content pack lets
Cortex send alerts to Command Zero for investigation, wait for an evidenced
verdict, and act on the result — either by recording the findings for an analyst
or by executing a native Command Zero response action.

The usual SOAR pattern is `alert → playbook → response`. This pack supports
`alert → investigation → verdict → response`, so automated response follows a
completed investigation rather than a single alert.

## What you get

| Content | Purpose |
| --- | --- |
| **Command Zero** integration | Submit alerts, poll for verdicts, write findings to the War Room, run native response actions. |
| **Command Zero - Investigate Alert** playbook | Submit, wait for the verdict, post the findings. No response action is evaluated. |
| **Command Zero - Investigate and Respond** playbook | As above, plus a native response action on a qualifying verdict, reported in the same note. |
| **Command Zero - Coordinated Response** playbook | A template that hands off to your own containment tasks and reports Command Zero's action and your stack's actions in one note. |
| **Command Zero - Sync Business Context** playbook | Pushes business context into Command Zero on a schedule, replacing the previous upload rather than duplicating it. |

## A note on terminology

Command Zero calls the thing you submit an **alert**, and the analysis it
produces an **investigation**. Cortex calls the case you work an **incident** on
XSOAR, an **alert** on XSIAM 2.x, and an **issue** on XSIAM 3.x.

The word "alert" therefore means different things on each side. **Everywhere
this pack says "alert" it means the Command Zero one** — the detection you
submit, not the case it came from.

The pack never reads or writes the surrounding case. You choose what to submit
by mapping it into the playbook's `AlertData` input, and the findings come back
as a War Room note.

## How findings are recorded

Investigation outcomes are written to the **War Room as notes**. This pack does
**not** set incident, alert, or investigation fields. Severity, status,
confidence and ownership stay under the analyst's control — Command Zero's
verdict informs the decision without silently changing the case.

Each note carries the investigation ID, verdict labels, severity, confidence
level, status, category, the findings summary, the observables, and a link to
the investigation in the Command Zero console. When a response action was
attempted, the note records what happened to it and whether it can be rolled
back. Failed investigations and declined response actions are raised to warning
entries so they stand out.

## Response actions stay governed by Command Zero

Native response actions are requested through Command Zero, which enforces its
own governance server-side. This pack reports the decision and never attempts to
work around it: an action that is blocked by policy or that conflicts with
another action is returned as a recorded outcome rather than a failure, so a
playbook can log it and carry on. Where an action is reversible, the rollback
handle is surfaced alongside it.

## Containment across both platforms

A Command Zero verdict can drive containment in your own stack as well as
Command Zero's native actions — ticketing, on-call notification, network-layer
response. Because the integration polls for the verdict, the playbook that
started the investigation is still running when the verdict arrives and simply
continues into your own tasks. **Nothing has to call inbound into Cortex**, and
no firewall change is needed.

Copy **Command Zero - Coordinated Response** and insert your containment tasks
at the marked hand-off point, or call **Command Zero - Investigate and Respond**
as a sub-playbook from orchestration you already have. Either way, actions your
stack takes are reported in the same War Room note as Command Zero's own, each
labelled with the platform that performed it.

## Enriching investigations with what you already know

Command Zero investigates better when it knows which users are executives, which
hosts are in PCI scope, and who owns what — things it cannot discover by querying
your systems. This pack can push that context from Cortex into Command Zero,
where it is applied automatically to any investigation touching a subject the
context covers.

**Command Zero - Sync Business Context** does it idempotently: it replaces the
existing upload rather than adding another, so a nightly job keeps one upload
current instead of accumulating hundreds. Records can come from anywhere you can
reach in Cortex — a list, a CMDB integration, an HR export.

A replace is a full replacement rather than a merge, so supply the complete set
each run. The previous version stays live until the new one finishes processing,
so context never disappears mid-sync.

Watchlists and Exclusions are not yet available in the Command Zero API. When
they are, they will be synchronised the same way.

## Before you start

You will need:

- A Command Zero tenant.
- An application configured by your Command Zero administrators with the
  **Application** role, and an API key issued to it. Keys begin with `c0.`.
- The UUID of the organization the instance should work against, shown in the
  Command Zero console alongside the API key.
- Outbound HTTPS from Cortex to the Command Zero API. **No inbound
  connectivity to Cortex is required** — the integration polls for results
  rather than waiting on a callback.

An API key may be granted access to more than one organization. The pack never
infers which one you mean: you name it explicitly, and the Test button confirms
the key can reach it. If you work across several organizations, configure one
instance per organization and target them from playbooks by instance name.

## Configuration checklist

1. Install this pack, from the marketplace or by uploading the pack archive.
2. Go to **Settings** > **Integrations** > **Servers & Services** and search for
   **Command Zero**.
3. Add an instance and enter the **API Key**. Leave **Base URL** at its default
   unless Command Zero support has directed you elsewhere.
4. Enter the **Organization ID**, copied from the Command Zero console.
5. Click **Test**. It verifies that the API is reachable, that the key is
   valid, and that the key has access to the organization you named. If the key
   cannot reach it, the message lists the organizations it can reach. No
   investigation is started.
6. Run `!cmdzero-remediation-template-list` to see which response actions your
   tenant offers, and note the `id` of any you intend to automate.
7. Add **Command Zero - Investigate Alert** to an incident type, or call it as a
   sub-playbook, mapping your alert fields to its `AlertData` and `AlertSchema`
   inputs.
8. To automate response, use **Command Zero - Investigate and Respond** instead
   and set `RemediationTemplateId`, `RemediationSubjectType`, and
   `RemediationSubjectValue`. Leave `RemediationTemplateId` empty to record the
   verdict without acting on it.

## Manual installation

If you are installing before the pack is available in your marketplace, or in an
environment without marketplace access:

1. Obtain the pack archive (`CommandZero.zip`) from Command Zero.
2. In Cortex, go to **Marketplace**.
3. Select **Upload content pack** — on some versions this sits behind the menu
   in the upper-right of the Marketplace page.
4. Upload the archive and confirm the installation.
5. Follow the configuration checklist above.

Manually installed packs do not update automatically. To upgrade, repeat the
upload with a newer archive.

## API schema version

This pack targets Command Zero public API schema version **2026-03-12**. The
targeted version is also shown in the integration description in the
configuration screen. If your tenant reports a different schema version, review
this pack's release notes before upgrading.

## Support

This pack is developed and supported by Command Zero.

- Email: support@cmdzero.io
- Web: https://cmdzero.io

When raising an issue, include the `traceId` shown in the War Room note or
command output — it lets Command Zero locate the relevant logs directly.
