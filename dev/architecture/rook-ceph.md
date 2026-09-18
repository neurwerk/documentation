# Rook/Ceph Storage

Rook/Ceph provides block, snapshot, and S3-compatible object storage. The
current deployment uses one storage node and one raw device. It is not highly
available.

## Ownership

The platform owns the chart, CRDs, storage classes, object store, Gateway, and
readiness Job:

```text
base/charts/rook-ceph/
base/releases/rook-ceph/
```

A deployable client configuration provides the approved Kubernetes node and
raw-device path:

```text
infrastructure/storage/rook-ceph/values.yaml
```

Use a stable path such as `/dev/disk/by-id/...`. The chart requires one explicit
node and device and never discovers or consumes all devices automatically.

## Topology

The Ceph cluster has one monitor, one manager, one RGW instance, and replica
size `1`. Block volumes, snapshots, and object data share the same physical
failure domain.

This topology does not tolerate storage-node or device failure. Retention
policies reduce accidental deletion risk but do not provide backups or disaster
recovery.

## Storage Interfaces

| Resource | Name | Deletion behavior |
| --- | --- | --- |
| General RBD `StorageClass` | `infra-rook-ceph-rbd` | `Delete` reclaim policy |
| OpenBao RBD `StorageClass` | `infra-rook-ceph-rbd-openbao` | `Retain` reclaim policy |
| RBD `VolumeSnapshotClass` | `infra-rook-ceph-rbd-snapshots` | `Delete` deletion policy |
| Object bucket `StorageClass` | `infra-rook-ceph-object-bucket` | `Retain` reclaim policy |

The general RBD class supports volume expansion and waits for the first
consumer before binding. OpenBao uses the same RBD pool through its retained
class.

The object-bucket class is a provisioning interface, not one shared bucket.
Each `ObjectBucketClaim` creates a bucket and namespace-local credentials. These
controller-generated Secrets are runtime data and must not be stored in Git or
Helm values. The object store also preserves its pools when the
`CephObjectStore` resource is deleted.

## Object Storage

Current object-storage consumers include:

- PII model bundles;
- LibreChat files;
- optional Code Interpreter files;
- Langfuse object data;
- OpenSearch archive snapshots, which expire after 90 days.

When the external object Gateway is enabled, the Rook chart creates an HTTPS
`Gateway` and `HTTPRoute` to the internal RGW Service. The public hostname is a
client-owned value.

When LibreChat object storage is enabled, it requires this browser-reachable
HTTPS endpoint because it returns presigned file URLs. Its core chart creates
the retained `frontend-librechat-files-object-bucket-claim` and reads the
generated Secret directly. Default files, avatars, images, and documents use
this bucket.

When composed and enabled, Code Interpreter creates a separate retained bucket.
Only its file server receives those credentials. RAG stores vectors in the
`librechat_rag` PostgreSQL database; its `/app/uploads` directory is temporary.

## Data Lifecycle

PVC retention is configured by each workload chart. There is no platform-wide
rule that retains every production PVC:

- `helm.sh/resource-policy: keep` prevents Helm from deleting that resource;
- StatefulSet claim retention protects PVCs during StatefulSet deletion or
  scale-down when configured;
- a `Retain` reclaim policy preserves the backing volume after its claim is
  released;
- the general RBD class can delete the backing volume when its PVC and PV are
  deleted.

Check the owning chart before deleting a release, StatefulSet, PVC, snapshot,
or `ObjectBucketClaim`. None of these policies replaces an off-cluster backup.

## Readiness

The release runs a finite post-install and post-upgrade readiness Job. It waits
for the Ceph cluster, object store, main RBD pool, PII model bucket and users,
model-sync credentials, and the Rook, CSI, and RGW deployments. It then checks
RGW reachability and performs an RBD write/read test through a temporary PVC.
The Job attempts to remove its temporary test resources on exit.

This Job gates Helm installation and upgrades. It is not continuous storage
monitoring.

The Ceph 20.2.4 upgrade requires current observed generations for the cluster and
object store, the selected running image, and completed daemon-key migration.
Readiness checks the admin, monitor, manager, OSD, crash-collector and exporter
key statuses plus the object gateway's own key status. Each must report the
requested generation or newer and a key creation version of at least 20.2.4.
Already-secure keys do not need another rotation on every later patch upgrade.

After migration is confirmed, the Job requires a newer health sample no older
than three minutes. It accepts `HEALTH_OK` with no reported problems, or
`HEALTH_WARN` containing only these warning-severity compatibility checks:

- `AUTH_INSECURE_ROTATING_SERVICE_KEY_TYPE`
- `AUTH_INSECURE_CLIENT_KEY_TYPE`
- `AUTH_INSECURE_KEYS_ALLOWED`
- `AUTH_INSECURE_KEYS_CREATABLE`

These warnings remain visible in Ceph and are named in readiness output. They
are not muted. Any other warning, any error, malformed or stale status, or an
incomplete migration blocks readiness. In particular, storage warnings such as
`BLUESTORE_SLOW_OP_ALERT` and the security errors
`AUTH_INSECURE_SERVICE_KEY_TYPE` and `AUTH_INSECURE_SERVICE_TICKETS` remain
blocking. The Job requires another fresh health sample after the RBD test.

Inspect the declared state with:

```bash
kubectl get cephclusters,cephblockpools,cephobjectstores -n infra-rook-ceph
kubectl get storageclasses,volumesnapshotclasses
kubectl get objectbucketclaims -A
```

## Ceph 20.2.4 Upgrade

Follow the [Rook CephX upgrade guide](https://rook.io/docs/rook/v1.20/Storage-Configuration/Advanced/cephx-key-rotation/).
Upgrade the Rook operator and matching CRDs to 1.20.7 first, and verify that the
new operator is running before adopting the separate Ceph 20.2.4 revision.
Keep Rook's upgrade checks enabled. The optional `rook` manager module is
disabled as recommended upstream for Ceph 20.2.2 through 20.2.4; this does not
disable the Rook Kubernetes operator.

Before an existing installation adopts the Ceph revision, inspect the current
daemon generation in the CephCluster spec and all the key statuses listed above,
without reading key material. For keys that still need migration, select an
`infraRookCeph.daemonKeyGeneration` greater than every existing key generation
and no lower than the persisted spec generation. The default `2` supports fresh
installations and previously unrotated generation-1 keys. Existing higher
generations require an explicit value. Preserve the selected generation on
retries and future upgrades; do not remove it or automatically increment it on
each reconciliation. Rook owns key rotation and the associated Secret updates.

CSI authentication keys retain `aes` compatibility; this upgrade does not
request CSI-key rotation or restrict allowed ciphers. Migrating CSI to
`aes256k` is a separate operation requiring Ceph-CSI 3.17.1 or newer and support
on every mounting node: Linux 7.0 or newer, or verified vendor backports, with
additional FIPS requirements. Core-daemon migration addresses the service-ticket
vulnerability without forcing that client migration. Rotating service-ticket
warnings can remain for two to three hours; do not wipe tickets to accelerate it.

Confirm current independent backups or explicit acceptance of data loss before
deployment. Downtime acceptance alone does not waive data protection, and a Git
rollback does not downgrade Ceph data or reverse key rotation. After deployment,
verify exact daemon versions, key-generation statuses, Flux reconciliation,
warnings, existing application data access, RGW requests, and manager memory.
The RGW update rejects unsigned `host` and `x-amz-*` headers in SigV4 requests;
test existing object-storage consumers rather than disabling that security fix.
This chart declares no RGW multisite topology; separately configured multisite
installations must follow the upstream coordinated-upgrade instructions.

## Model Publication

The tool in `tooling/cli_tools/media_downloader_uploader/` publishes verified
PII model bundles to the `pii-models` bucket. From that project, run:

```bash
uv run media-downloader-uploader
```

Select the Ceph RGW upload action and an explicit Kubernetes context. The tool
uploads model files and checksums before `manifest.yaml`. Model sync treats the
manifest as the bundle marker and independently verifies the bundle before
selecting it. Until a verified transformer bundle is selected, the PII Engine
remains available in bundled baseline mode.
