# CI/CD Workflows

The CI/CD pipeline is defined in a single unified workflow: [`ci.yml`](ci.yml).

It runs on every push and pull request to `main` and `develop`, with path-based filtering to skip unaffected jobs.

For full documentation including stage breakdown, job dependencies, Docker image tagging, and how to run CI checks locally, see the [CI/CD Pipeline documentation](../../docs/ci.md).
