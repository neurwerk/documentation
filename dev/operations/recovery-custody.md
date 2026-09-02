# OpenBao Recovery Custody

Prepare offline custody before the first OpenBao bootstrap. This procedure
covers the static-seal kit and recovery-share packages.

## Custody Material

### Static-Seal Kit

`stack-setup` stores the static-seal kit at
`operator-custody/openbao-seal.json` under the custody root. The file contains
the static seal key, cluster binding, and bootstrap checkpoint.

During bootstrap, it may temporarily contain custodian keys, the initial root
token, encrypted shares, or administrator passwords. `stack-setup` removes this
material after the relevant checkpoints complete.

Store the kit on encrypted offline media, separate from the custodian packages.
The static seal allows automatic restarts but cannot authorize recovery-root
operations. `stack-setup` does not support replacing the immutable Kubernetes
static-seal Secret.

### Custodian Packages

Bootstrap creates three `0600` ZIP packages. Each contains a passwordless
RSA-4096 OpenPGP key pair, one encrypted share, binding metadata, and recovery
instructions.

The ZIP is not encrypted, and the private key has no passphrase. Possession of a
package gives control of one recovery share. Store each package on separate,
encrypted offline media.

Any two distinct packages can authorize a recovery-root operation.

### Custody Root

The default custody root is
`~/.local/share/neurwerk/openbao/<client-name>/`. Use `--custody-root` only when
this location is unsuitable.

The root and its subdirectories must be outside Git repositories and workspace
roots, owned by the current user, mode `0700`, and not symbolic links.

## Roles And Records

Assign each package to a named custodian. Require two custodians to approve and
attend every recovery-root operation. The CLI enforces two distinct shares, but
it cannot verify that two different people supplied them.

If one operator temporarily controls all three packages, recovery still has
single-operator custody. Record this status and complete the handover before
treating recovery as operational.

Maintain an access record outside Git. Record the client, cluster, share number,
custodian, physical storage location, transfers, verifications, participants,
purpose, time, and result. Never record shares, private keys, secret values,
tokens, local package paths, or recovery command output.

## Bootstrap And Handover

1. Run `stack-setup bootstrap` from a trusted, encrypted workstation.
2. Enter three distinct custodian names when prompted.
3. Keep `custodian-packages/custodian-1.zip` and `custodian-2.zip` in place until
   bootstrap is complete. An interrupted bootstrap uses these paths to resume.
4. Copy each package to separate encrypted removable media. Deliver it to the
   custodian named in its metadata and README.
5. Do not decrypt a share during ordinary handover.
6. Store the static-seal kit separately. Never store it with two custodian
   packages.
7. Verify two packages in a controlled live ceremony before deleting the
   bootstrap operator's copies.

Avoid SSD, backup, and synchronized-storage copies: deleting a file does not
prove its removal. Prefer encrypted removable storage or hardware tokens.

> **Warning:** OpenBao can complete initialization before the workstation saves
> its one-time response. If `stack-setup` reports this state, stop and escalate.
> Do not delete storage, the namespace, or the static-seal Secret. Rebuilding an
> empty cluster requires explicit authorization and is not custody recovery.

## Verification And Reconciliation

Use exactly two packages with `stack-setup recovery verify` or
`stack-setup reconcile`. Both custodians must approve the action and attend the
local ceremony. A distributed ceremony is not supported.

The CLI validates the kit and package bindings, decrypts each share in a separate
temporary GnuPG home, and submits the shares over a TLS-verified connection.
Plaintext shares remain in process memory. The CLI creates a temporary root
token and attempts to revoke it before returning.

If the command crashes or reports a revocation failure, stop and escalate. The
temporary root token may still be active.

`recovery verify` performs a privileged live check. It verifies custody and
cluster binding; it does not back up or restore OpenBao data.

`reconcile` requires a completed bootstrap and applies only the versioned catalog
compiled into the installed `stack-setup` release. It accepts no arbitrary
secret paths, policies, or applications. It revokes other root-policy tokens and
its temporary root before Kubernetes convergence.

Record the participants, purpose, share numbers, time, client, cluster, and
result. Do not log secret input, GnuPG output, or token values.

## Loss Or Compromise

If one package is lost, keep the remaining packages. Verify the two remaining
shares under dual control and record the loss. `stack-setup` does not support
recovery-share replacement or rotation.

If the static-seal kit is lost or compromised, stop and escalate. Replacing the
Kubernetes static-seal Secret is not a supported operator operation.

Review custody after every handover, staff change, suspected compromise, lost
share, or emergency use. Repeat controlled verification after a handover.
