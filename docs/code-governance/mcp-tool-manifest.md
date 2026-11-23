# MCP Tool Manifest

Status: Draft for human review  
Date: 2026-11-21  
Owner: D  
Reviewer: B  
Related: `docs/architecture/permission-model.md`, `.opencode/permissions.jsonc`,
`AGENTS.md`

## Purpose and scope

This document is the authoritative allow-list for Model Context Protocol (MCP)
tools in this repository. It complements the path-based permission model with a
capability-based control: a path may be whitelisted while every MCP tool that
could act on it stays disabled.

The default is deny. All MCP tools are disabled unless a row in the allowed-tools
table below explicitly enables a tool for a named role with a stated scope and
justification. Absence of a tool from the table means it is disabled.

## Default

- ALL MCP tools are disabled by default (default deny).
- No agent role, including D, may invoke an MCP tool absent an approved entry in
  this manifest.
- A tool being installed, discoverable, or available in a client does not
  constitute approval to use it.

## Current state

No MCP servers or MCP tools are configured or enabled in this checkout. Nothing
in this document should be read as claiming that an MCP integration exists.

## Allowed tools

| Role / principal | Tool | Scope | Justification |
| --- | --- | --- | --- |
| All roles (A, B, C, D, E) and the generic coding agent | None currently needed | — | No MCP tool is required for any current task, including D's deterministic-guard work. All work is achievable with local file, search, shell, and test tooling. |

Explicit statement: **no MCP tool is currently enabled for any role.** The
allowed-tools set is empty.

## Change control

Enabling any MCP tool requires all of the following, in order:

1. **Human approval** — explicit human authorization for the specific tool and
   role; agents never self-approve.
2. **Role scoping** — the entry names the role(s) permitted to use the tool and
   states the concrete scope (paths, operations, and resources) it may touch,
   following least privilege.
3. **Manifest entry** — the tool, role, scope, and justification are added to the
   allowed-tools table in this document before first use, with the document's
   status updated through the normal shared-doc approval process.
4. **Policy sync** — the change is reconciled with the course policy source
   `.opencode/permissions.jsonc` (not auto-loaded) and the enforced live
   `opencode.jsonc` (owner E; currently absent from this checkout), under
   `check_permission_sync`.
5. **Recorded review conditions** — a review trigger and a revocation procedure
   are recorded for the tool.

## Revocation and review

- Any enabled tool is revoked immediately if its scope is exceeded, its
  justification no longer holds, or a permission-sync mismatch is found.
- Revocation is performed by a human and requires the manifest and the policy
  source to be updated together.
- This manifest is reviewed whenever the permission model, the live
  `opencode.jsonc`, or the policy source changes.

## References

- `docs/architecture/permission-model.md` — principals, tiers, default deny,
  overlap rule, and the `check_permission_sync` item.
- `.opencode/permissions.jsonc` — course policy source (not auto-loaded).
- `AGENTS.md` — access table and config-loading note.
