# Build staging repair — 17 October 2026

The user requested a fix after the morning candidate rendered successfully but
`build.py --incremental` exited with `OSError: [Errno 39] Directory not empty`
while removing its temporary sibling directory. No public promotion followed.

The affected environment synchronises the workspace in the background. A full
candidate tree reappeared at the former staging location after its `docs` had
already been moved to the checkout. Workspace-local disposable trees are exposed
to that synchronisation race; suppressing cleanup errors would hide the failure.

`build.py` now stages in the system temporary directory when it is on the same
filesystem as the checkout. It retains the sibling fallback for separate mounts,
so atomic `os.replace` promotion and rollback remain valid. The portal snapshot
helper uses the same placement rule, retaining its publication/Wire lock.

Regression coverage checks isolation from a simulated synchronised workspace,
same-filesystem promotion, build rollback, portal rollback and unchanged Wire.
The isolation test was observed failing before the fix. Full candidate checks
remain required; no gate is removed or downgraded. Existing publications, source
and quote times, UI, schedules and task states are preserved (DEC-013/014/015).

Implementation, CI, main and Pages status are reported separately in the change
and publication records. A successful local build alone is not live publication.
