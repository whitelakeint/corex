# Deployment Steps to Remote Server

Server: `jnpwladmin@208.109.191.251`
Password: `e45#8deR5RZ5`
Remote Path: `/home/jnpwladmin/tavus`

## Quick Deployment Commands

Run these commands in your terminal (you'll be prompted for password for each):

```bash
# 1. Copy modified backend files
scp backend/app.py jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/backend/
scp backend/config.py jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/backend/
scp backend/tool_stubs.py jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/backend/
scp backend/tavus_client.py jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/backend/

# 2. Copy frontend
scp frontend/index.html jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/frontend/

# 3. Copy scripts and config
scp scripts/setup_persona.py jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/scripts/
scp .env jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/
scp CLAUDE.md jnpwladmin@208.109.191.251:/home/jnpwladmin/tavus/

# 4. SSH into server and restart
ssh jnpwladmin@208.109.191.251
```

## On the Remote Server

Once connected via SSH, run:

```bash
cd /home/jnpwladmin/tavus

# Remove deleted Daily.co integration files
rm -f backend/daily_client.py backend/escalation.py

# Restart the server
./stop.sh
./start.sh

# Verify it's running
tail -f server.log
```

## Or Use Single Tarball Method

```bash
# Create tarball (already done)
tar -czf tavus-deployment.tar.gz \
  backend/app.py backend/config.py backend/tool_stubs.py backend/tavus_client.py \
  frontend/index.html scripts/setup_persona.py CLAUDE.md .env

# Copy tarball
scp tavus-deployment.tar.gz jnpwladmin@208.109.191.251:/tmp/

# SSH and deploy
ssh jnpwladmin@208.109.191.251

# On remote server:
cd /home/jnpwladmin/tavus
./stop.sh
tar -xzf /tmp/tavus-deployment.tar.gz
rm -f backend/daily_client.py backend/escalation.py
./start.sh
rm /tmp/tavus-deployment.tar.gz
tail -f server.log
```

## What Was Changed

- **Removed**: Daily.co video escalation integration (daily_client.py, escalation.py)
- **Modified**: app.py (removed SSE endpoints and escalation logic)
- **Modified**: config.py (removed DAILY_API_KEY, DAILY_DOMAIN)
- **Modified**: frontend/index.html (removed escalation UI handlers)
- **Modified**: scripts/setup_persona.py (updated escalation prompt)
- **Updated**: .env (removed Daily.co credentials, updated persona ID to pd2c01750caf)

The avatar will now say the escalation phrase but won't attempt to create video calls.
