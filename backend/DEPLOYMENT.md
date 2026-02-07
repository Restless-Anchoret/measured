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
- Skip setting up PostgreSQL (we're using SQLite)
- Skip deploying immediately

### Step 3: Create Persistent Volume

Create a persistent volume for the SQLite database:

```bash
fly volumes create measured_data --size 1 --region ams
```

Replace `ams` with your chosen region. The volume name `measured_data` matches the mount source in `fly.toml`.

**Important**: Volumes are region-specific and tied to a single machine. For production at scale, consider PostgreSQL instead.

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

#### Automated Backups

The production database is automatically backed up **daily at 2 AM UTC** using GitHub Actions. Backups are:
- Stored as GitHub Artifacts with **30-day retention**
- Compressed with gzip (~90% size reduction)
- Named with timestamps (e.g., `backup-2026-02-07.sql.gz`)

**Setup Requirements:**

Before automated backups will work, you must configure the Fly.io API token:

1. Generate a Fly.io API token:
   ```bash
   fly auth token
   ```

2. Add it as a GitHub repository secret:
   - Go to your GitHub repository → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `FLY_API_TOKEN`
   - Value: Paste the token from step 1
   - Click "Add secret"

**Manual Backup Trigger:**

You can trigger a backup manually at any time:
1. Go to your GitHub repository → Actions tab
2. Select "Backup Database" workflow
3. Click "Run workflow" → "Run workflow"

#### Restore Database from Backup

To restore a database from a backup:

1. **Download the backup:**
   - Go to GitHub repository → Actions → "Backup Database"
   - Select a successful workflow run
   - Download the backup artifact (e.g., `backup-2026-02-07.sql.gz`)
   - Extract it: `gunzip backup-2026-02-07.sql.gz`

2. **Restore locally (for testing):**
   ```bash
   # Delete the old database and create fresh one from backup
   rm -f measured.db
   sqlite3 measured.db < backup-2026-02-07.sql
   ```

3. **Restore to production:**
   ```bash
   # Upload the backup to Fly.io
   fly ssh sftp shell
   put backup-2026-02-07.sql /data/backup.sql
   exit
   
   # Restore the database (replaces existing database)
   fly ssh console
   cd /data
   
   # IMPORTANT: Backup current database first!
   cp measured.db measured.db.before-restore-$(date +%Y%m%d-%H%M%S)
   
   # Delete old database and restore from backup
   rm -f measured.db
   sqlite3 measured.db < backup.sql
   
   # Verify the restore was successful
   sqlite3 measured.db "SELECT COUNT(*) FROM projects; SELECT COUNT(*) FROM sessions;"
   
   exit
   ```
   
   **⚠️ Important Notes:**
   - The SQL dump contains `CREATE TABLE` statements, so it must be applied to a **fresh/empty database**
   - Always backup the current database before restoring (as shown above)
   - If something goes wrong, you can restore from `measured.db.before-restore-*` files

#### Manual Backup (Alternative)

If you need to create a backup outside of the automated schedule:

```bash
# Create and download a compressed backup
fly ssh console --app measured-backend --command "sh -c 'sqlite3 /data/measured.db .dump > /data/backup.sql && gzip -f /data/backup.sql'"
fly ssh sftp get --app measured-backend /data/backup.sql.gz ./backup.sql.gz

# Or for an uncompressed backup:
fly ssh console --app measured-backend --command "sqlite3 /data/measured.db .dump > /data/backup.sql"
fly ssh sftp get --app measured-backend /data/backup.sql ./backup.sql
```

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

Verify volume is mounted:
```bash
fly ssh console
ls -la /data
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

To deploy to multiple regions, you'll need:
1. A volume in each region
2. A machine in each region
3. Consider PostgreSQL for multi-region databases

```bash
# Add a volume in another region
fly volumes create measured_data --size 1 --region lhr

# Add a machine in that region
fly machine clone --region lhr
```

**Note**: SQLite doesn't support multi-region replication. For multi-region deployments, migrate to PostgreSQL.

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

## Migration to PostgreSQL (Optional)

If you need better scalability or multi-region support:

1. Create a PostgreSQL database:
   ```bash
   fly postgres create
   ```

2. Attach it to your app:
   ```bash
   fly postgres attach <postgres-app-name>
   ```

3. Update `requirements.txt`:
   ```
   databases[asyncpg]==0.9.0  # Instead of aiosqlite
   ```

4. The DATABASE_URL will be automatically set by Fly.io

5. Redeploy:
   ```bash
   fly deploy
   ```

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

