# Deployment Guide: Fly.io

This guide walks you through deploying the Measured API backend to Fly.io.

## Prerequisites

1. **Install Fly.io CLI**
   ```bash
   # macOS
   brew install flyctl
   
   # Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Authenticate with Fly.io**
   ```bash
   fly auth login
   ```

3. **Verify your installation**
   ```bash
   fly version
   ```

## Initial Deployment

### Step 1: Configure Your App

Review and update the `fly.toml` file if needed:
- **app**: Change `"measured-backend"` to your preferred app name (must be unique across Fly.io)
- **primary_region**: Change `"ams"` to your preferred region (run `fly platform regions` to see options)

### Step 2: Create the Fly.io App

From the `backend` directory, run:

```bash
cd backend
fly launch --no-deploy
```

When prompted:
- Choose a unique app name (or use the one in fly.toml)
- Select your preferred region
- Skip deploying immediately

### Step 3: Provision PostgreSQL

Create a Fly Postgres cluster and attach it to your app:

```bash
fly postgres create --name <your-db-name> --region ams
fly postgres attach --app <your-app-name> <your-db-name>
```

This provisions the database/role and writes the resulting connection string to the `DATABASE_URL` secret. `database.py` requires `DATABASE_URL` to be set at startup — there's no fallback default.

### Step 4: Deploy the Application

Deploy your application to Fly.io:

```bash
fly deploy
```

This will:
1. Build the Docker image
2. Push it to Fly.io's registry
3. Create and start your application

### Step 5: Verify Deployment

Check if your app is running:

```bash
fly status
```

Open your app in a browser:

```bash
fly open /api/health
```

You should see: `{"status": "healthy"}`

## Managing Your Deployment

### View Logs

Stream real-time logs:

```bash
fly logs
```

### Access Shell

SSH into your running application:

```bash
fly ssh console
```

### Scale Resources

Change machine resources:

```bash
# Increase memory
fly scale memory 512

# Change VM size
fly scale vm shared-cpu-2x

# Add more machines (requires volume per machine)
fly scale count 2
```

### Update Application

After making code changes:

```bash
fly deploy
```

### Environment Variables

Set environment variables:

```bash
# Set a variable
fly secrets set MY_SECRET=value

# List secrets
fly secrets list

# Unset a secret
fly secrets unset MY_SECRET
```

### Database Management

The production database is PostgreSQL, running as a Fly Postgres cluster (`measured-database`) attached to `measured-backend` via a `DATABASE_URL` secret. See the "PostgreSQL Database" section below for connection details, backups, and restore instructions.

## Monitoring

### Health Checks

The health check endpoint (`/api/health`) is configured in `fly.toml`. Fly.io automatically monitors this endpoint and restarts the application if it fails.

### Metrics Dashboard

View metrics in the Fly.io dashboard:

```bash
fly dashboard
```

### Application Status

Check detailed status:

```bash
fly status --all
```

## Cost Optimization

The configuration includes auto-stop/auto-start features:

- `auto_stop_machines = true`: Stops machines when idle
- `auto_start_machines = true`: Starts machines on incoming requests
- `min_machines_running = 0`: Allows all machines to stop when idle

This helps minimize costs for low-traffic applications.

## Troubleshooting

### Application Won't Start

Check logs:
```bash
fly logs
```

### Database Connection Issues

Verify `DATABASE_URL` is set:
```bash
fly secrets list -a measured-backend
```

Test connectivity to the Postgres cluster directly (see "Connecting from a Local Machine" under PostgreSQL Database below):
```bash
fly proxy 15432:5432 -a measured-database
psql "postgresql://measured_backend:<password>@localhost:15432/measured_backend" -c "SELECT 1;"
```

### Health Check Failing

Test the health endpoint locally first:
```bash
curl https://your-app.fly.dev/api/health
```

### Rebuild from Scratch

If you need to start over:
```bash
fly apps destroy measured-backend
# Then follow deployment steps again
```

## Advanced Configuration

### Custom Domain

Add a custom domain:

```bash
fly certs create yourdomain.com
fly certs show yourdomain.com
```

Follow the instructions to add DNS records.

### Multiple Regions

To deploy the app machine to multiple regions:

```bash
fly machine clone --region lhr
```

For multi-region database access, look at Fly Postgres's own replica support (`fly postgres create` supports adding read replicas in other regions to an existing cluster).

### CORS Configuration

The application allows all origins by default (see `app/main.py`). For production, update the CORS configuration:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## PostgreSQL Database

Production runs on a Fly Postgres cluster, `measured-database`, attached to `measured-backend`. The `DATABASE_URL` secret (never committed, holding embedded credentials) points at it; the app fails fast at startup if it's unset.

### Connecting from a Local Machine

`measured-database.flycast` (the cluster's internal hostname) is only resolvable from inside Fly's private network. To reach it from your own machine, open a tunnel first:

```bash
fly proxy 15432:5432 -a measured-database
```

Then connect to `localhost:15432` with the app's DB credentials, e.g.:

```bash
psql "postgresql://measured_backend:<password>@localhost:15432/measured_backend"
```

### Automated Backups

The production database is automatically backed up **daily at 2 AM UTC** using GitHub Actions (`.github/workflows/backup-postgres-database.yml`). It tunnels into `measured-database` the same way, runs `pg_dump` (via a `postgres:18` container, matching the cluster's server version — a mismatched client version makes `pg_dump` refuse to run), and uploads the gzipped result. Backups are:
- Stored as GitHub Artifacts with **30-day retention**
- Compressed with gzip
- Named with timestamps (e.g., `pg-backup-2026-09-28.sql.gz`)

**Setup Requirements:** the workflow needs two GitHub repository secrets (Settings → Secrets and variables → Actions):
- `FLY_API_TOKEN` — generate via `fly auth token`
- `POSTGRES_BACKUP_PASSWORD` — the `measured_backend` role's password

**Manual Backup Trigger:** Actions tab → "Backup Postgres Database" workflow → "Run workflow".

### Restore Database from Backup

1. **Download the backup:**
   - Go to GitHub repository → Actions → "Backup Postgres Database"
   - Select a successful workflow run
   - Download the backup artifact (e.g., `pg-backup-2026-09-28.sql.gz`)
   - Extract it: `gunzip pg-backup-2026-09-28.sql.gz`

2. **Restore locally (for testing), against the Docker Compose Postgres:**
   ```bash
   docker compose up -d
   psql "postgresql://measured:measured@localhost:5432/measured" < pg-backup-2026-09-28.sql
   ```

3. **Restore to production**, via the same tunnel used to connect:
   ```bash
   fly proxy 15432:5432 -a measured-database

   # IMPORTANT: back up the current state first (see Manual Backup Trigger above,
   # or run pg_dump directly against localhost:15432 as in "Connecting from a Local
   # Machine" above) before restoring over it.

   psql "postgresql://measured_backend:<password>@localhost:15432/measured_backend" \
       < pg-backup-2026-09-28.sql

   # Verify the restore was successful
   psql "postgresql://measured_backend:<password>@localhost:15432/measured_backend" \
       -c "SELECT COUNT(*) FROM projects; SELECT COUNT(*) FROM sessions;"
   ```

   **⚠️ Important Notes:**
   - The dump contains `CREATE TABLE` statements, so restoring into a database that already has these tables will error — drop them first if you're restoring over existing data
   - Always back up the current state before restoring
   - `pg_dump`/`psql` version must be able to talk to the cluster's Postgres 18 server — use a matching client (e.g. `docker run --rm --network host -e PGPASSWORD=... postgres:18 psql ...`) if your local `psql` is older

## Support

- [Fly.io Documentation](https://fly.io/docs/)
- [Fly.io Community Forum](https://community.fly.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Security Best Practices

1. **Never commit secrets** to version control
2. **Use fly secrets** for sensitive configuration
3. **Enable HTTPS** (enabled by default in fly.toml)
4. **Restrict CORS** origins in production
5. **Regular backups** of your database
6. **Monitor logs** for suspicious activity
7. **Keep dependencies updated** (run `pip list --outdated` regularly)

## Quick Reference

```bash
# Deploy
fly deploy

# View logs
fly logs

# Check status
fly status

# SSH into machine
fly ssh console

# Open app
fly open

# View dashboard
fly dashboard

# Restart application
fly apps restart measured-backend
```

