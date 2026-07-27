# Public release procedure

Never publish the working repository or reuse its Git history. Create a
source-only snapshot and publish that snapshot as a new repository instead:

```powershell
.\tools\check_public_release.ps1
```

The command runs secret scanning, public-safety scanning (including
requirements), forbidden tracked-file checks, unit tests, and the memory
benchmark. It then builds `dist/public/` from Git-tracked source files only
and repeats the secret and public-safety scans on the snapshot. Runtime
databases, exports, backups, attachments, `.env`, logs, and local
configuration files are excluded.

## Local redaction rules

Create a git-ignored `.private_terms` file when an additional private term must
be removed from the public snapshot. Use one rule per line:

```text
private-term=Synthetic replacement
```

The file is read only while building the snapshot. It is never copied into the
snapshot or added to Git. The public-safety scanner also uses the left-hand
term to detect accidental occurrences in tracked files.

`PUBLIC READY WITH MANUAL CHECK` means every automatic check passed. Inspect
the snapshot once more, then publish its contents as a new repository with a
new initial commit. Do not reuse Git history from the private working
repository.

## GitHub Actions mirror

The private repository contains a manually triggered workflow named **Publish
Public Mirror**. It never runs on a normal push, pull request, or schedule.
Before its first non-dry run, create an environment named `public-release` and
set `PUBLIC_REPO_TOKEN` there. Use a fine-grained GitHub token limited to the
public mirror repository with only **Contents: Read and write** and **Metadata:
Read** permissions.

The workflow validates the target repository identity and visibility, runs all
release gates, uploads only `dist/public` as an artifact, and then creates a
new `master` history (or synchronizes it) using the generated snapshot. The
token is supplied through a job-local `GIT_ASKPASS` helper; it is never stored
in a remote URL, Git configuration, source, snapshot, or log command. A
dry-run verifies the token, target repository, and mirror diff, but never
creates a commit or pushes.
