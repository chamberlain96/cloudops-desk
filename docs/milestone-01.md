# Milestone 1 — Local Application and DevSecOps CI

Date: October 12, 2026

## Goal

Build a working support-ticket application, preserve its data,
containerize it, and automate testing and security checks before
starting AWS deployment.

## Application completed

CloudOps Desk currently includes:

- A Flask API and browser interface.
- Ticket creation, listing, and retrieval.
- Validation of incoming requests.
- SQLite persistence through Flask-SQLAlchemy.
- Six automated tests using an isolated temporary database.

Endpoints:

| Method | Route | Purpose |
|--------|-------|---------|
| GET | / | Display the web interface |
| GET | /health | Check application responsiveness |
| POST | /tickets | Create a ticket |
| GET | /tickets | List tickets |
| GET | /tickets/<id> | Retrieve one ticket |

Successful creation returns 201.
Invalid input returns 400.
An unknown ticket returns 404.

The health endpoint currently checks application responsiveness,
not database readiness.

## Project components

| Location | Purpose |
|----------|---------|
| app/__init__.py | Flask application setup and routes |
| app/models.py | Ticket database model |
| app/templates/index.html | Browser interface |
| tests/test_api.py | Automated application tests |
| requirements.txt | Runtime dependencies |
| requirements-dev.txt | Runtime and testing dependencies |
| requirements-security.txt | Bandit and pip-audit |
| Dockerfile | Application image definition |
| .dockerignore | Exclude local files from build context |
| .github/workflows/ci.yml | CI workflow |
| worker/ | Reserved for future background processing |

## Container implementation

The image uses Python, Gunicorn, and a non-root application user.

- Container application port: 5000.
- Original local container: cloudops-desk, localhost port 5001.
- Security candidate container: cloudops-security-test, port 5002.
- Original database volume: cloudops-ticket-data.
- Candidate database volume: cloudops-security-test-data.

The volumes mount at /app/instance, where SQLite stores tickets.
The two containers use separate databases.

We verified that a ticket survives removal and replacement of
the original container when its named volume is reused.

We used Docker commands directly. Compose was installed but is
not required for the current deployment.

## CI workflow

On pushes to main and pull requests targeting main, CI:

1. Checks out the repository with Git history.
2. Scans history for secrets using Gitleaks.
3. Installs development and security dependencies.
4. Audits runtime Python dependencies using pip-audit.
5. Runs pytest.
6. Scans Python source using Bandit.
7. Builds an image tagged with the commit SHA.
8. Exports the image and generates a full Trivy report.
9. Uploads the vulnerability report as an artifact.
10. Blocks fixable HIGH and CRITICAL image vulnerabilities.
11. Initializes an isolated database and starts the image.
12. Checks health, ticket creation, and ticket retrieval over HTTP.
13. Displays container logs and removes smoke-test resources.

Tests run outside the runtime image.
The container smoke test verifies the actual packaged application.

The workflow does not publish images or deploy to AWS yet.

## Git controls

Changes are made on feature branches and submitted through
pull requests.

Main requires pull requests and the test-and-build status check.
Required approving reviews were disabled for this solo lab.
A team environment would normally require another reviewer.

## Verification completed

- Six application tests passed.
- Browser ticket creation and retrieval worked.
- Tickets survived application restart.
- Tickets survived container replacement.
- An intentional failing test failed CI.
- Branch protection blocked merging failing CI.
- Bandit detected a deliberately unsafe eval example.
- The unsafe example was removed before merging.
- Gitleaks reported no leaks in the initial local history scan.
- pip-audit reported no known runtime dependency vulnerabilities.
- The runtime candidate excluded pytest.
- The container smoke test passed.

## Security findings and limitations

The initial image scan reported four HIGH Python findings
involving msgpack, setuptools, and urllib3.

Investigation found msgpack and urllib3 bundled inside pip.
After pip was removed from the runtime candidate, the new scan
reported no HIGH or CRITICAL Python findings.

The candidate report still contained 44 HIGH Debian findings
with no listed fixed versions and no CRITICAL findings.

These remain unresolved and visible in the report. Passing the
lab gate is not production security approval.

The lab gate blocks fixable HIGH and CRITICAL vulnerabilities.
Findings without fixes still require assessment, tracking,
mitigation, and rescanning.

Scanner results are a point-in-time assessment and can change.

Authentication, authorization, PostgreSQL, the background worker,
AWS deployment, OIDC, managed secrets, and monitoring remain
future stages. SQLite volumes are persistence, not backups.

## Troubleshooting lessons

- Activate the virtual environment before running Python tools.
- Use a separate test database to avoid saved data affecting tests.
- Keep YAML indentation consistent.
- Keep Trivy command flags inside their scan step.
- Retry transient connection errors while a container starts.
- Inspect container logs when readiness checks fail.
- Separate runtime, testing, and security dependencies.
- Investigate where vulnerable packages originate before upgrading.

## Local verification commands

From the project root:

    source .venv/bin/activate
    python -m pip install -r requirements-dev.txt
    python -m pip install -r requirements-security.txt
    python -m pytest -q
    python -m bandit -r app
    python -m pip_audit -r requirements.txt --strict

Start the existing original container:

    docker start cloudops-desk

Visit:

    http://localhost:5001

Stop it:

    docker stop cloudops-desk

## Next milestone

Document the AWS architecture and provision its initial networking
with Terraform. Then configure an EC2 application deployment
with Ansible.

Before provisioning, review connectivity, IAM permissions,
expected costs, state management, and cleanup.

---

# Milestone 2 — AWS Network and Terraform State

Date: October 13, 2026

## Goal

Build a reusable AWS network with Terraform, protect its state,
and add infrastructure checks to CI.

## State storage

Bucket: cloudops-desk-tfstate-eb2bb881

Configuration:
- Versioning enabled.
- AES256 server-side encryption.
- Public access blocked.
- Accidental Terraform destruction protected.

State keys:
- Bootstrap: bootstrap/terraform.tfstate
- Development: environments/dev/terraform.tfstate

Bootstrap state was migrated from local storage to S3.
Both backends enable native S3 locking with use_lockfile = true.

State files and saved plans are excluded from Git.
Provider lock files are committed.

## Network architecture

Region: us-east-1
VPC: 10.20.0.0/16

| Subnet | CIDR | Placement |
|--------|------|-----------|
| Public 1 | 10.20.1.0/24 | First selected AZ |
| Public 2 | 10.20.2.0/24 | Second selected AZ |
| Private 1 | 10.20.11.0/24 | First selected AZ |
| Private 2 | 10.20.12.0/24 | Second selected AZ |

Terraform defines:
- One VPC.
- One internet gateway.
- Four subnets.
- Two custom route tables.
- One internet route.
- Four subnet associations.

Public subnets route 0.0.0.0/0 through the internet gateway.
Private subnets currently have only VPC-local routing.
Automatic public-IP assignment is disabled in all four subnets.

No NAT gateway, EC2 instance, load balancer, RDS database,
or EKS cluster was included in this stage.

## Terraform structure

- infra/bootstrap/: State bucket setup.
- infra/modules/network/: Reusable network module.
- infra/environments/dev/: Development configuration.

Module outputs expose VPC, subnet, and route-table IDs.

## Verification

Expected successful network apply:
13 added, 0 changed, 0 destroyed.

After deployment, run:

    terraform -chdir=infra/bootstrap plan
    terraform -chdir=infra/environments/dev plan

Expected:
No changes. Your infrastructure matches the configuration.

Inspect AWS subnets and route tables to confirm the CIDRs,
two-zone placement, and public/private routing.

## CI and Git protection

A separate Terraform workflow checks:
- Formatting.
- Bootstrap configuration validation.
- Development configuration validation.

CI initialization uses -backend=false and read-only provider
lock files. It does not need AWS credentials or change resources.

Required checks for main:
- test-and-build
- terraform-checks

Terraform planning and deployment still run locally.
OIDC-based automation is future work.

## Limitations and next steps

- The application is not deployed to AWS yet.
- Private workload internet access is not configured.
- Workload security groups and VPC flow logs are future work.
- S3 storage, requests, and retained versions can incur charges.
- Keep the state bucket while Terraform manages infrastructure.

Next: Review the EC2 deployment architecture, permissions, costs,
and cleanup; provision with Terraform and configure with Ansible.
