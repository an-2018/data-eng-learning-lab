# Operations and release runbook

## Deployment boundary

Run the application, database, queue, artifact store, and worker services on an EU-hosted Linux environment. Put the API and web services behind TLS. Keep PostgreSQL, Redis, object storage, and the Docker socket on private networks. Only the worker that provisions learner sandboxes receives the Docker socket.

The worker must set `SANDBOX_RUNTIME=runsc` and the host must have a working gVisor installation. `runc` is permitted only for local development and compatibility checks. Learner containers run as an unprivileged user with no network, a read-only root filesystem, CPU, memory, process, disk, output, and time limits. Trusted grading stays in the worker process; hidden tests and reference solutions are never mounted into learner containers.

## Before publishing a content version

1. Run `scripts/validate_content.py`.
2. Run each reference solution against its public and private fixture set.
3. Run each recorded wrong solution and confirm the relevant assertion fails.
4. Check that references are official, reviewed, and have a recorded version or review date.
5. Confirm the public exercise API cannot return solutions, grading contracts, private fixtures, or hidden hints.
6. Publish immutable exercise and runtime versions only after these checks pass.

## Runtime and recovery checks

- Benchmark reference solutions and set limits from measured CPU, memory, and latency.
- Keep one active job per learner and no more than two concurrent Spark jobs initially.
- Retry infrastructure failures at most twice. Do not retry incorrect learner submissions automatically.
- Reclaim expired worker leases and mark jobs as infrastructure errors when a worker disappears.
- Canceling a job must terminate the sandbox and preserve only bounded logs and declared artifacts.
- Test a failed staged ingestion and a retry before promoting a dataset.
- Take daily encrypted backups. Rehearse restore at least once per release cycle; the initial target is four-hour recovery and at most 24 hours of lost progress.

## Budget and observability

Start with the €300/month planning envelope: application/database/queue €50, execution €130, storage/backups €20, tutor €60, and monitoring/contingency €40. Alert at 70% and 90%; pause optional tutor and advanced-compute usage at the €400 hard ceiling.

Monitor queue time, job latency, timeouts, memory kills, worker leases, cleanup failures, grader disagreements, repeated misconception feedback, tutor usage, and spend. Store raw execution artifacts for 30 days. Retain source and scores until learner deletion.

## Pilot gate

Pilot with three to five learners. Observe whether requirements are clear, variants prevent memorization, feedback is accurate, prerequisites are sufficient, and learners can transfer to a new dataset. Correct the lesson or grader before public release when any of these checks fail.

