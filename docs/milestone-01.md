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

## Milestone 3 — Terraform EC2 and Ansible deployment

### Goal
Deploy CloudOps Desk to AWS using Terraform for infrastructure and Ansible for server configuration and application deployment.

### Infrastructure
- Reused the Terraform VPC and a public subnet.
- Provisioned an Ubuntu EC2 instance with an encrypted root volume.
- Restricted SSH and application access to my public IP.
- Required IMDSv2.
- Attached an instance role with the managed Systems Manager policy.
- Used the existing S3 remote state backend with locking.

### Deployment
- Installed and enabled Docker through an Ansible role.
- Transferred a Docker image archive from WSL to EC2.
- Loaded the image only when the archive changed or the image was missing.
- Stored the SQLite database in a named Docker volume.
- Initialized the database only when its file was missing.
- Managed the application container with community.docker.
- Combined configuration, image preparation, database initialization, and deployment in ansible/release.yml.
- Added a health check with retries.

### Verification
- The application loaded on EC2 and saved tickets.
- Tickets remained after restarting the container.
- Repeated Ansible runs reported changed=0 and failed=0.
- Added GitHub Actions syntax validation for the release playbook.

### Troubleshooting
The first image-loading attempt failed because the archive was missing on EC2. I built and exported the image locally, copied the archive to the server, and then loaded it successfully.

### Current limitations
- Image building and release execution are initiated from WSL.
- The application uses HTTP with access restricted to my IP.
- SQLite data survives container replacement, but is not protected against instance termination.
- Database initialization checks file existence; schema migrations are not implemented.
- Health checks confirm the application responds, not database readiness.
- Attaching the Systems Manager policy alone does not verify SSM connectivity.
- CI blocks fixable HIGH and CRITICAL image vulnerabilities; unresolved findings remain in the full report.

### Cost control
Stop the EC2 instance between sessions. EBS storage and S3 charges can continue while it is stopped. Its public IP can change when restarted, requiring an inventory update.

### Interview explanation
“I provisioned an AWS server with Terraform and automated Docker application deployment with Ansible. I verified repeatable deployments and container restart persistence, added CI validation, and documented security, recovery, and cost limitations.”

## Milestone 4 — ECR publishing with OIDC and EC2 deployment

### Goal
Publish tested Docker images from GitHub Actions to Amazon ECR and deploy them to EC2 without copying image archives or storing AWS access keys.

### Implementation
- Created an encrypted ECR repository with immutable tags and scan-on-push.
- Configured GitHub OIDC and a publishing role restricted to this repository's main branch.
- Published the tested image using its Git commit SHA as the tag.
- Granted the EC2 instance role pull permissions scoped to the application repository.
- Installed AWS CLI through Ansible using the official Snap package.
- Added an ECR preparation playbook that hides authentication details from logs.
- Updated release.yml to pull and deploy an image selected by its exact digest.
- Removed the archive preparation playbook and old hardcoded image defaults.

### Verification
- GitHub Actions authenticated through OIDC and published images to ECR.
- EC2 obtained AWS credentials through its instance role.
- EC2 pulled an image by digest.
- The release playbook completed successfully.
- Existing tickets remained after deployment.
- The combined playbook passed its syntax check.

### Troubleshooting
- Terraform proposed replacing the stopped EC2 instance because public IP association was read as false. Starting the existing instance and regenerating the plan cleared the replacement.
- GitHub authentication initially failed because the trust policy used the legacy subject format. Updating it to include the repository and owner IDs resolved the mismatch.
- SSH required verification of the host key at the new public IP. I retrieved the fingerprint through Session Manager and confirmed it matched.
- AWS CLI was missing on EC2, so I added its installation to the Ansible role.

### Current limitations
- GitHub Actions publishes images, but release execution still starts from WSL.
- The release command requires cloudops_image to be supplied explicitly.
- ECR authentication uses a temporary credential stored in root's Docker configuration.
- The AWS CLI Snap package updates automatically rather than pinning a minor version.
- The application still uses HTTP and SQLite without an instance-loss backup.
- Database migrations and automated rollback are not implemented.

### Interview explanation
“I built a pipeline that tests and scans a Docker image, authenticates to AWS through OIDC, and publishes it to ECR. EC2 uses a separate IAM role with repository-scoped pull permissions, and Ansible deploys the selected image by digest while preserving the database volume.”

## Milestone 5 — SSM release execution and application rollback

### Implementation
- Added Ansible block/rescue logic to remember the current image, deploy a selected image, verify health, and restore the previous image after failure.
- Kept a recovered release marked as failed so CI reports the release outcome correctly.
- Installed an isolated Ansible runtime and the Docker collection on EC2.
- Added a local inventory so EC2 can run Ansible against itself without SSH.
- Installed application release playbooks on EC2 through install-release.yml.
- Created the Terraform-managed CloudOpsDesk-Release SSM document.
- Restricted the document input to this ECR repository and an exact image digest.
- Added a host-side release lock.
- Created a separate GitHub OIDC deployment role scoped to the release document and application instance.
- Added a manual GitHub deployment workflow with input validation, ECR verification, concurrency control, and SSM result reporting.

### Validation
- A normal Ansible release passed.
- An intentional verification failure entered the recovery path.
- A deliberately broken local image was used for a rollback test.
- The dedicated SSM document successfully executed local Ansible on EC2.
- The first GitHub-triggered release remains to be verified after merging.

### Troubleshooting
- The Ubuntu-packaged WSL AWS CLI failed with "badly formed help string" for SSM send-command. A separate AWS bundled CLI installation successfully submitted the command.
- The initial collection check failed because its installation directory did not exist. Added directory creation before checking collections.

### Limitations
- Release playbooks must be installed on EC2 separately when their contents change.
- Rollback restores application code, not database changes.
- This is a single-server deployment with possible downtime during container replacement.
- Health verification currently checks the application endpoint, not database readiness.
- The deployment workflow accepts an existing image digest; it does not independently enforce CI provenance.
- SSH access remains configured for administration and bootstrap.

## Milestone 6 — PostgreSQL support and private RDS foundation

### Application preparation
- Made the database connection configurable through DATABASE_URL, retaining SQLite as the default.
- Added the Psycopg PostgreSQL driver.
- Verified ticket creation through Flask and confirmed the record directly in local PostgreSQL.
- Added /ready to check database connectivity, separate from /health.
- Added automated readiness tests.
- Enabled connection-pool pre-ping and a PostgreSQL connection timeout.
- Corrected configuration ordering so SQLite tests do not receive PostgreSQL-only connection arguments.

### AWS infrastructure
- Created private RDS PostgreSQL 17.11 using Terraform.
- Used db.t4g.micro, Single-AZ, and 20 GiB encrypted gp3 storage.
- Restricted port 5432 to the application's security group.
- Required TLS through a database parameter group.
- Enabled RDS-managed administrator credentials in Secrets Manager.
- Enabled deletion protection and required a final snapshot on deletion.
- Configured one-day automated backup retention because the account rejected seven days.

### Verification
- RDS reported available, publicly accessible false, storage encrypted true, and managed secret active.
- A Python script executed through SSM retrieved credentials using the EC2 instance role.
- The script connected with sslmode=verify-full, executed SELECT 1, and confirmed TLS.
- Removed the temporary EC2 administrator-secret access policy after the check.

### Troubleshooting
- A newer Ubuntu AMI selected by most_recent caused Terraform to propose EC2 replacement. Pinned the existing AMI to preserve the server and its SQLite data.
- AWS rejected seven-day backup retention under the account plan. Retried successfully with one day.
- An empty shell command-ID variable prevented an SSM waiter from running. Submitted the command directly and tracked its returned ID.

### Current boundaries
- The deployed application still uses SQLite.
- Existing tickets have not been migrated.
- Restricted application database credentials and RDS application deployment are pending.
- One-day backup retention and Single-AZ availability are lab limitations.
- Backup configuration is verified; a restore drill has not yet been completed.
- Database-check dependencies on EC2 were installed through SSM and are not yet fully managed by Ansible.

### Interview explanation
“I prepared a Flask application for PostgreSQL and provisioned private, encrypted RDS infrastructure with Terraform. I verified certificate-checked TLS connectivity through SSM using Secrets Manager and temporary IAM access, then removed the administrator-secret permission.”

## Restricted RDS application credentials

Created a dedicated PostgreSQL login, cloudops_app, with no superuser,
database creation, role creation, replication, or row-security bypass privileges.

Stored its generated password in AWS Secrets Manager. The bootstrap script
reuses saved credentials when rerun and does not print passwords.

Verified application login using TLS with certificate and hostname validation.

Removed temporary bootstrap permissions after setup. Confirmed that the
EC2 instance role can read the application secret but cannot read the RDS
administrator secret.

Current boundary: database and schema connection permissions are configured.
Table permissions, ticket migration, and application cutover remain pending.
The deployed application continues to use SQLite.
