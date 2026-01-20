# SlateDB Quick Start

## 🚀 Get Running in 3 Steps

### Step 1: Set Up Credentials

```bash
# Copy example
cp .env.example .env

# Edit .env and set these variables:
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_ENDPOINT_URL=https://your-s3-endpoint (optional)
# SLATE_RUNNER_BUCKET=nuon-dev
# BUCKET_PREFIX=demo-1  (optional, for namespacing)
```

### Step 2: Test Connection

```bash
source venv/bin/activate
python test_slatedb_minimal.py
```

**Should complete in ~10-30 seconds** with "SUCCESS" message.

### Step 3: Run Runner

```bash
source venv/bin/activate
python runner/main.py
```

## 📁 S3 Bucket Structure

### Without BUCKET_PREFIX
```
s3://nuon-dev/
  └── slatedb/
      ├── clever-falcon/         ← Runner 1 (friendly name)
      │   ├── manifest-00001.json
      │   ├── wal-00001.log
      │   └── compacted-00001.sst
      └── quick-wolf/            ← Runner 2 (friendly name)
          ├── manifest-00001.json
          └── ...
```

### With BUCKET_PREFIX="demo-1"
```
s3://nuon-dev/
  └── demo-1/                    ← Your prefix
      └── slatedb/
          ├── clever-falcon/     ← Runner 1
          │   ├── manifest-00001.json
          │   └── ...
          └── quick-wolf/        ← Runner 2
              └── ...
```

## 🔍 What Gets Stored Where

### SlateDB Internal Files
Location: `s3://bucket/[prefix/]slatedb/{runner_name}/`
- `manifest-*.json` - Database metadata
- `wal-*.log` - Write-ahead logs
- `compacted-*.sst` - Sorted string tables (your data lives here)

### Your Application Data (Inside SlateDB)
When you call `slate_storage.put("runner-state/...", data)`:
- Data is written to WAL
- Eventually compacted into `.sst` files
- Retrieved via `slate_storage.get("runner-state/...")`

Example keys stored:
- `runner-state/runner-abc123/state.json`
- `states/job-123/terraform.tfstate`
- `outputs/job-123.txt`

## ⚡ Performance

### First-Time Initialization
- **Time:** 10-30 seconds
- **Why:** Creating manifest in S3, setting up database structure
- **Network:** 2-3 S3 API calls

### Subsequent Starts
- **Time:** 1-5 seconds
- **Why:** Reading existing manifest from S3
- **Network:** 1 S3 API call

### During Operation
- `put()`: ~1ms (local WAL)
- `get()`: ~1-10ms (cached) or ~50-100ms (S3 read)
- `flush_wal()`: ~50-200ms (S3 write)
- `create_checkpoint()`: ~100-500ms (manifest update)

## 🐛 Troubleshooting

### Hangs at "Creating SlateDB instance..."

**Cause:** Missing credentials or S3 connectivity issue

**Fix:**
1. Check `.env` file has credentials
2. Run `./check_env.sh` to verify
3. Test with `python test_slatedb_minimal.py` (has 30s timeout)

### "Credentials provided: False"

**Fix:** Set these in `.env`:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Can't Connect to S3

**Fix:**
```bash
# Test endpoint directly
curl -I $AWS_ENDPOINT_URL

# Verify bucket exists and you have access
aws s3 ls s3://nuon-dev/
```

## ✅ Success Indicators

You should see:
```
[SlateDB] Credentials provided: True  ← MUST be True
[SlateDB] ✓ SlateDB instance created
[SlateDB] ✓ Connection test successful
[SlateDB] ✓ Initialized successfully
```

## 📊 Monitoring

### Check SlateDB Files in S3
```bash
# Without prefix
aws s3 ls s3://nuon-dev/slatedb/

# With prefix
aws s3 ls s3://nuon-dev/demo-1/slatedb/
```

### View Runner Logs
```
[Jobs] ✓ Uploaded output to SlateDB
[Jobs] ✓ Flushed WAL to S3          ← Confirms WAL persistence
[Jobs] ✓ Created checkpoint: abc123  ← Confirms checkpoint created
```

## 🔐 Security Notes

- Credentials stored in `.env` (gitignored)
- Each runner has isolated S3 prefix
- WAL and checkpoints provide durability
- No data loss even if process crashes

## 📚 Next Steps

1. ✅ Complete steps above
2. Run a test job
3. Verify checkpoint created in logs
4. Check S3 bucket for SlateDB files
5. Test state sync task

For detailed information, see [SLATEDB_SETUP.md](./SLATEDB_SETUP.md)
