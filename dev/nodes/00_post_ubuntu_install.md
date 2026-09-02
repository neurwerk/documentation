# Ubuntu K3s Node Setup

Use this guide after installing Ubuntu on a K3s server VM. Replace all example
addresses, interface names, hostnames, key paths, VM IDs, and PCI IDs.

## Prerequisites

- Set the Proxmox VM CPU type to `x86-64-v3` or `host`.
- Create the `neurwerk-admin` Ubuntu account with sudo access.
- Keep console access available while changing the network configuration.

Verify that the VM exposes the required CPU features:

```bash
grep -m1 '^flags' /proc/cpuinfo
```

The output must include `avx`, `avx2`, `bmi1`, `bmi2`, `f16c`, `fma`, `abm`,
`movbe`, and `xsave`.

## 1. Configure a Stable Node Address

Use a static Ubuntu address or a DHCP reservation for the VM's persistent MAC
address. Unreserved DHCP is not supported.

For a static address, identify the interface and edit the Netplan file:

```bash
ip link
sudoedit /etc/netplan/00-installer-config.yaml
```

Example:

```yaml
network:
  version: 2
  ethernets:
    ens18:
      dhcp4: false
      addresses:
        - 172.20.1.92/22
      routes:
        - to: default
          via: 172.20.1.254
      nameservers:
        addresses:
          - 9.9.9.9
```

Apply the configuration:

```bash
sudo chmod 600 /etc/netplan/00-installer-config.yaml
sudo netplan try
sudo netplan apply
```

## 2. Configure SSH Access

### Create the Tunnel Account

On the Ubuntu VM:

```bash
sudo adduser --gecos "" k8s-tunnel
sudo visudo -f /etc/sudoers.d/k3sup-neurwerk-admin
```

Add this temporary sudoers rule for K3sup:

```text
neurwerk-admin ALL=(ALL) NOPASSWD: ALL
```

### Configure the Workstation

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh

ssh-keygen -t rsa -b 4096 -m PEM \
  -f ~/.ssh/example_com_kubernetes_admin.pem
ssh-keygen -t rsa -b 4096 -m PEM \
  -f ~/.ssh/example_com_kubernetes_tunnel.pem

chmod 600 ~/.ssh/example_com_kubernetes_admin.pem
chmod 600 ~/.ssh/example_com_kubernetes_tunnel.pem

ssh-copy-id \
  -i ~/.ssh/example_com_kubernetes_admin.pem.pub \
  neurwerk-admin@172.20.1.92
ssh-copy-id \
  -i ~/.ssh/example_com_kubernetes_tunnel.pem.pub \
  k8s-tunnel@172.20.1.92
```

Add these aliases to `~/.ssh/config`:

```sshconfig
Host kubernetes-admin.example.com
    HostName 172.20.1.92
    User neurwerk-admin
    IdentityFile ~/.ssh/example_com_kubernetes_admin.pem
    IdentitiesOnly yes

Host k8s-tunnel.example.com
    HostName 172.20.1.92
    User k8s-tunnel
    IdentityFile ~/.ssh/example_com_kubernetes_tunnel.pem
    IdentitiesOnly yes
```

Test both keys before locking the tunnel account password:

```bash
chmod 600 ~/.ssh/config
ssh kubernetes-admin.example.com
ssh k8s-tunnel.example.com
ssh -t kubernetes-admin.example.com 'sudo passwd --lock k8s-tunnel'
```

## 3. Install K3s

Run these commands on the workstation. `NODE_IP` must match the stable address
configured above.

```bash
curl -sLS https://get.k3sup.dev | sh
sudo install k3sup /usr/local/bin/

NODE_IP=172.20.1.92
KUBE_CONTEXT=example-context

k3sup install \
  --host "$NODE_IP" \
  --sudo true \
  --user neurwerk-admin \
  --ssh-key ~/.ssh/example_com_kubernetes_admin.pem \
  --context "$KUBE_CONTEXT" \
  --local-path ~/.kube/config \
  --merge \
  --k3s-extra-args "--node-ip $NODE_IP --advertise-address $NODE_IP --secrets-encryption"

ssh kubernetes-admin.example.com \
  'sudo rm /etc/sudoers.d/k3sup-neurwerk-admin'
```

### Connect Through the SSH Tunnel

Keep the tunnel running in one terminal:

```bash
ssh -L 6443:localhost:6443 k8s-tunnel.example.com -N
```

In another terminal, configure and verify the context:

```bash
KUBE_CONTEXT=example-context

kubectl config use-context "$KUBE_CONTEXT"
cluster="$(kubectl config view --minify -o jsonpath='{.contexts[0].context.cluster}')"
kubectl config set-cluster "$cluster" --server=https://127.0.0.1:6443

kubectl --context "$KUBE_CONTEXT" get nodes -o wide
ssh -t kubernetes-admin.example.com 'sudo k3s secrets-encrypt status'
```

Continue only when Secret encryption reports `Enabled` and the node's
`InternalIP` matches `NODE_IP`.

## 4. Configure NVIDIA GPU Support

Skip this section for CPU-only nodes.

### Configure PCI Passthrough

Enable VT-d on Intel systems or IOMMU/AMD-Vi on AMD systems in the server
firmware. Also enable IOMMU in the Proxmox boot configuration.

Run these commands as `root` on Proxmox. The example passes the GPU at `65:00`
to VM `100`.

```bash
lspci -nn | grep -Ei 'VGA|3D|Audio'
find /sys/kernel/iommu_groups/ -type l | grep '65:00'

printf 'vfio\nvfio_iommu_type1\nvfio_pci\n' \
  > /etc/modules-load.d/vfio.conf
printf 'options vfio-pci ids=10de:1eb0,10de:10f8\n' \
  > /etc/modprobe.d/vfio.conf
printf 'blacklist nouveau\noptions nouveau modeset=0\n' \
  > /etc/modprobe.d/blacklist-nouveau.conf

update-initramfs -u -k all
reboot
```

After Proxmox restarts, verify VFIO ownership and attach the GPU:

```bash
lspci -nnk -s 65:00.0
lspci -nnk -s 65:00.1

qm set 100 --hostpci0 0000:65:00,pcie=1
qm start 100
```

Both functions must report `Kernel driver in use: vfio-pci`.

### Install the Ubuntu GPU Runtime

On the Ubuntu VM, install the recommended server driver:

```bash
lspci -nn | grep -i nvidia
sudo apt-get update
sudo ubuntu-drivers list --gpgpu
sudo ubuntu-drivers install --gpgpu
sudo reboot
```

After the VM restarts, verify the driver and install the container toolkit:

```bash
nvidia-smi

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg2

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor \
      -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -sL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart k3s
sudo grep nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml
```

The current PII Engine GPU workload requests `nvidia.com/gpu` without setting a
`RuntimeClass`. Add the default runtime to `/etc/rancher/k3s/config.yaml`
without removing existing keys:

```yaml
default-runtime: nvidia
```

Restart K3s:

```bash
sudo systemctl restart k3s
```

### Install the NVIDIA Device Plugin

Run these commands on the workstation while the SSH tunnel is active:

```bash
KUBE_CONTEXT=example-context

helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
helm upgrade --install nvdp nvdp/nvidia-device-plugin \
  --kube-context "$KUBE_CONTEXT" \
  --namespace nvidia-device-plugin \
  --create-namespace

kubectl --context "$KUBE_CONTEXT" get nodes \
  -o custom-columns=NAME:.metadata.name,GPU:.status.capacity.nvidia\.com/gpu
```

The GPU column must show the number of GPUs available on the node.
