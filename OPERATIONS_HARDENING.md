# Operations hardening — server access & firewall

Runbook for locking down the production VM that hosts this app. Nothing in this file executes from the repo — every command runs against the target VM via SSH, with the operator as `sudo`.

The app's own security posture (cookie flags, CSRF, HSTS, ORM hygiene) lives in `backend/testimonies/settings.py` and the deploy hardening in `scripts/deploy.sh`. This file covers the host.

---

## Topology (from `CLAUDE.md`)

- **App VM** — dedicated VM running gunicorn + node + nginx. Hostname and IP live in GitHub Actions secrets (`/testimonies-world/.github/workflows/deploy.yml`); not committed.
- **TLS** — terminates upstream at **Caddy on the Proxmox host** (`/opt/shared/cobox/README.md`). Caddy forwards plain HTTP to this VM's nginx. The VM does **not** bind 443.
- **Database** — PostgreSQL `testimonies_world` at `10.0.0.100:5432` (remote, shared). Not on this VM.
- **Internal ports on this VM** — backend `127.0.0.1:8040`, frontend `127.0.0.1:3000`. Never reachable from outside.

The firewall on this VM should therefore expose **SSH (22)** and **HTTP (80)** only. HTTPS terminates on the hypervisor.

---

## Preflight

Run every step below with `sudo`. If a check fails, fix it before continuing — these layers are designed to fail closed together, not in isolation.

```bash
# Confirm you're on the right VM and you're root-equivalent
hostname
sudo -n true && echo "sudo OK" || echo "sudo NOT passwordless — abort"

# Confirm no operator is currently locked out by SSH changes
who
ss -tlnp | grep ':22\b'   # SSH must be up; we never want to lock ourselves out
```

If SSH is on a non-default port, capture it now and substitute `<SSH_PORT>` everywhere below.

---

## 1. SSH hardening

### 1.1 Audit current state

```bash
sudo sshd -T 2>/dev/null | grep -iE 'permitrootlogin|passwordauthentication|kbdinteractive|pubkey|allowusers|allowgroups' | sort
```

Expected (post-hardening) values:
- `permitrootlogin prohibit-password` or `no`
- `passwordauthentication no`
- `kbdinteractiveauthentication no`
- `pubkeyauthentication yes`

### 1.2 Backup current config

```bash
sudo cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.bak-$(date +%Y%m%d-%H%M%S)
sudo chmod 0600 /etc/ssh/sshd_config.bak-*
```

### 1.3 Enforce the policy

Write the canonical config:

```bash
sudo tee /etc/ssh/sshd_config.d/00-hardening.conf > /dev/null <<'EOF'
# Key-only root + user login. No password, no KbdInteractive.
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes

# Surface reduction
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitUserEnvironment no
PermitTunnel no
GatewayPorts no

# Idle discipline
ClientAliveInterval 300
ClientAliveCountMax 2
LoginGraceTime 30
MaxAuthTries 3
MaxSessions 5

# Logging — verbose enough to investigate break-in attempts.
LogLevel VERBOSE
EOF
```

`PermitRootLogin prohibit-password` (not `no`) keeps deploys and break-glass admin via a root-owned key viable. Operators who don't need root ssh should not put a root key in `~/.ssh/authorized_keys` — that's the policy line, not the sshd line.

If a non-standard SSH port is in use, set `Port <SSH_PORT>` in this file too (or a separate `01-port.conf`) and update UFW accordingly.

### 1.4 Validate + reload — without disconnecting yourself

```bash
# Validate the config — sshd refuses to start on a bad config.
sudo sshd -t && echo "sshd config OK"

# Apply. systemd-managed sshd reloads in-place; existing sessions stay open.
sudo systemctl reload ssh
```

### 1.5 Verify

In a **second** SSH session (do not close the first until you have confirmed you can log in again):

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 deploy@<vm> 'whoami && sudo -n true && echo OK'
```

The `-o BatchMode=yes` forbids the password prompt — if key auth is broken, this command fails fast instead of silently falling through.

Then, from the original session:

```bash
sudo sshd -T 2>/dev/null | grep -iE '^permitrootlogin|^passwordauthentication|^kbdinteractiveauthentication' | sort
sudo tail -n 50 /var/log/auth.log | grep -i 'accepted\|failed' | tail -20
```

---

## 2. Authorized-keys hygiene

```bash
# Every account that can log in should have a non-empty authorized_keys.
for u in root deploy; do
  if [ -f "/$u/.ssh/authorized_keys" ]; then
    echo "$u: $(wc -l <"/$u/.ssh/authorized_keys") keys"
  else
    echo "$u: NO authorized_keys file"
  fi
done

# Each key should be one of: ed25519 (preferred), ecdsa-sha2-nistp256/384/521, ssh-rsa (4096-bit minimum).
# Anything else is suspicious.
sudo awk '/ssh-/ {print "  " $0}' /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null
```

Permissions:

```bash
sudo chmod 0700 /root/.ssh /home/*/.ssh
sudo chmod 0600 /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys
sudo chown -R root:root /root/.ssh
sudo chown -R "$USER":"$(id -gn "$USER")" /home/$USER/.ssh
```

If a stale `authorized_keys` contains a key whose private half is gone or compromised: edit it out. Never delete the file — `chmod 0600` and `> /dev/null` overwrite differently.

---

## 3. UFW firewall

### 3.1 Audit current state

```bash
sudo ufw status verbose
sudo iptables -S | head -40
```

### 3.2 Set defaults

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw default routed deny   # only relevant if the VM routes for other hosts; harmless otherwise
```

### 3.3 Allow the only ports that should be reachable from outside

```bash
sudo ufw allow in <SSH_PORT>/tcp comment 'SSH'
sudo ufw allow in 80/tcp        comment 'nginx (Caddy forwards HTTPS-terminated traffic here)'

# Deliberately NOT opening:
#   443/tcp — TLS terminates on the Caddy hypervisor upstream. nginx on this
#             VM binds only :80 and serves over plain HTTP loopback. Opening
#             443 here would bypass Caddy and break the cert chain.
#   8040/tcp — gunicorn is bound to 127.0.0.1 by the systemd unit. nginx
#              proxies to it on loopback.
#   3000/tcp — node is bound to 127.0.0.1 by the systemd unit.
#   5432/tcp — Postgres lives on 10.0.0.100, not this VM.
```

If you must allow an alternate SSH port, do it explicitly and tag the comment so a future audit can read intent.

### 3.4 Enable + verify

```bash
sudo ufw enable
sudo ufw status verbose numbered
```

`ssh` reload does not interrupt existing sessions, but a brand-new UFW rule applying mid-session can drop packets if you got the SSH rule wrong. Confirm the SSH line in `ufw status verbose` before the `enable` if you have any doubt — UFW's rule numbering makes removal a single `sudo ufw delete <n>`.

### 3.5 Confirmation

```bash
sudo ss -tlnp | grep -E ':(22|80|<SSH_PORT>)\b'    # SSH and HTTP listening
sudo ss -tlnp | grep -E ':(443|3000|5432|6379|8040)\b'  # expect NOTHING bound on public interfaces
```

The second check is the proof: no app or DB port is exposed to the network. Loopback bindings (`127.0.0.1:8040`, `127.0.0.1:3000`) will not show in `ss -tlnp` without the `-l` flag for loopback — that's the point.

---

## 4. PostgreSQL account audit (remote DB at `10.0.0.100`)

The DB is on a different VM. Run these from **that** VM, or from this VM with `PGHOST=10.0.0.100`.

### 4.1 Role inventory

```bash
PGPASSWORD=... psql -h 10.0.0.100 -U postgres -c "\du"     # or the admin role in use
```

Check every role for:
- **No `SUPERUSER` attribute** for application roles. Only the operator role may have it.
- **`LOGIN` only where needed.** Roles that exist for ownership should be `NOLOGIN`.
- **Reasonable password age.** `SELECT rolname, rolvaliduntil FROM pg_authid WHERE rolvaliduntil IS NOT NULL;`

### 4.2 Empty / default-password check

```bash
# Any role with rolpassword NULL has no password — should not exist for LOGIN roles.
sudo -u postgres psql -c "SELECT rolname FROM pg_authid WHERE rolpassword IS NULL AND rolcanlogin;"

# Roles whose password is the empty string are returned by some pg_authid views as NULL;
# the canonical fix is to set a real password and rotate any secrets that depend on it.
```

### 4.3 Weak password policy

PostgreSQL has no built-in password complexity rules. Enforce at the role-creation layer:

```bash
# 1. Generate a strong random password per role.
NEW_PW=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')

# 2. Set it on the role.
sudo -u postgres psql -c "ALTER ROLE testimonies_world_app LOGIN PASSWORD '$NEW_PW';"

# 3. Store the new password in the operator-only secrets store, not in the repo
#    and not in /opt/rtv-cases/backend/.env unless that file is mode 0600 and
#    owned by the deploy user.
sudo install -m 0600 -o deploy -g deploy /dev/null /opt/rtv-cases/backend/.env
```

### 4.4 Confirm pg_hba.conf posture

```bash
sudo grep -E '^(host|local)' /etc/postgresql/*/main/pg_hba.conf
```

Expected:
- Local Unix-socket: `peer` for the `postgres` role (operator sudo), `scram-sha-256` or `md5` for everything else.
- TCP (`host`/`hostssl`): `scram-sha-256` only. **No `trust`, no `password`** lines for any role.
- The application's role (`testimonies_world_app`) connects from the app VM's IP only — not `0.0.0.0/0`.

If `trust` appears anywhere, fix it before continuing. An open trust line is a one-line outage.

### 4.5 Application-role password rotation drill

Run this **once** after deploy to confirm secrets match end-to-end:

```bash
# From the app VM, with the deploy user:
sudo -u deploy psql "postgresql://testimonies_world_app@10.0.0.100:5432/testimonies_world" \
    -c "SELECT 1;"    # should print '1' and exit 0
```

If it fails with `password authentication failed for user "..."`, the `.env` on the app VM is stale against the DB. Rotate the password in the secrets store and update `.env` together.

---

## 5. Service-account review (this VM)

```bash
# Every account that has a password set should be a service that needs one.
# Humans should use SSH keys; service accounts should be NOLOGIN.
awk -F: '$2 !~ /^[*!]/ {print $1}' /etc/shadow | while read u; do
  uid=$(id -u "$u")
  if [ "$uid" -ge 1000 ] && [ -d "/home/$u" ]; then
    echo "user account with password: $u (uid $uid)"
  fi
done

# Lock + expire any account that's unused for > 30 days.
sudo lastlog | awk '$5 == "**Never" {print $1}' | while read u; do
  echo "never logged in: $u"
  sudo passwd -l "$u"
done
```

The systemd app users (`deploy`, `www-data`) are operating-system service accounts — they should be `NOLOGIN` in `/etc/passwd` (shell `/usr/sbin/nologin` or `/bin/false`). The `deploy` user is the exception because `scripts/deploy.sh` runs commands as it; verify it can `sudo -u deploy <command>` from a logged-in operator session.

---

## 6. Verification matrix

After running every step above, confirm:

| Check | Command | Expected |
|---|---|---|
| SSH key-only | `sudo sshd -T \| grep ^passwordauthentication` | `passwordauthentication no` |
| Root key-only | `sudo sshd -T \| grep ^permitrootlogin` | `permitrootlogin prohibit-password` |
| No KbdInteractive | `sudo sshd -T \| grep ^kbdinteractiveauthentication` | `kbdinteractiveauthentication no` |
| UFW active | `sudo ufw status \| head -1` | `Status: active` |
| UFW defaults | `sudo ufw status verbose \| grep 'Default:'` | `deny (incoming)`, `allow (outgoing)` |
| UFW allowlist | `sudo ufw status numbered` | Only SSH and 80/tcp listed |
| No public app ports | `sudo ss -tlnp \| grep -vE '127\.0\.0\.1\|::1' \| grep -E ':(3000\|5432\|6379\|8040)\b'` | empty output |
| No DB `trust` auth | `grep -E '^\s*(host\|local).*trust' /etc/postgresql/*/main/pg_hba.conf` | empty output |
| DB uses SCRAM | `grep -E '^(host\|hostssl)' /etc/postgresql/*/main/pg_hba.conf` | every line ends with `scram-sha-256` |
| App-role can connect | `sudo -u deploy psql "postgresql://testimonies_world_app@10.0.0.100:5432/testimonies_world" -c 'SELECT 1;'` | prints `1` |

If any row fails, fix that row's section above before claiming the VM is hardened.

---

## 7. Rollback

Every change above is reversible from a separate session that retained the pre-change state. Pre-hardening backups:

- `/etc/ssh/sshd_config.bak-<timestamp>` — restore with `sudo cp -a … /etc/ssh/sshd_config && sudo systemctl reload ssh`.
- `ufw` rules — `sudo ufw status numbered` then `sudo ufw delete <n>` for each added rule; `sudo ufw disable` to revert defaults wholesale.

Do not delete the backups for at least one full deploy cycle (~2 weeks). A late-emerging break-glass need usually arrives after the operator who made the change has logged off.