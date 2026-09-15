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

### Server-Key Integration Evidence

[Tooling PR #32](https://github.com/neurwerk/k8s_stack_tooling/pull/32) merged as
`0c0d5b35fc9e68b70e0cb48f3741e1888f7a287b`; [Base PR #143](https://github.com/neurwerk/k8s_stack_base/pull/143)
merged as `f3ad4196382da780c1ae073d845b2de221bad4e3`. Tooling's full setup-project
checks passed: frozen lock/sync, Ruff lint/format, type checks, 244 tests with
92.96% coverage, and source/wheel build. Its entire seven-project CI matrix and
Required CI passed in run `34944756901`. No package or image was published.

Base full checks passed with 85 chart tests, 10 security tests, 59 platform tests
(two existing tag-only skips), four Node tests and all seven pre-commit hooks.
Required CI run `34945436562` passed on head
`803b491e480904948e9086c33060777ce3dd943b`, including the unchanged isolated packet
test. Independent combined review cleared both repositories and this runbook
after the exact optional tooling prerequisite was recorded. All three default
stage renders remained byte-identical; no client composition was selected.
Key tests use an in-memory OpenBao fake and deterministic WireGuard key fixture,
not live OpenBao or operational key generation. Live ESO delivery and Mac setup
were not verified by those source checks; subsequent delivery evidence is below.

### Gateway Runtime

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
3. Provision the persistent server key using the implemented optional
   [OpenBao/ESO flow](../architecture/secrets.md), not a new recovery service.
   `wireguard.serverKeySecret` names a namespace-local Secret with `privateKey`.
   Use `wireguard-server-key` with the setup catalog described below. No live key
   has been provisioned by source implementation; delivery readiness must precede
   the gateway stage. Keep the Mac key on the Mac.
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

### Server-Key Setup

`openbao-stack-setup` `0.2.13` extends the existing schema-4 optional catalog;
use Tooling commit `0c0d5b35fc9e68b70e0cb48f3741e1888f7a287b`, merged in
[Tooling PR #32](https://github.com/neurwerk/k8s_stack_tooling/pull/32) and recorded
in Base's optional release prerequisite, not the older global prerequisite or a moving checkout. Neither
merging source nor building the CLI package authorizes credential operations.

1. With separate staging authorization, compose Base's independent namespace
   package and `releases/wireguard/secret-sync/`, plus a client-owned
   `wireguard-product-values` ConfigMap in namespace `wireguard`. The namespace
   requests the existing OpenBao CA bundle; ESO uses a namespace-local store,
   role `wireguard`, ServiceAccount `wireguard-external-secrets`, audience `openbao`.
2. In the ConfigMap's `values.yaml`, set `wireguard.enabled: true`,
   `wireguard.serverKeySecret: wireguard-server-key`, `wireguard.replicas: 0` and
   `wireguard.peers: []`. These are setup selections, not permission to run the
   gateway. Leave its HelmRelease stage unselected/suspended while actual network
   facts are unknown; enabling its chart without those facts fails rendering.
   Do not duplicate the selector in shared values or override it inline.
3. Run the existing `stack-setup reconcile` ceremony from the trusted workstation
   using explicit context/client and two approved custodian packages. Use the
   [documented command and custody rules](openbao.md#reconcile-the-catalog).
   This reconciles the full existing catalog, including its established
   infrastructure side effects; it is not a WireGuard-only operation. Fresh
   installations can select the same catalog during authorized bootstrap.
4. The tool creates only a missing `wireguard/internal:privateKey`, using X25519
   raw base64 and compare-and-set persistence. It validates and preserves existing
   keys rather than rotating them; invalid values require operator investigation.
   It never logs the key or adds peers. After revoking temporary root access it
   waits for the store and refreshes the `wireguard-server-key` ExternalSecret.
   ESO copies only `privateKey` to the one same-named namespace-local Secret.
5. Verify SecretStore/ExternalSecret Ready conditions and target metadata, not
   Secret values. The first secret-sync readiness wait may remain pending until
   the catalog is reconciled; do not make the ceremony depend on that first wait
   succeeding. Before application activation, make the gateway Flux stage depend
   on the now-Ready secret-sync stage, namespace and client values. The setup tool
   does not select or reconcile the gateway HelmRelease.

An absent ConfigMap or disabled selector creates no WireGuard record, role or
refresh; other read failures and malformed selection fail closed. Deselection
preserves any existing key and role, and does not revoke devices. No supported
provider-update command exposes or rotates this key. Recovery restores server
identity separately from the current approved peers; use no peers if uncertain.

### Stopped Alpha Staging Evidence

On 2026-09-15, the operator authorized a client preparation change selecting only
the independent namespace, namespace-local values and optional secret-sync
packages. The gateway HelmRelease stayed unselected, with `replicas: 0` and
`peers: []` in the setup values. Base stayed at
`f3ad4196382da780c1ae073d845b2de221bad4e3`; neither its source selector nor the
client's immutable access-checker pin changed. Full client checks passed with
69 tests and one existing opt-in skip, all seven hooks passed, independent review
found no remaining defects, and hosted CI plus exact-test-merge compatibility
passed before merging without a bypass.

Automatic Flux reconciliation made the namespace and client values Ready. No
gateway Deployment, Pod, Service or HelmRelease existed. Secret-sync remained
NotReady: the SecretStore reported `InvalidProviderConfig` with an invalid role,
and the ExternalSecret reported `SecretSyncedError` because its store was not
ready. This is an expected provisioning block, not successful key delivery; no
credential ceremony or forced reconciliation was performed to clear it.

The existing 51 HelmReleases and 68 active Pods remained Ready, all 19 PVCs were
Bound, and Ceph reported `HEALTH_OK`. Forgejo and operations PostgreSQL retained
their Pod identities and zero restarts; Forgejo had no public Gateway or ingress
allowance. Recent Fluent Bit/OpenSearch logs had no error- or warning-marked
entries; raw application log content and credential values were not disclosed.
This verifies stopped preparation only, not browser login, file transfers,
end-to-end UDP, live CNI/NAT policy, Mac enrollment, DNS or activation acceptance.

### Activation Validation Blocker

On 2026-09-15, after the operator reported completing the approved catalog
ceremony, read-only inspection confirmed the WireGuard SecretStore Ready/Valid,
ExternalSecret Ready/SecretSynced with the current-generation synchronization
prefix, and secret-sync stage Ready. No Secret values or operational private
keys were read. Both Git sources, all 13 existing Flux stages and all 51
HelmReleases were Ready; Forgejo, its certificate and both logging-pipeline
components remained healthy.

The separately authorized one-device activation was prepared but not deployed.
Full client validation rejected the newly selected `charts/wireguard` because
the immutable selected-values checker at
`90d6ce6342375520ee1bd644aa24d8013ee1d96f` has no classification for that chart.
The current Base checker at `f3ad4196382da780c1ae073d845b2de221bad4e3` also lacks
it. Independent review reproduced the failure and confirmed that no supported
client setting can extend the hard-coded chart catalog. A reviewed Base checker
prerequisite and subsequent immutable client checker pin are required; do not
skip the check, conceal the selected HelmRelease or suspend it to bypass validation.
This prerequisite exceeds the requested single client activation PR, so activation
remains stopped pending approval of that additional scope. Runtime Base selection,
keys, public applications and stable clients remain unchanged. The Mac resolver
procedure below is prepared, not a claim of tested Mac resolution or enrollment.

### Mac Enrollment

After the network/activation gates are authorized, create an empty tunnel in the
Mac WireGuard app so the device key is generated locally. Give the operator only
its public key and owner for the static peer entry; never export its private key
to a ticket, repository, server or chat. Configure the reviewed device `/32`, UDP
endpoint, virtual destination `/32` in `AllowedIPs`, MTU and scoped hostname
mapping only after the real values are known. Do not set catch-all routes or DNS.

After an authorized gateway start (an empty peer list is safe), obtain only its
public key with the narrow command below and use it as the Mac's server peer:

```bash
kubectl --context <kube-context> -n wireguard exec deployment/wireguard -- wg show wg0 public-key
```

This command is not permission to contact the cluster now. Do not substitute
`wg showconf`, a Secret dump or a private-key query. Use the stop/update/start
sequence below when adding the approved Mac peer, then verify both positive
Forgejo access and negative unrelated-route/port tests. Remove it the same way;
application credential offboarding remains separate.

### Scoped Mac DNS

The pilot uses a workstation-local `dnsmasq` instance and macOS's per-domain
resolver, not a gateway DNS service, `/etc/hosts`, public DNS changes or a
WireGuard `DNS` field. This needs user-executed Mac setup; Linux-side checks do
not establish macOS application resolution. Use the canonical hostname and
reviewed virtual IPv4 from the private client configuration. Keep the tunnel off
while preparing resolution, and do not replace an existing resolver or listener.

With Homebrew already available, install `dnsmasq` if absent (`brew install
dnsmasq`). Check `scutil --dns`, any existing `/etc/resolver/<canonical-hostname>`
file, and TCP/UDP port 1053 with `lsof -nP -iTCP:1053 -iUDP:1053`; stop on a
conflict rather than overwriting another VPN's setup. In one terminal, set the
two values below from the client and leave this foreground process running for
the pilot:

```bash
export FORGEJO_HOST=forgejo.example.com
export FORGEJO_VIRTUAL_IP='<reviewed-virtual-ip>'
"$(brew --prefix)/sbin/dnsmasq" --no-daemon --conf-file=/dev/null \
  --port=1053 --listen-address=127.0.0.1 --bind-interfaces \
  --no-resolv --no-hosts --local="/$FORGEJO_HOST/" \
  --host-record="$FORGEJO_HOST,$FORGEJO_VIRTUAL_IP"
```

The empty configuration file avoids loading an existing broad dnsmasq setup.
No upstream, DHCP or wildcard address mapping is configured. Only the exact
host has an A record; AAAA and HTTPS/SVCB queries cannot introduce another
destination. The local zone also covers names beneath that host, not siblings
or the parent domain. This process does not need root on port 1053.

In a second terminal set `FORGEJO_HOST` to the same canonical hostname, then
create only its resolver file, refusing to overwrite one that already exists:

```bash
sudo mkdir -p /etc/resolver
printf 'nameserver 127.0.0.1\nport 1053\n' |
  sudo sh -c 'set -C; umask 022; cat > "$1"' sh "/etc/resolver/$FORGEJO_HOST"
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
scutil --dns
dig @127.0.0.1 -p 1053 "$FORGEJO_HOST" A
dig @127.0.0.1 -p 1053 "$FORGEJO_HOST" AAAA
dscacheutil -q host -a name "$FORGEJO_HOST"
```

Verify the system result is only the virtual IPv4 and ordinary public/corporate
names still use their existing resolvers. Plain `dig <hostname>` does not prove
macOS's scoped resolver selection. With WireGuard on, test normal `curl` without
`--resolve`, browser login and Git HTTPS. Browser secure-DNS/proxy settings can
bypass the system resolver: inspect the actual application rather than changing
global DNS. With the tunnel off the hostname may still resolve to the virtual
IP, but Forgejo access must fail. Test resolver failure and any concurrent VPN;
the DNS mapping is not a firewall or a proven fail-closed routing mechanism.

After the pilot, stop only this foreground process and remove only the resolver
file created here, then flush the cache and recheck ordinary resolution. Do not
leave a dead resolver installed. A persistent login service can replace the
foreground invocation after successful Mac testing; it is not installed by this
runbook or required to test the connection. Upstream references:
[dnsmasq options](https://dnsmasq.org/docs/dnsmasq-man.html) and
[macOS resolver selection](https://www.manpagez.com/man/5/resolver/).

### Stop Update Start

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
