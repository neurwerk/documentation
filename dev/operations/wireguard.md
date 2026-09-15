# Static WireGuard Pilot

Base's optional `charts/wireguard/` gateway implements a static one-device,
Forgejo-HTTPS-only pilot. Source availability is not deployment acceptance.
No active client selects this package, and it remains excluded from stable
release eligibility. Do not contact clusters, change DNS/firewalls, or provision
keys without separate authorization. The user executes EC2 changes with our help;
agents do not SSH to EC2.

## Verified Source

[Base PR #141](https://github.com/neurwerk/k8s_stack_base/pull/141) merged as
`763c55e0079a5ee24b9eaed0f92a2ff946c96ef5` on 2026-09-15, closing bounded issue
#140. Full local `mise exec -- make check` passed: 84 chart tests, 10 security
tests, 59 platform tests with two existing tag-only skips, and four embedded
Node tests. All seven `mise exec -- pre-commit run --all-files` hooks passed.
Independent review found and verified fixes for CI fixture ownership and an
unavailable HTTP-server applet; hosted packet execution then caught the down-link
route-order bug, which was corrected before final re-review and merge.

[Required CI run 34942789332](https://github.com/neurwerk/k8s_stack_base/actions/runs/34942789332)
passed on reviewed head `8fa925a10a75f832e2c118f85e509f247f878d03`, including
`uv run --frozen python tests/wireguard/packets.py`. The exact published image
started with the chart's real firewall, mounted root-owned key and restricted
capabilities. The test verified allowed TCP 443 forwarding, denied unapproved
port/direct destination/unapproved peer, gateway stop, and empty-peer restart.
The synthetic TCP backend was not Forgejo or a TLS/login test. All three default
stage renders were byte-for-byte unchanged. No cluster, EC2, DNS, credential,
platform release, image publication or client-adoption operation was performed.

## Runtime Contract

The independent `releases/namespaces/wireguard/` and `releases/wireguard/` packages
are absent from default stages. Defaults are `enabled: false`, `replicas: 0`,
and `peers: []`. The HelmRelease depends on Forgejo and reads the namespace-local
`wireguard-product-values` ConfigMap. The chart accepts at most one peer with
an owner, public key and IPv4 address; no device private key is accepted.

LinuxServer WireGuard `1.0.20260223-r0-ls122` is pinned to published OCI index
`sha256:dca67384e3e9a5bcc288461fa983e6fcb0e248e5a2d8e5b3e5d3f753bfac3e35`.
The chart overrides upstream initialization with its small shell startup script;
no upstream key generator, configuration generator, CoreDNS or management service
runs. There is no runtime package installation or first-party image publication.
UID 0 and `NET_ADMIN` are required for network namespace configuration; all other
capabilities are dropped, privilege escalation is disabled, the filesystem is
read-only, and no host network/mount or Kubernetes API token is granted.

Startup first removes any stale `wg0`, installs default-drop nftables input,
output and forwarding chains, configures the static peer and key, brings up
WireGuard, then adds its `/32` return route. The Pod's routing sysctl is set by Kubernetes
before process startup, but decrypted traffic cannot enter before those rules.
Graceful shutdown removes the interface; Pod deletion is the required stop gate,
including if a process was killed before it could clean up.

Peer source addresses are authenticated by WireGuard and checked before NAT.
Only TCP 443 to `virtualIP` is DNATed to `forgejoServiceIP:443` and masqueraded
as the gateway Pod; direct Service addressing is not a grant. Reverse traffic is
limited to that established flow. IPv6, SSH, peer-to-peer, gateway management and
unrelated transit have no allowance. Kubernetes egress additionally selects
Forgejo's exact namespace and Pod labels on destination Pod TCP 3000, so stale
Service-address reuse must not authorize another application's Pods.

## Before Activation

1. Obtain separate operational approval and confirm the real network facts:
   unused outer UDP port, node address/exposure, allowed post-SNAT outer sources,
   non-overlapping unicast peer/virtual addresses, current Forgejo Service IP,
   first device owner/public key, scoped Mac resolution and nested-tunnel MTU.
   Chart fixtures are synthetic, not suggested production allocations.
2. Verify node kernel WireGuard/nftables support, Pod security admission and
   kubelet allowance for unsafe Pod-local `net.ipv4.ip_forward`. The workload
   does not load modules or change kubelet configuration. Verify the CNI supports
   exact Pod egress/ingress for this double-NAT path before granting access.
3. Implement approved persistent server-key delivery using the existing
   [OpenBao/ESO flow](../architecture/secrets.md), not a new recovery service.
   `wireguard.serverKeySecret` names a namespace-local Secret with `privateKey`.
   A selection-gated provisioning catalog/SecretStore/ExternalSecret is still
   pending; the gateway does not create or rotate credentials. Readiness of that
   delivery stage must precede the gateway stage. Keep the Mac key on the Mac.
4. Select Forgejo's `httpsClients` peer with namespace `wireguard` and Pod labels
   `app.kubernetes.io/name: wireguard`, `app.kubernetes.io/instance: wireguard`.
   Set Forgejo's `externalGateway.enabled: false`, remove other direct human
   bypasses, and retain only separately approved workload consumers. Policies
   are additive; DNS removal alone cannot close an existing route.
5. Prepare user-applied UDP forwarding and symmetric return routing without
   changing infrastructure WireGuard peers or public HAProxy services. ClusterIP
   is the default; optional NodePort requires an explicit port and uses Local
   traffic policy, so the chosen node must actually host the gateway. Confirm
   all outer interfaces/IP families remain within the approved boundary.
6. Preserve the canonical hostname, native Forgejo TLS, Keycloak origin and
   OAuth callback. Use only an exact scoped Mac mapping to the virtual IP and
   client `AllowedIPs` for that `/32`; do not replace ordinary/corporate DNS or
   use client routes as authorization. Public DNS-01 certificate renewal needs
   no public Forgejo route. Verify actual resolution, renewal and login later.

## Manual Changes

1. Reconcile `wireguard.replicas: 0` through the approved client change and wait
   for every old gateway Pod to be deleted. Verify access has stopped. Do not
   force-delete an unreachable Pod and assume the process stopped; establish
   node isolation first if necessary. Do not rely on a scale command that Flux
   could immediately undo.
2. Only while stopped, edit the current approved peer list or other runtime
   inputs. Removing the one peer means `peers: []`. For target Service changes
   or recreation, keep the gateway stopped until the new IP, HTTPS port and
   destination identity have been verified. Key rotation is also stop/update/start.
3. Reconcile `replicas: 1` only after the new configuration and required Secret
   delivery are confirmed. Inspect process-local probes, events and safe logs;
   never dump WireGuard configuration or Secret values. A failed restart leaves
   access closed. Verify both allowed access and denial for the removed peer.

There is no controller, automatic expiry, lease, watcher, hot reload or automatic
revocation deadline. Recreate prevents rolling overlap but does not replace the
manual sequence. Never restore historical peers during an application rollback;
if the approved list is untrusted, start empty and approve the device again.
This is an operator recovery procedure, not an immutable permission authority.
Removing tunnel access does not revoke separate native application credentials.

## Acceptance

Base's normal full checks cover render contracts. Required CI also runs a
disposable Docker test against the exact image and rendered startup files for
allowed forwarding, denied ports/direct destinations/unapproved peers, stopping
and empty-list restart. It uses synthetic ephemeral keys and no host networking.
The workspace VM cannot run that dataplane test; do not claim local packet proof.

Live acceptance remains required: verify encrypted UDP return paths, CNI-visible
gateway Pod identity, destination isolation after NAT, exact TLS identity,
browser login/Git HTTPS and normal transfers at the selected MTU. Test altered
client routes, tunnel-off behavior, removal during an open connection, and
unrelated network/port denial. Check public applications and their login/files
remain unchanged, then inspect Flux, workloads, storage, events and logs.
Do not broaden policy to node ranges if the CNI loses the intended Pod identity.

The first pilot does not privatize other administration. Later whole-tool Grafana
reuse is simpler than LibreChat's admin callback/API on its public chat origin.
AgentGateway's unauthenticated powerful port 15000 still requires the existing
authentication or path-proxy boundary, preserving Studio analytics; a private
hostname alone is insufficient. These are later slices, not pilot prerequisites.
