# Security Policy

Asset Assistant is currently in pre-alpha development. Security reports are welcome.

## Supported versions

There is not yet a stable, security-supported release branch. The actively developed code is reviewed on a best-effort basis; no fixed response or remediation timeline is promised.

## Reporting a vulnerability

**Do not publish a working exploit, credentials, or sensitive details in a public GitHub issue.**

Use the repository's **Security** tab and **Report a vulnerability** option if private vulnerability reporting is enabled. If it is unavailable, open a public issue containing **only a non-sensitive request for a private reporting channel**; do not include exploit details.

When a private channel is available, provide:
- A concise description and potential impact.
- Affected version, commit, and environment.
- Reproduction steps or proof of concept, shared privately.
- Any suggested mitigation.

Reports are assessed as maintainer capacity allows. Please allow time for investigation before public disclosure.

## Scope

Potential issues include unsafe file handling, command execution, untrusted project inputs, dependency vulnerabilities, and unsafe export or import behavior. Ordinary functional bugs belong in the public bug-report template.
