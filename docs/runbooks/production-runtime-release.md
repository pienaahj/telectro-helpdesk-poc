# Production Runtime Release Runbook

## Status

Canonical operational runbook for deploying durable application-runtime releases to the Telectro ERPNext / Helpdesk production environment.

This procedure was established from the production deployments performed on 15–16 July 2026.

## Purpose

This runbook defines the repeatable procedure for promoting a merged repository change into the Telectro production runtime.

It exists because the production VM is deliberately not a Git working copy.

The production environment is an artifact target consisting of:

- a deployed application directory;
- immutable Docker runtime images;
- durable site, database, Redis, asset, and log storage;
- a production environment file;
- deployment evidence retained on the VM.

The authoritative source remains:

- the GitHub repository;
- the clean local Git checkout;
- the exact merged commit used to build the release;
- the immutable image and transfer archive created from that commit.

The procedure is intended to ensure that every production release is:

- traceable;
- repeatable;
- narrowly scoped;
- reversible where technically possible;
- supported by explicit evidence;
- verified at runtime, database, HTTP, and user-interface levels where applicable.

## Scope

This runbook covers routine durable application-runtime releases for the existing production site:

```text
erp.telectro.co.za
```

It includes:

- release identification;
- local Git and source preflight;
- source-artifact creation;
- runtime-image build and validation;
- image archive creation and transfer;
- production image loading;
- fresh site backup;
- production environment update;
- selective runtime-service recreation;
- frontend nginx reload;
- site migration;
- cache clearing;
- site-aware database validation;
- changed-function execution;
- direct and routed health checks;
- browser-level verification;
- evidence capture;
- runtime rollback.

This runbook does not replace:

- initial production-host provisioning;
- firewall, DNS, certificate, or reverse-proxy administration;
- database-restore incident procedures;
- disaster recovery;
- general Docker-host maintenance;
- the broader production architecture and readiness guidance in `production-deployment.md`.

Urgent live-source corrections are treated as an exception and are described only to define their boundaries. They are not the normal deployment path.

## Related documents

- `docs/runbooks/production-deployment.md`
  - production architecture;
  - infrastructure responsibility boundary;
  - production Compose shape;
  - host and app-layer readiness;
  - initial deployment requirements.

- `docs/runbooks/bench-verification.md`
  - proof discipline;
  - source-of-truth hierarchy;
  - fresh Bench and browser verification principles.

- `docs/runbooks/pilot-docs-index.md`
  - canonical documentation map;
  - document ownership and navigation.

## Production deployment model

### Source of truth

The authoritative release source is:

```text
GitHub repository:
pienaahj/telectro-helpdesk-poc

Normal production release branch:
main
```

Every release must identify:

```text
release ID
source branch
full commit SHA
previous production image
candidate production image
image archive SHA-256
image config digest
site name
migration requirement
changed production artifacts
evidence paths
```

The production VM must not become an independently maintained source-code fork.

Do not perform routine production releases through:

```text
git pull
git checkout
git merge
live branch creation
manual conflict resolution
ad hoc source editing
```

### Production host

```text
Host:
erp.telectro.co.za

SSH/VPN address:
172.44.50.100

Application root:
/opt/telectro/erpnext/app

Production environment file:
/opt/telectro/erpnext/app/.env.production

Staging root:
/opt/telectro/erpnext/staging/<release-id>

Evidence root:
/opt/telectro/erpnext/deploy-evidence

Site:
erp.telectro.co.za
```

### Runtime image

The durable application release is selected by:

```text
ERPNEXT_IMAGE=telectro/erpnext-runtime:<immutable-release-tag>
```

A release tag must never be reused for different image contents.

Recommended format:

```text
prod-YYYYMMDD-<short-commit>
```

Example:

```text
prod-20260716-83f6147
```

### Long-running application services

The following five services use the custom runtime image and form the normal application-runtime replacement set:

```text
backend
websocket
queue-short
queue-long
scheduler
```

These five services must use the same immutable runtime image.

### One-shot setup services

The following services are not part of a routine release:

```text
configurator
create-site
```

They must not be started or recreated during a normal update to an existing production site.

### Post-migration infrastructure proof

The following infrastructure services remain unchanged unless a release explicitly requires an infrastructure change:

```text
db
redis-cache
redis-queue
frontend
```

At the time this runbook was established:

```text
MariaDB:
mariadb:10.6

Redis:
redis:6.2-alpine

Frontend:
frappe/erpnext:v15.94.1
```

The frontend container is intentionally separate from the custom application runtime image.

It normally remains the same container during an application release, but its nginx process must be reloaded after the backend container is recreated.

## Non-negotiable deployment principles

### Production is an artifact target

A durable production release must be traceable to all of the following:

```text
merged Git commit
source artifact
immutable runtime-image tag
image archive
archive checksum
embedded image content
production environment setting
running container image
migration state
database validation
functional smoke proof
HTTP proof
browser proof where applicable
deployment evidence
```

A source marker alone is not runtime proof.

A rendered Compose image alone is not running-container proof.

A successful migration alone is not functional proof.

### Verify the current state before changing it

Every deployment begins by proving the current production state.

At minimum, record:

- active `ERPNEXT_IMAGE`;
- runtime container IDs;
- configured container images;
- service states;
- restart counts;
- backend health;
- frontend, database, and Redis state;
- current routed `/api/method/ping` result;
- current environment-file hash;
- available disk space;
- latest backup state.

Never infer current production state from a prior handover or previous evidence file.

### One gate at a time

Do not combine the complete release into one large terminal paste.

The release must be divided into explicit gates such as:

1. local source proof;
2. image build;
3. candidate image validation;
4. image archive creation;
5. transfer and checksum proof;
6. production image load;
7. fresh backup;
8. environment update and Compose render;
9. runtime recreation;
10. nginx reload and HTTP proof;
11. migration;
12. cache clear and database verification;
13. functional and browser proof;
14. final evidence.

Each gate must:

- have one narrow purpose;
- print clear success markers;
- stop before the next state-changing gate;
- retain enough output to diagnose failure.

### Use site-aware production wrappers

Use the repository-controlled production wrappers wherever available.

Examples:

```bash
./bin/prod-compose.sh
./bin/prod-bench.sh
./bin/prod-migrate.sh
./bin/prod-render-compose.sh
```

Do not replace them with plain `docker compose` or raw Frappe initialization unless the runbook explicitly requires and proves that method.

### Recreate only the five runtime services

A normal application release recreates only:

```text
backend
websocket
queue-short
queue-long
scheduler
```

Do not recreate:

```text
frontend
db
redis-cache
redis-queue
configurator
create-site
```

unless a separately reviewed release explicitly requires it.

### Reload nginx after every backend recreation

Recreating `backend` normally gives it a new Docker-network IP address.

The existing frontend nginx workers may continue using the previously resolved backend IP even after Docker DNS resolves `backend` correctly.

The proven failure pattern is:

```text
backend container:
healthy

direct backend ping:
200 {"message":"pong"}

frontend Docker DNS lookup:
new backend IP

nginx upstream log:
old backend IP

routed frontend response:
502 Bad Gateway
```

Therefore, after every backend recreation:

1. wait for backend health;
2. prove a direct backend ping;
3. run `nginx -t` in the existing frontend container;
4. run `nginx -s reload`;
5. wait for the routed frontend ping to return `pong`;
6. prove the frontend container ID did not change.

The same nginx reload is mandatory after recreating the previous backend during runtime rollback.

### Prove both direct and routed application health

The deployment must distinguish two health paths.

Direct backend proof:

```text
backend container
→ localhost:8000
→ Frappe
→ pong
```

Routed application proof:

```text
VM frontend binding
→ nginx
→ backend container
→ Frappe
→ pong
```

A healthy backend with a failing routed path indicates a frontend, nginx, Docker-network, or reverse-proxy problem rather than proof that the candidate runtime is defective.

### Take a fresh verified backup before the runtime switch

The backup must be taken immediately before the runtime image is activated.

The backup is not proven merely because the Bench command exits successfully.

For each of the four matching backup artifacts, record:

```text
filename
common backup prefix
non-zero size
SHA-256
```

The expected artifacts are:

```text
site configuration backup
database backup
public files archive
private files archive
```

Do not assume one archive extension. Production backups may use `.tar`, `.tgz`, or another Bench-supported extension.

### Update only the intended environment line

For a routine runtime release, update exactly:

```text
ERPNEXT_IMAGE=<candidate-image>
```

Before changing it:

- record the environment-file hash;
- prove exactly one `ERPNEXT_IMAGE` line exists;
- create an exact timestamped backup.

After changing it:

- prove non-image lines are unchanged;
- render production Compose;
- prove required services resolve to the candidate image;
- prove no service still resolves to the previous runtime image;
- prove the frontend image setting is unchanged;
- prove the running containers remain on the previous image until recreation.

### Do not restart Docker to solve a release-build problem

A healthy production Docker daemon must not be restarted merely because image pull or build DNS is unreliable.

The established fallback is:

```text
build outside production
→ docker save
→ compress
→ checksum
→ transfer
→ docker load
```

Do not interrupt the complete production stack to make the VM act as an image builder.

### Use exact success markers and reject hidden failures

A command exit status of `0` is not sufficient when:

- an interactive console is involved;
- output is piped through `tee`;
- embedded Python performs assertions;
- a tool can print a traceback without correctly propagating failure.

Each validation must require:

- an exact success marker;
- successful command status;
- absence of known failure patterns;
- post-action health proof.

Known failure patterns include:

```text
Traceback
AssertionError
OperationalError
ProgrammingError
FileNotFoundError
SyntaxError
502 Bad Gateway
```

### Browser proof is mandatory for UI-sensitive releases

Browser-level proof must be completed before closing a release that changes:

```text
Workspace layout
Workspace links
report visibility
report navigation
roles or permissions
customer portal behavior
partner workspace behavior
user-facing labels
user-facing actions
```

An empty report result such as `Nothing to show` is valid when the report executes successfully and no production records match.

For non-UI releases, browser proof remains release-specific but must still be considered during release planning.

### Deployment evidence is part of the release

Evidence must be written under:

```text
/opt/telectro/erpnext/deploy-evidence
```

A release is not complete until:

- the final evidence file exists;
- its exact path is recorded;
- the final success marker is present;
- the daily handover records the commit, image, migration result, and proof state.

## Release classification

Before touching production, classify the change.

### Type A — repository-only change

Examples:

- documentation;
- tests;
- unused development scripts;
- code not intended for the current production release.

Action:

```text
merge only
no production deployment
```

### Type B — urgent targeted source correction

Use only when:

- a narrowly defined production artifact is missing or incorrect;
- the exact required files are known;
- the source-only correction is reversible;
- waiting for the durable image release is operationally unacceptable;
- a durable image-backed release will follow.

Requirements:

- stage the exact source artifact;
- back up every target file;
- replace only explicitly approved files;
- preserve all production-local state;
- prove `.env.production` is unchanged;
- prove the running image is still the previous image;
- record the source-only state as temporary;
- reconcile the change into the next immutable image.

A Type B correction is not a completed durable release.

### Type C — durable runtime release

This is the standard production path.

It includes:

```text
merged clean source
immutable runtime image
candidate image proof
archive and checksum proof
production image load
fresh verified backup
exact environment update
selective runtime recreation
backend health proof
frontend nginx reload
direct and routed ping proof
site migration when required
cache clear
site-aware database proof
functional execution
browser proof where applicable
final evidence
```

## Standard durable runtime release procedure

The following phases are the canonical Type C release path.

Do not skip directly to a later phase because an artifact or image from an earlier attempt appears to exist. Re-prove every release-specific input.

## Phase 0 — define the release identity

**Execution context:** local Mac, clean repository checkout.

Create the release identity before building or transferring anything.

Recommended release ID:

```text
YYYYMMDD-<short-commit>
```

Recommended immutable image tag:

```text
telectro/erpnext-runtime:prod-YYYYMMDD-<short-commit>
```

Example:

```text
RELEASE_ID=20260716-83f6147
IMAGE_TAG=telectro/erpnext-runtime:prod-20260716-83f6147
```

Record at minimum:

```text
RELEASE_ID
SOURCE_BRANCH
FULL_COMMIT_SHA
SHORT_COMMIT_SHA
PREVIOUS_PRODUCTION_IMAGE
CANDIDATE_IMAGE
SITE_NAME
SOURCE_ARTIFACT
SOURCE_ARTIFACT_SHA256
IMAGE_ARCHIVE
IMAGE_ARCHIVE_SHA256
IMAGE_CONFIG_DIGEST
MIGRATION_REQUIRED
CHANGED_PRODUCTION_ARTIFACTS
```

The release ID, image tag, source commit, and evidence filenames must agree.

Do not reuse an existing image tag for rebuilt or changed contents.

Required marker:

```text
RELEASE_IDENTITY_DEFINED
```

## Phase 1 — local Git preflight

**Execution context:** local Mac, repository root.

Prove the current branch, commit, working-tree state, and remote relationship.

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse --short HEAD
git status --short
git log -1 --oneline
git fetch origin
git rev-list --left-right --count HEAD...origin/main
```

For a normal production release, required conditions are:

- branch is `main`;
- working tree is clean;
- local `main` matches `origin/main`;
- the intended pull request is merged;
- the full commit SHA is recorded;
- no uncommitted fixture exports or generated files remain.

Do not build a production release from:

```text
an unmerged feature branch
a dirty working tree
a detached HEAD
a local commit not present on origin/main
```

Required marker:

```text
LOCAL_GIT_RELEASE_PREFLIGHT_OK
```

## Phase 2 — inspect and classify the change

Compare the previous deployed commit with the candidate commit.

Typical commands:

```bash
git diff \
  <previous-production-commit>..<candidate-commit> \
  --stat

git diff \
  <previous-production-commit>..<candidate-commit> \
  --name-status
```

Review changed production artifacts individually.

Examples:

```bash
git diff \
  <previous-production-commit>..<candidate-commit> \
  -- apps/telephony/telephony/hooks.py

git diff \
  <previous-production-commit>..<candidate-commit> \
  -- apps/telephony/telephony/fixtures/workspace.json

git diff \
  <previous-production-commit>..<candidate-commit> \
  -- apps/telephony/telephony/fixtures/report.json
```

Determine whether the release changes:

```text
Python application code
hooks
fixtures
DocTypes
patches
reports
Workspace definitions
frontend assets
permissions
roles
database schema
data
scripts only
documentation only
```

Record whether migration is required.

Migration should normally be treated as required when the release changes:

```text
fixtures
DocTypes
custom fields
patches
hooks that affect fixture import
roles or permissions
Workspace definitions
Reports
database schema
```

For JSON fixtures, validate syntax locally:

```bash
python3 -m json.tool \
  apps/telephony/telephony/fixtures/workspace.json \
  >/dev/null
```

Use semantic validation for changed fixtures. Do not rely only on valid JSON syntax.

A semantic validator should prove, as applicable:

- exact record identity;
- expected metadata;
- expected child rows;
- exact role lists;
- expected labels and spelling;
- no duplicate records;
- no stale or unintended records;
- expected report type and reference DocType;
- expected Workspace card and link structure.

Prefer a saved temporary validation script over deeply nested inline shell quoting.

Required markers:

```text
RELEASE_CHANGE_REVIEW_OK
RELEASE_MIGRATION_DECISION_RECORDED
LOCAL_FIXTURE_VALIDATION_OK
```

The fixture marker is required only when fixture files changed.

## Phase 3 — create the source artifact

The source artifact exists for:

- release traceability;
- staged inspection;
- checksum evidence;
- emergency recovery reference;
- proving exactly which repository state produced the image.

For a normal Type C release, the source artifact is **not automatically copied into the live production application tree**.

The production runtime source comes from the immutable image.

Only an explicitly classified Type B correction may apply selected source files directly to the production application directory.

Recommended local artifact path:

```text
/tmp/telectro-app-<release-id>.tar.gz
```

The artifact should contain the repository-controlled deployment source needed to:

- build the runtime image;
- inspect changed application overlays;
- reproduce the release;
- verify release markers.

It must not contain:

```text
.git
local secrets
.env.production
.env.local
site data
database data
Redis data
local import files
deployment evidence
editor caches
macOS AppleDouble files
```

### macOS artifact guard

macOS can add AppleDouble files named:

```text
._*
```

The artifact must exclude them during creation where possible.

After creating or extracting the artifact, prove the count is zero:

```bash
find <artifact-staging-directory> \
  -type f \
  -name '._*' \
  -print
```

Any listed files must be removed before transfer or use.

Record:

```bash
shasum -a 256 \
  /tmp/telectro-app-<release-id>.tar.gz
```

Required markers:

```text
SOURCE_ARTIFACT_CREATED
SOURCE_ARTIFACT_APPLEDOUBLE_FREE
SOURCE_ARTIFACT_SHA256_RECORDED
```

## Phase 4 — build the immutable runtime image

### Build location

Preferred order:

1. controlled CI Linux AMD64 builder;
2. controlled external AMD64 builder;
3. Mac Docker Buildx targeting Linux AMD64.

Do not use the production VM as the normal image builder.

Do not restart the production Docker daemon to solve a build, pull, or registry-DNS problem.

### Architecture

The production host requires:

```text
linux/amd64
```

On Apple Silicon, specify the target platform explicitly:

```text
--platform linux/amd64
```

An ARM64 host warning during local AMD64 image testing can be expected. The candidate image itself must still inspect as `linux/amd64`.

### Build inputs

At the time this runbook was established, the runtime image used:

```text
Dockerfile:
docker/telectro-runtime.Dockerfile

ERPNext base:
frappe/erpnext:v15.94.1

Helpdesk:
v1.18.1

Required final apps:
frappe
erpnext
helpdesk
telephony
```

All production base images and upstream application refs must be pinned.

Do not build a production runtime from moving references such as:

```text
latest
main
develop
edge
```

### Build execution

Use a saved script or repository-controlled helper rather than a large interactive terminal paste.

The build must:

- change to the repository root;
- accept an explicit image tag;
- use the exact candidate commit;
- target `linux/amd64`;
- load or export the completed image;
- retain the complete build log;
- fail when any installation, import, asset, or build step fails;
- avoid tag reuse.

On the Mac, use a tested Buildx builder. Do not assume the default builder is suitable merely because it exists.

Keep the Mac awake during a long build.

Required marker:

```text
CANDIDATE_RUNTIME_IMAGE_BUILD_OK
```

## Phase 5 — validate the candidate image locally

Do not transfer the candidate merely because the image build returned status `0`.

Prove at minimum:

```text
expected immutable tag exists
operating system is linux
architecture is amd64
all four required apps exist
Python imports pass
application versions match the release
changed artifacts are embedded
```

Inspect the image:

```bash
docker image inspect "$IMAGE_TAG"
```

Prove the platform:

```text
Os=linux
Architecture=amd64
```

Run candidate validation in an isolated container.

The validation should prove:

```text
frappe import succeeds
erpnext import succeeds
helpdesk import succeeds
telephony import succeeds
bench command runs
expected application versions are present
changed fixture or source file exists
changed fixture or source file has the expected hash
```

Expected application versions at the time this runbook was established:

```text
frappe 15.96.0
erpnext 15.94.1
helpdesk 1.18.1
telephony 0.0.1
```

For fixture releases, validate the fixture **inside the image**, not only in the local checkout.

Examples of semantic image validation include:

- Workspace card count and names;
- Workspace card widths;
- Card Break count;
- ordered report links;
- exact label spelling;
- Report metadata;
- exact child-role list;
- required query clauses;
- no unintended report script;
- no duplicate fixture records.

Record:

```text
candidate image tag
candidate image creation timestamp
candidate image local size
candidate image OS
candidate image architecture
embedded artifact SHA-256
application versions
validation log path
```

Required markers:

```text
CANDIDATE_RUNTIME_PLATFORM_OK
CANDIDATE_RUNTIME_IMPORTS_OK
CANDIDATE_RUNTIME_VERSIONS_OK
CANDIDATE_EMBEDDED_CHANGE_OK
CANDIDATE_RUNTIME_VALIDATION_OK
```

## Phase 6 — create and prove the image archive

Save the candidate image to a compressed archive.

Recommended path:

```text
/tmp/telectro-erpnext-runtime-<image-tag>.tar.gz
```

Example:

```bash
docker save "$IMAGE_TAG" |
  gzip -1 \
  >"$IMAGE_ARCHIVE"
```

Validate gzip integrity:

```bash
gzip -t "$IMAGE_ARCHIVE"
```

Record the exact archive size:

```bash
stat -f '%z' "$IMAGE_ARCHIVE"
```

Record the archive SHA-256:

```bash
shasum -a 256 "$IMAGE_ARCHIVE"
```

### Record the embedded config digest

Inspect the uncompressed Docker archive manifest and identify its config object.

Docker archives may use either of these layouts:

```text
<digest>.json
```

or:

```text
blobs/sha256/<digest>
```

The validation must:

1. read `manifest.json`;
2. locate the config path for the expected tag;
3. hash the actual config blob;
4. prove that the config blob’s SHA-256 matches its declared digest;
5. record the config digest separately from the daemon-reported image ID.

Record:

```text
archive path
archive byte size
archive SHA-256
config path
declared config digest
actual config blob SHA-256
expected image tag
```

Required markers:

```text
IMAGE_ARCHIVE_GZIP_OK
IMAGE_ARCHIVE_TAG_OK
IMAGE_ARCHIVE_SHA256_RECORDED
IMAGE_ARCHIVE_CONFIG_DIGEST_OK
IMAGE_ARCHIVE_VALIDATION_OK
```

## Phase 7 — transfer the release artifacts

**Execution context:** local Mac to production staging.

Production staging location:

```text
/opt/telectro/erpnext/staging/<release-id>
```

Recommended structure:

```text
/opt/telectro/erpnext/staging/<release-id>/app
/opt/telectro/erpnext/staging/<release-id>/image
```

Before transfer, check production free space for:

- the compressed archive;
- temporary verification files;
- the loaded Docker image;
- the fresh Bench backup;
- retained deployment evidence.

Transfer with resumable `rsync`:

```bash
rsync -avP \
  "$IMAGE_ARCHIVE" \
  "${IMAGE_ARCHIVE}.sha256" \
  erp@172.44.50.100:/opt/telectro/erpnext/staging/<release-id>/image/
```

Transfer the source artifact and its checksum separately when required for release traceability.

Do not unpack or copy the source artifact into the live application root during a normal Type C release.

An SSH disconnect after file transfer does not prove transfer failure or success. Reconnect and verify the staged files directly.

Required marker:

```text
RELEASE_ARTIFACT_TRANSFER_COMPLETE
```

## Phase 8 — verify and load the image on production

**Execution context:** production VM.

Before loading, prove:

```text
expected staged archive exists
archive size matches local evidence
archive SHA-256 matches local evidence
gzip integrity passes
candidate tag is not already ambiguously reused
running production containers remain unchanged
```

Run:

```bash
sha256sum "$IMAGE_ARCHIVE"
gzip -t "$IMAGE_ARCHIVE"
```

Load the image without changing running containers:

```bash
gzip -dc "$IMAGE_ARCHIVE" |
  docker load
```

After loading, prove:

```text
expected image tag exists
image OS is linux
image architecture is amd64
image creation timestamp matches the candidate
application imports pass
application versions match
embedded artifact hash matches
embedded semantic validation passes
running containers still use the previous image
```

### Cross-daemon image identity

Do not require the Mac and production Docker daemons to report an identical value for:

```text
docker image inspect .Id
```

Docker Desktop and the production daemon may report different daemon-local image IDs for an archive whose bytes and config object are identical.

Release identity must rely primarily on:

1. exact image archive SHA-256;
2. exact embedded config blob digest;
3. exact immutable image tag;
4. image operating system and architecture;
5. image creation timestamp;
6. exact embedded application and fixture proof.

A different daemon-reported image ID must be investigated and recorded, but it does not by itself prove archive corruption.

The production image-load gate must not update `.env.production`, recreate containers, or migrate the site.

Required markers:

```text
PRODUCTION_ARCHIVE_SHA256_OK
PRODUCTION_ARCHIVE_GZIP_OK
PRODUCTION_IMAGE_LOAD_OK
PRODUCTION_CANDIDATE_PLATFORM_OK
PRODUCTION_CANDIDATE_IMPORTS_OK
PRODUCTION_CANDIDATE_VERSIONS_OK
PRODUCTION_CANDIDATE_EMBEDDED_CHANGE_OK
RUNNING_PRODUCTION_RUNTIME_UNCHANGED
PRODUCTION_IMAGE_LOAD_AND_VALIDATION_OK
```

## Phase 9 — take and verify a fresh production backup

**Execution context:** production VM.

Take the backup immediately before changing `.env.production` or recreating runtime services.

Change to the production application root:

```bash
cd /opt/telectro/erpnext/app
```

Run the site-aware backup:

```bash
./bin/prod-bench.sh \
  --site erp.telectro.co.za \
  backup \
  --with-files
```

The backup must produce four artifacts sharing one new timestamped prefix:

```text
site configuration backup
database backup
public files archive
private files archive
```

The exact file extensions may vary between Bench versions or backup runs.

Do not assume:

```text
.tar
.tgz
.sql.gz
```

without inspecting the generated filenames.

### Backup verification

For each of the four artifacts, record:

```text
full path
filename
common backup prefix
byte size
SHA-256
```

Each artifact must:

- exist;
- have the expected common prefix;
- have a non-zero size;
- be readable;
- have its SHA-256 recorded in deployment evidence.

Example verification:

```bash
ls -lh \
  /home/frappe/frappe-bench/sites/erp.telectro.co.za/private/backups/

sha256sum \
  /home/frappe/frappe-bench/sites/erp.telectro.co.za/private/backups/<backup-file>
```

The database backup must not be treated as proven merely because the Bench backup command returned status `0`.

Record the backup prefix as the release’s database rollback point.

Do not proceed when:

```text
fewer than four matching artifacts exist
one artifact has zero size
artifact prefixes do not match
a checksum cannot be calculated
the backup path is ambiguous
```

Required markers:

```text
PRODUCTION_BACKUP_COMMAND_OK
PRODUCTION_BACKUP_FOUR_ARTIFACTS_OK
PRODUCTION_BACKUP_ARTIFACT_HASHES_OK
PRODUCTION_PRE_RELEASE_BACKUP_OK
```

## Phase 10 — update `.env.production` and prove Compose intent

**Execution context:** production VM.

Production environment file:

```text
/opt/telectro/erpnext/app/.env.production
```

This phase changes configuration intent only.

It must not recreate containers, migrate the site, or run one-shot setup services.

### Pre-change guards

Before modifying the file, prove:

```text
the file exists
exactly one ERPNEXT_IMAGE line exists
the line contains the expected previous image
the candidate image exists in the local Docker daemon
the previous image exists in the local Docker daemon
the current routed application ping succeeds
```

Record:

```bash
grep -n '^ERPNEXT_IMAGE=' .env.production
sha256sum .env.production
```

Create an exact timestamped backup:

```text
.env.production.pre-<release-id>-<timestamp>
```

Example:

```text
.env.production.pre-20260716-83f6147-20260716_122035
```

Prove the backup is byte-for-byte identical to the original:

```bash
cmp -s \
  .env.production \
  .env.production.pre-<release-id>-<timestamp>
```

Record the backup SHA-256.

### Change exactly one line

Update only:

```text
ERPNEXT_IMAGE=<candidate-image>
```

Use an atomic replacement method that:

- requires exactly one matching line;
- verifies the expected previous value;
- preserves file line endings;
- preserves file permissions and metadata;
- writes to a temporary file;
- uses an atomic rename;
- removes the temporary file on failure.

Do not use a broad text replacement that could alter other values.

### Prove only the intended setting changed

After the update, prove:

```text
exactly one ERPNEXT_IMAGE line exists
the line contains the candidate image
the complete file hash changed
all non-ERPNEXT_IMAGE lines have the same hash as before
ERPNEXT_NGINX_IMAGE is unchanged
```

Required markers:

```text
PRODUCTION_ENVIRONMENT_PRE_CHANGE_GUARDS_OK
PRODUCTION_ENVIRONMENT_BACKUP_EXACT_OK
PRODUCTION_ERPNEXT_IMAGE_UPDATE_OK
PRODUCTION_ERPNEXT_IMAGE_UPDATE_ONLY_OK
```

### Render the production Compose model

Use the repository-controlled rendering path:

```bash
OUTPUT_FILE=/tmp/telectro-production-compose-<release-id>.yaml \
  ./bin/prod-render-compose.sh
```

Also inspect the machine-readable model:

```bash
./bin/prod-compose.sh \
  config \
  --format json
```

Prove the candidate image is rendered for:

```text
backend
configurator
create-site
queue-long
queue-short
scheduler
websocket
```

The presence of the candidate image in `configurator` and `create-site` is expected in the rendered model.

It does not authorize those one-shot services to run.

Prove:

```text
no rendered service retains the previous runtime image
frontend retains ERPNEXT_NGINX_IMAGE
no unexpected public edge configuration appears
```

Before runtime recreation, prove the five running runtime containers still use the previous image.

This distinguishes:

```text
configured future state
```

from:

```text
actual running state
```

Required markers:

```text
PRODUCTION_COMPOSE_RENDER_OK
PRODUCTION_RENDERED_RUNTIME_IMAGE_REFERENCES_OK
PRODUCTION_RUNNING_CONTAINERS_STILL_ON_PREVIOUS_IMAGE
PRODUCTION_ENVIRONMENT_AND_RENDER_VALIDATION_OK
```

## Phase 11 — capture the pre-recreation container boundary

Before recreating anything, record the container IDs for:

```text
backend
websocket
queue-short
queue-long
scheduler
frontend
db
redis-cache
redis-queue
```

Also record the existing container IDs, if any, for:

```text
configurator
create-site
```

For the five runtime services, prove:

```text
configured image is the previous image
state is running
restart count is 0
backend health is healthy
```

For infrastructure, prove:

```text
frontend is running
database is running and healthy where a health check exists
Redis services are running
```

Record:

```text
service name
container ID
configured image
state
health state
restart count
```

The recorded IDs form the proof boundary for the selective recreation.

Required markers:

```text
PRE_RECREATION_RUNTIME_IDENTITIES_CAPTURED
PRE_RECREATION_INFRASTRUCTURE_IDENTITIES_CAPTURED
PRE_RECREATION_ONE_SHOT_STATE_CAPTURED
PRODUCTION_RUNTIME_RECREATION_PRECHECK_OK
```

## Phase 12 — recreate only the five runtime services

Recreate exactly:

```text
backend
websocket
queue-short
queue-long
scheduler
```

Use:

```bash
./bin/prod-compose.sh \
  up \
  -d \
  --no-deps \
  --force-recreate \
  backend \
  websocket \
  queue-short \
  queue-long \
  scheduler
```

Do not include:

```text
frontend
db
redis-cache
redis-queue
configurator
create-site
```

Expected impact:

- brief interruption to application requests;
- database remains running;
- Redis remains running;
- frontend container remains running;
- one-shot setup services remain untouched.

Required marker:

```text
PRODUCTION_RUNTIME_RECREATION_COMMAND_OK
```

### Wait for candidate runtime state

Wait until all five runtime services:

```text
exist
are running
use the candidate image
```

Wait until backend health becomes:

```text
healthy
```

Use a bounded retry loop.

Do not continue indefinitely.

Record each attempt with:

```text
attempt number
runtime running state
backend health state
```

After readiness, prove:

```text
all five runtime container IDs changed
all five configured images equal the candidate image
all five states are running
backend health is healthy
restart counts are 0
```

Required markers:

```text
PRODUCTION_CANDIDATE_RUNTIME_SERVICES_RUNNING
PRODUCTION_CANDIDATE_BACKEND_HEALTHY
PRODUCTION_FIVE_RUNTIME_SERVICES_ON_CANDIDATE
```

### Prove infrastructure was not recreated

For each infrastructure service:

```text
frontend
db
redis-cache
redis-queue
```

Compare its current container ID with the ID captured before recreation.

Required result:

```text
before ID equals after ID
service remains running
```

For `configurator` and `create-site`, prove the before and after container-ID sets are identical.

Required markers:

```text
PRODUCTION_INFRASTRUCTURE_CONTAINERS_UNCHANGED
PRODUCTION_ONE_SHOT_SETUP_SERVICES_NOT_RUN
```

## Phase 13 — prove the candidate backend directly

Before involving nginx, prove the candidate backend itself is responding.

Run the request inside the backend container against:

```text
http://localhost:8000/api/method/ping
```

Provide the site through the expected Frappe request header.

Example:

```bash
./bin/prod-compose.sh exec \
  -T \
  backend \
  bash -lc '
    curl \
      -fsS \
      -H "X-Frappe-Site-Name: erp.telectro.co.za" \
      http://localhost:8000/api/method/ping
  '
```

Required response:

```json
{"message":"pong"}
```

This proves:

```text
candidate backend process
→ Gunicorn/Frappe
→ site resolution
→ application response
```

It does not yet prove nginx routing.

Required marker:

```text
PRODUCTION_DIRECT_CANDIDATE_BACKEND_PING_OK
```

## Phase 14 — reload nginx in the unchanged frontend container

The frontend container must normally remain unchanged during a runtime release.

However, the running nginx workers may retain the IP address of the removed backend container.

Docker DNS can already resolve `backend` to the new IP while nginx workers continue routing to the old IP.

Therefore, an nginx reload is mandatory after every backend recreation.

### Capture the current frontend and backend identities

Record:

```text
frontend container ID
backend container ID
current backend Docker-network IP
frontend DNS result for backend
```

The frontend container ID must still match the ID captured before runtime recreation.

### Validate nginx configuration

Run:

```bash
docker exec <frontend-container-id> \
  nginx -t
```

Do not reload when nginx configuration validation fails.

Required marker:

```text
PRODUCTION_FRONTEND_NGINX_CONFIGURATION_OK
```

### Reload nginx

Run:

```bash
docker exec <frontend-container-id> \
  nginx -s reload
```

This sends a reload signal to nginx in the existing frontend container.

It must not recreate the frontend container.

Required marker:

```text
PRODUCTION_FRONTEND_NGINX_RELOAD_OK
```

### Wait for routed application recovery

Test the internal production frontend binding with the correct Host header:

```bash
curl \
  -fsS \
  -H "Host: erp.telectro.co.za" \
  http://192.168.0.11:8080/api/method/ping
```

Use a bounded retry loop because the first request immediately after reload may still be handled by an old worker.

Required response:

```json
{"message":"pong"}
```

After success, prove:

```text
frontend container ID is unchanged
backend container is still healthy
runtime restart counts remain 0
```

Required markers:

```text
PRODUCTION_CANDIDATE_FRONTEND_ROUTE_OK
PRODUCTION_FRONTEND_CONTAINER_ID_UNCHANGED
PRODUCTION_RUNTIME_HEALTHY_AFTER_NGINX_RELOAD
PRODUCTION_RUNTIME_SWITCH_OK
```

## Diagnosing a 502 after backend recreation

Do not immediately classify a routed `502 Bad Gateway` as a defective runtime image.

First compare:

```text
direct backend ping
current backend Docker-network IP
frontend DNS resolution for backend
nginx error-log upstream IP
```

The proven stale-upstream pattern is:

```text
direct backend ping:
200 {"message":"pong"}

current backend IP:
new IP

frontend DNS result:
new IP

nginx error log:
old removed backend IP

frontend route:
502 Bad Gateway
```

In that state:

- the candidate backend is healthy;
- Docker DNS is current;
- nginx workers have retained the previous backend IP.

Recovery:

```bash
docker exec <frontend-container-id> nginx -t
docker exec <frontend-container-id> nginx -s reload
```

Then wait for the routed ping to return `pong`.

Do not recreate the frontend merely to refresh backend resolution unless nginx reload fails and diagnostics justify recreation.

## Pre-migration rollback

The runtime switch must have an automatic or immediately executable rollback path before migration begins.

This rollback applies only while no candidate migration has run.

### Rollback triggers

Rollback should be initiated when any of these remain unresolved:

```text
candidate backend does not become healthy
one or more runtime services do not remain running
candidate runtime restart counts increase
direct backend ping fails
nginx configuration validation fails
routed frontend ping does not recover
unexpected infrastructure containers were recreated
one-shot setup services ran
candidate image assignment is inconsistent
```

### Restore the previous environment

Restore the exact `.env.production` backup created for this release.

Prove:

```text
ERPNEXT_IMAGE contains the previous image
the restored file matches the backup
Compose renders the previous runtime image
```

Required marker:

```text
ROLLBACK_ENVIRONMENT_RESTORED
```

### Recreate the previous runtime

Recreate only:

```text
backend
websocket
queue-short
queue-long
scheduler
```

Wait for:

```text
all five services running
all five services on the previous image
backend healthy
restart counts stable
```

Required markers:

```text
ROLLBACK_PREVIOUS_RUNTIME_RECREATED
ROLLBACK_PREVIOUS_BACKEND_HEALTHY
```

### Reload nginx after rollback recreation

Rollback recreates backend again and can assign yet another Docker-network IP.

Therefore, rollback must also:

```bash
docker exec <frontend-container-id> nginx -t
docker exec <frontend-container-id> nginx -s reload
```

Wait for:

```text
routed HTTP 200
{"message":"pong"}
```

Prove the frontend container ID remained unchanged.

Required markers:

```text
ROLLBACK_FRONTEND_NGINX_RELOADED
ROLLBACK_FRONTEND_ROUTE_RECOVERED
ROLLBACK_FRONTEND_CONTAINER_UNCHANGED
AUTOMATIC_RUNTIME_ROLLBACK_OK
```

A rollback that restores a healthy direct backend but leaves nginx returning `502` is incomplete.

### Stop after rollback

After successful pre-migration rollback:

- preserve all candidate evidence;
- do not retry immediately without diagnosing the failure;
- record the previous image as active;
- record that migration was not run;
- keep the candidate image loaded for diagnosis;
- do not delete the fresh backup.

## Runtime switch gate

Migration may begin only after all of these agree:

```text
.env.production selects candidate image
rendered Compose selects candidate image
five running runtime services use candidate image
backend is healthy
direct backend ping returns pong
nginx configuration is valid
nginx has been reloaded
routed frontend ping returns pong
frontend container ID is unchanged
database and Redis container IDs are unchanged
one-shot setup services were not run
restart counts are stable
```

Required final marker before migration:

```text
PRODUCTION_RUNTIME_READY_FOR_MIGRATION
```

## Phase 15 — capture the pre-migration application state

Before running migration, capture the relevant current database state when the release changes existing fixtures, configuration records, roles, Reports, or Workspaces.

This proof establishes:

```text
what production contained before migration
what the candidate fixture is expected to change
whether the migration later imported the intended state
```

Use site-aware Bench commands.

Supported methods:

```text
prod-bench.sh ... mariadb
prod-bench.sh ... console
```

Do not use a raw Python process with manually constructed `frappe.init()` and `frappe.connect()` as the default production-validation method.

That method can bypass Bench’s normal execution context and fail before database connection because logging, site paths, or environment state were not initialized correctly.

The proven failure was:

```text
FileNotFoundError:
/home/frappe/logs/database.log
```

That failure indicated an invalid validation context, not a database or migration failure.

### SQL capture

Use MariaDB for simple checks such as:

```text
record existence
row counts
flag values
field values
child-row counts
ordered child rows
```

Example:

```bash
./bin/prod-bench.sh \
  --site erp.telectro.co.za \
  mariadb \
  --skip-column-names \
  --execute 'SELECT 1;'
```

### Frappe document capture

Use Bench console when validation requires:

```text
Frappe DocType loading
Workspace JSON content
child-table semantics
ordered links
document properties
report execution
permission-aware framework behavior
```

The console input must:

- use the current site selected by Bench;
- print an exact completion marker;
- exit explicitly;
- be captured into evidence.

Because an interactive console can return status `0` despite confusing output, validate its output separately.

Reject evidence containing:

```text
Traceback
AssertionError
OperationalError
ProgrammingError
FileNotFoundError
SyntaxError
```

unless the occurrence is an intentionally quoted diagnostic string rather than an actual failure.

Required markers:

```text
PRE_MIGRATION_DATABASE_STATE_CAPTURED
PRE_MIGRATION_SITE_AWARE_VALIDATION_OK
```

This phase is required when later proof depends on comparing old and new database state.

## Phase 16 — run the production migration

Use the repository-controlled migration wrapper:

```bash
SITE=erp.telectro.co.za \
  ./bin/prod-migrate.sh
```

The wrapper must execute migration through the production Bench and Compose context.

Do not replace it with:

```text
plain docker compose exec
raw Python
a local development Bench command
an unqualified bench migrate
```

unless a separately reviewed incident procedure requires it.

### Migration evidence

Capture the complete output in the release evidence file.

Expected migration activity may include:

```text
updating DocTypes
updating dashboards
updating customizations
running patches
importing fixtures
executing after_migrate hooks
queuing Helpdesk search-index rebuilding
```

A queued asynchronous Helpdesk search-index rebuild is not itself a migration failure.

### Network-dependent migration activity

Helpdesk migration can trigger NLTK asset downloads such as:

```text
averaged_perceptron_tagger_eng
punkt_tab
brown
```

This introduces a possible outbound-network dependency during migration.

The release plan must therefore consider:

- whether production outbound internet is available;
- whether the required assets are already present;
- whether future runtime images should bake these assets into the image;
- whether an interrupted download could leave migration incomplete.

Do not interrupt migration merely because these downloads take longer than schema updates.

### Migration success conditions

Required proof:

```text
migration command exits successfully
no unresolved traceback appears
after_migrate hooks complete
backend remains running
backend remains healthy
backend remains on candidate image
runtime restart counts remain stable
frontend route remains available
```

Required markers:

```text
PRODUCTION_MIGRATION_COMMAND_OK
PRODUCTION_MIGRATION_HOOKS_OK
PRODUCTION_RUNTIME_HEALTHY_AFTER_MIGRATION
PRODUCTION_MIGRATION_OK
```

### Migration failure rule

Once migration has started, do not automatically rerun it merely because a later validation step fails.

First determine:

```text
whether migration completed
which patch or fixture stage failed
whether the database transaction committed
whether the failure occurred only in the validator
whether the release remains backward compatible
```

A failure after:

```text
PRODUCTION_MIGRATION_COMMAND_OK
```

must be treated as a post-migration state until proven otherwise.

Do not automatically switch back to the previous image without evaluating database compatibility.

## Phase 17 — clear the production site cache

After successful migration, clear the production site cache:

```bash
./bin/prod-bench.sh \
  --site erp.telectro.co.za \
  clear-cache
```

This is the standard order:

```text
migrate
→ clear-cache
→ database semantic verification
→ functional execution
→ health proof
→ browser proof
```

Required proof:

```text
clear-cache exits successfully
backend remains running
backend remains healthy
backend remains on candidate image
runtime container IDs remain unchanged
runtime restart counts remain stable
```

Required markers:

```text
PRODUCTION_CLEAR_CACHE_OK
PRODUCTION_RUNTIME_HEALTHY_AFTER_CACHE_CLEAR
```

A cache-clear failure occurs after migration.

Do not rerun migration automatically to resolve it.

## Phase 18 — verify the migrated database state

Validate the exact production database state expected from the release.

The validation must be specific to the changed artifact.

Generic proof such as:

```text
the table exists
the document can be loaded
the fixture file was present in the image
```

is not enough.

### Supported site-aware validation methods

Use:

```bash
./bin/prod-bench.sh \
  --site erp.telectro.co.za \
  mariadb
```

for direct SQL assertions.

Use:

```bash
./bin/prod-bench.sh \
  --site erp.telectro.co.za \
  console
```

for Frappe document and framework semantics.

### Report validation

For changed Reports, validate as applicable:

```text
exact Report name
Report type
reference DocType
module
standard/custom state
disabled flag
prepared-report flag
query content or query length
report script content or absence
exact role count
exact role order where order is meaningful
```

Required markers should be release-specific, for example:

```text
PRODUCTION_REPORT_ROW_OK
PRODUCTION_REPORT_ROLES_OK
PRODUCTION_REPORT_DATABASE_STATE_OK
```

### Workspace validation

For changed Workspaces, validate as applicable:

```text
exact Workspace name
expected role rows
Workspace content parses as JSON
expected card names
expected card widths
expected card order where intentional
exact Card Break count
expected link count
exact link labels
exact link targets
exact link types
hidden flags
absence of stale labels or spelling
```

For card layout, validate only the cards intentionally controlled by the release.

Do not fail merely because unrelated legitimate Workspace cards exist.

For roles, distinguish:

```text
exact expected role set
```

from:

```text
one required role among other legitimate roles
```

The validator must reflect the actual fixture contract rather than being stricter than the intended behavior.

Required markers should be release-specific, for example:

```text
PRODUCTION_WORKSPACE_DATABASE_STATE_OK
PRODUCTION_WORKSPACE_LINKS_OK
PRODUCTION_WORKSPACE_ROLES_OK
```

### DocType and fixture validation

For other fixture or DocType changes, validate:

```text
document exists
exact expected field values
expected child rows
no duplicate child rows
disabled/enabled state
permissions or roles where applicable
schema fields exist
stale records are absent when removal was intended
```

### Validation output rules

The validator must:

- print the inspected values;
- print exact success markers;
- fail when an assertion fails;
- capture output to evidence;
- reject tracebacks and known database errors;
- leave production data unchanged.

Required generic markers:

```text
PRODUCTION_DATABASE_SEMANTIC_VALIDATION_OK
PRODUCTION_CHANGED_ARTIFACT_DATABASE_STATE_OK
```

## Phase 19 — execute the changed behavior through Frappe

Database presence alone does not prove that the changed behavior works.

Execute the relevant operation through the Frappe framework.

Examples:

```text
run a Query Report
run a Script Report
load a Workspace document
call a whitelisted method
execute a fixture-backed function
perform a read-only permission check
```

The smoke must be narrowly scoped and should avoid creating operational production records.

### Report execution

For a changed Report, prove:

```text
the Report resolves
the report code executes
the query or script does not error
the returned column structure is valid
the returned row structure is valid
```

An empty result is acceptable when no production records match.

Examples:

```text
columns=12
rows=0
```

or a browser state such as:

```text
Nothing to show
```

can represent successful execution.

The important proof is absence of:

```text
missing Report
SQL error
Python exception
permission error
invalid column structure
invalid filter handling
```

### Production data rule

Do not create fake operational tickets merely to force a report to show rows.

For UI and report proof:

- use existing legitimate production records where available;
- accept valid empty-state execution;
- create only a minimal clearly labelled smoke-test record when absolutely necessary;
- remove or archive that record according to the agreed production data rule;
- never reuse a smoke-test record as normal operational history.

### Console execution caution

When Bench console is used:

- include an exact marker;
- capture all output;
- exit explicitly;
- check output for actual tracebacks;
- do not rely only on status `0`;
- do not depend on an interactive exit prompt in unattended automation.

Preferred long-term direction:

```text
repository-controlled non-interactive validation helper
```

or:

```text
proven bench execute target
```

Required markers:

```text
PRODUCTION_CHANGED_FUNCTION_EXECUTION_OK
PRODUCTION_FUNCTIONAL_SMOKE_OK
```

## Phase 20 — prove runtime and HTTP health after migration

After database and functional validation, re-prove the complete runtime boundary.

### Runtime services

For:

```text
backend
websocket
queue-short
queue-long
scheduler
```

record and validate:

```text
container ID
configured image
running state
health state where defined
restart count
```

Required conditions:

```text
all five use candidate image
all five are running
backend is healthy
restart counts remain 0
container IDs match the post-switch IDs
```

### Infrastructure services

For:

```text
frontend
db
redis-cache
redis-queue
```

prove:

```text
container IDs match the pre-release IDs
services remain running
database remains healthy where a health check exists
```

### Direct backend proof

Repeat the direct request:

```text
backend container
→ localhost:8000
→ Frappe
→ pong
```

Required marker:

```text
POST_MIGRATION_DIRECT_BACKEND_PING_OK
```

### Internal routed frontend proof

Repeat:

```bash
curl \
  -fsS \
  -H "Host: erp.telectro.co.za" \
  http://192.168.0.11:8080/api/method/ping
```

Required marker:

```text
POST_MIGRATION_FRONTEND_ROUTE_OK
```

### External HTTPS proof

Test the public route:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  --max-time 20 \
  https://erp.telectro.co.za/api/method/ping
```

Required response:

```json
{"message":"pong"}
```

This proves the path through:

```text
public DNS
→ HTTPS termination
→ Telectro reverse proxy
→ VM frontend
→ nginx
→ candidate backend
→ Frappe
```

It does not replace role, permission, or browser verification.

Required markers:

```text
POST_MIGRATION_RUNTIME_SERVICES_OK
POST_MIGRATION_INFRASTRUCTURE_UNCHANGED
POST_MIGRATION_DIRECT_BACKEND_PING_OK
POST_MIGRATION_FRONTEND_ROUTE_OK
POST_MIGRATION_EXTERNAL_HTTPS_OK
POST_MIGRATION_RUNTIME_HEALTH_OK
```

## Phase 21 — perform browser-level verification

Browser proof is mandatory for a release that changes:

```text
Workspace layout
Workspace links
Reports
report navigation
roles
permissions
customer portal behavior
partner workspace behavior
labels
actions
frontend behavior
```

Use a fresh browser state.

Depending on the change, use:

```text
hard refresh
private/incognito window
sign out and back in
a role-appropriate production user
```

Do not rely on a browser tab opened before migration or cache clearing.

### Workspace proof

For a Workspace change, verify:

```text
the correct route opens
the expected role can access it
the intended card layout is visible
card headings are correct
links are present
spelling is correct
unrelated cards remain intact
```

### Report proof

Open every changed or newly linked Report and verify:

```text
route opens
title is correct
no permission error
no missing-report error
no server exception
report executes
empty state is acceptable when valid
filters render when expected
```

### Permission proof

Where roles or visibility changed, test:

```text
one intended positive-access user
one intended negative-access user
```

Do not claim negative permission proof when no suitable restricted user exists.

Record such proof as:

```text
deferred
blocked by test-user availability
not verified
```

rather than assuming it passed.

### Customer and Partner proof

For customer-portal or Partner changes, use the correct account type and route.

Do not substitute an Administrator or System Manager browser session for:

```text
Customer Website User
Partner user
restricted technician
restricted coordinator
```

when the purpose is to prove role containment.

### Screenshot evidence

For UI-sensitive changes, retain screenshots showing:

```text
the Workspace or portal state
the changed labels or controls
each changed Report successfully loaded
the relevant empty or populated execution state
```

Screenshot filenames should use the exact verified UI spelling.

Avoid stale or incorrect names such as:

```text
Oversite
Worksapce
```

when the verified UI says:

```text
Oversight
Workspace
```

Required markers:

```text
PRODUCTION_BROWSER_ROUTE_OK
PRODUCTION_BROWSER_CHANGED_UI_OK
PRODUCTION_BROWSER_REPORT_EXECUTION_OK
PRODUCTION_BROWSER_ROLE_PROOF_OK
```

Use only the markers applicable to the release.

Final browser gate:

```text
PRODUCTION_BROWSER_VERIFICATION_OK
```

## Phase 22 — reconcile release metadata and source markers

The production VM can contain:

```text
a host-side deployed application artifact
an immutable runtime image
source markers
a deployment manifest
```

These are related but not automatically identical states.

Do not update a source marker to claim that the host application tree contains a commit when its corresponding files were not actually deployed there.

For a normal image-only Type C release:

- the running application source comes from the immutable image;
- the image manifest records the source commit;
- the staged source artifact records the build source;
- the host `apps/` directory may still reflect an earlier separately deployed artifact;
- source markers must describe the state they actually identify.

Record separately:

```text
runtime image source commit
staged source-artifact commit
host application-artifact commit
running image tag
migration status
database validation status
```

Where `.source-branch` or `.deploy-manifest.txt` already exist, inspect their defined purpose before updating them.

Do not use one marker to represent both:

```text
host source tree
```

and:

```text
runtime image source
```

unless the deployment model explicitly makes those states identical.

Long-term preferred approach:

```text
machine-readable release manifest
```

containing:

```text
release_id
created_at
source_branch
commit_sha
previous_image_tag
candidate_image_tag
image_config_digest
archive_sha256
source_artifact_sha256
host_source_artifact_commit
site_name
migration_required
migration_completed
changed_artifacts
expected_runtime_services
evidence_paths
browser_proof_state
```

Required marker:

```text
PRODUCTION_RELEASE_METADATA_RECONCILED
```

## Phase 23 — write the final evidence record

Create a final evidence file under:

```text
/opt/telectro/erpnext/deploy-evidence
```

Recommended path:

```text
/opt/telectro/erpnext/deploy-evidence/<release-id>-final-state.txt
```

The final record must contain:

```text
UTC timestamp
release ID
source branch
full commit SHA
previous image
candidate image
archive SHA-256
config digest
source-artifact SHA-256
backup prefix
backup artifact paths
backup artifact sizes
backup artifact SHA-256 values
environment backup path
active ERPNEXT_IMAGE
rendered runtime image
five runtime service names
five runtime container IDs
five runtime configured images
five runtime states
five runtime restart counts
backend health
frontend container ID
database container ID
Redis container IDs
direct backend ping
internal frontend ping
external HTTPS ping
migration status
cache-clear status
database validation markers
functional smoke markers
browser proof state
release metadata state
rollback point
operator
```

The evidence must explicitly state whether:

```text
browser proof completed
negative role proof completed
negative role proof deferred
source-only correction remains unreconciled
post-migration rollback was required
```

Required final marker:

```text
FINAL_PRODUCTION_DEPLOYMENT_STATE_OK
```

A release is not complete merely because the application appears to work.

The final evidence path and marker must be recorded.

## Phase 24 — close the release operationally

After final evidence passes:

- record the deployed commit;
- record the immutable image tag;
- record the backup prefix;
- record the migration result;
- record the final evidence path;
- record browser proof;
- record any deferred role proof;
- record any follow-up operational issue;
- update the daily handover;
- retain the previous image and backup until the agreed retention point.

Do not immediately delete:

```text
previous runtime image
candidate archive
source artifact
environment backup
database backup
deployment evidence
```

Retention and cleanup should occur through a separate reviewed maintenance procedure.

Required marker:

```text
PRODUCTION_RELEASE_OPERATIONALLY_CLOSED
```

## Post-migration rollback boundary

Once migration has run, restoring only the previous image may be unsafe.

The rollback decision must evaluate:

```text
schema changes
patch execution
fixture imports
field removals
data transforms
permission changes
backward compatibility
file changes
search-index state
```

### Image-only rollback after migration

An image-only rollback may be acceptable only when it is proven that:

- the migration introduced no incompatible schema or data changes;
- the previous image can operate against the migrated database;
- fixtures are backward compatible;
- no removed code is required by the migrated state;
- the rollback has been reviewed and documented.

Do not assume fixture-only means automatically backward compatible.

### Full state restore

A general post-migration restore may require:

1. declare a controlled production incident;
2. prevent new application writes;
3. stop the five application runtime services;
4. preserve failed-release evidence;
5. verify the exact pre-release backup prefix;
6. restore the database backup;
7. restore public files when changed;
8. restore private files when changed;
9. restore site configuration when required;
10. restore the previous `.env.production`;
11. render and prove the previous image;
12. recreate only the five runtime services;
13. wait for backend health;
14. prove direct backend pong;
15. validate and reload nginx;
16. prove routed pong;
17. verify database/application compatibility;
18. perform browser smoke proof;
19. write incident and restore evidence.

A database restore must not be run casually over a live writable site.

It requires:

```text
explicit incident decision
known backup identity
controlled write boundary
restore commands appropriate to the backup format
post-restore proof
```

This runbook defines the decision boundary but does not replace a dedicated database-restore runbook.

### Post-migration rollback evidence

Record:

```text
why rollback was required
whether migration completed
whether database restore was required
which backup was restored
which image became active
whether files were restored
nginx reload result
direct and routed ping result
browser smoke result
```

Required marker after a successful full restore:

```text
POST_MIGRATION_PRODUCTION_RESTORE_OK
```

## Deployment completion gate

A durable production release is complete only when all applicable layers agree:

```text
merged Git commit
source artifact
immutable runtime image
archive checksum
config digest
production environment
rendered Compose state
five running runtime containers
unchanged infrastructure containers
frontend nginx state
migrated database
cache state
database semantic proof
functional smoke proof
direct backend endpoint
internal routed endpoint
external HTTPS endpoint
browser and role proof
release metadata
deployment evidence
daily handover
```

Any unresolved disagreement between those layers means the release is incomplete or ambiguous.

Final release markers:

```text
FINAL_PRODUCTION_DEPLOYMENT_STATE_OK
PRODUCTION_RELEASE_OPERATIONALLY_CLOSED
```
