# Indexer Service

Automated document embedding pipeline for the BedtimeNews archive. Clones the repository, processes markdown files, generates embeddings, and stores them in PostgreSQL + pgvector.

See [main README](../README.md) for setup instructions.

## Features

- **Auto-sync**: Clones/updates from [bedtimenews-archive-contents](https://github.com/bedtimenews/bedtimenews-archive-contents)
- **Incremental processing**: Content-based change detection (SHA256)
- **Scheduled execution**: Configurable cron schedule (default: hourly)
- **Smart chunking**: Markdown-aware semantic chunking
- **Batch embedding**: Efficient OpenAI API usage
- **Monitoring**: Built-in debugger and statistics

## Pipeline Phases

```plaintext
1. Repository Sync    → Clone/pull latest from GitHub
2. Change Detection   → Compare file hashes (ADD/MODIFY/DELETE)
3. Document Loading   → Parse markdown structure
4. Chunking           → Create semantic chunks with metadata
5. Embedding          → Generate vectors via OpenAI API
6. Database Update    → Store chunks + update history
```

## Configuration

### Cron Schedule

Set in `.env`:

```bash
# Every hour (default)
INDEXER_CRON_SCHEDULE="0 * * * *"

# Every 30 minutes
INDEXER_CRON_SCHEDULE="*/30 * * * *"

# Daily at 2 AM
INDEXER_CRON_SCHEDULE="0 2 * * *"
```

### Document Filters

Edit `index_config.yml`:

```yaml
# Include patterns (processed first)
include:
  # 睡前消息
  - "main/*/*.md" 

  # 参考信息
  - "reference/*/[0-9]*.md"

  # 高见
  - "opinion/[0-9]*.md"

  # 每日新闻 (YYYY/MM/DD.md)
  - "daily/*/*/[0-9]*.md"

  # 讲点黑话
  - "commercial/[0-9]*.md"

  # 产经破壁机
  - "business/[0-9]*.md"
  - "business/-[0-9]*.md" # -1.md and -2.md

  # 直播问答记录
  - "livestream/*/*/[0-9]*.md"

# Exclude patterns (processed after include)
exclude:
  # Directory index files
  - "main/[0-9]*-[0-9]*.md"
  - "reference/[0-9]*-[0-9]*.md"
  - "livestream/[0-9]*.md"
  - "daily/[0-9]*.md"


# File validation rules
validation:
  # Minimum file size in bytes (skip empty or tiny files)
  min_file_size: 100

  # Maximum file size in bytes (skip extremely large files)
  max_file_size: 10485760 # 10 MB
```

## Debugging Utilities

### Test Connection

```bash
docker compose exec indexer python -m src.debugger test
```

### View Statistics

```bash
# Database stats
docker compose exec indexer python -m src.debugger stats

# Recent file actions
docker compose exec indexer python -m src.debugger recent --limit 20

# Indexing history for all files
docker compose exec indexer python -m src.debugger history

# History for specific file
docker compose exec indexer python -m src.debugger history main/901-1000/960.md
```

### Inspect Documents

```bash
# View chunks for a document
docker compose exec indexer python -m src.debugger inspect main/901-1000/960.md
```

### View Logs

```bash
# Recent cron logs
docker compose exec indexer python -m src.debugger logs

# Last 100 lines
docker compose exec indexer python -m src.debugger logs --lines 100

# All logs
docker compose exec indexer python -m src.debugger logs --all
```

### Manual Execution

```bash
# Run pipeline manually (one-time)
docker compose exec indexer python -m src.pipeline
```

### Clear Data

```bash
# DANGER: Clear all indexed data
docker compose exec indexer python -m src.debugger clear
```

## Database Schema

The indexer manages three tables in the `rag` schema:

**`rag.document_chunks`**: Stores chunks with embeddings

- `chunk_id`: Unique identifier (`{doc_id}:{chunk_index}`)
- `doc_id`: Document path without extension
- `chunk_index`: 0-based index within document
- `heading`: Section heading (if any)
- `text`: Chunk content
- `word_count`: Number of words
- `embedding`: 1536-dim vector
- `created_at`: Timestamp

**`rag.indexing_history`**: Tracks file status

- `file_path`: Relative path in repository
- `content_hash`: SHA256 hash for change detection
- `indexed_at`: When file was processed
- `last_modified`: File modification time

**`rag.file_actions`**: Audit log

- `file_path`: Relative path
- `action_type`: ADD, MODIFY, or DELETE
- `content_hash`: SHA256 hash (NULL for DELETE)
- `run_timestamp`: When action was recorded
- `processed_at`: When action was processed

## Data Backup and Restore

The PostgreSQL data volume is stored in a gitignored directory in the codebase. You can back up and restore the entire database using standard tar archives.

### Backup PostgreSQL Data

**Prerequisites**: Stop all services to ensure data consistency:

```bash
docker compose down
```

**(Optional) Check volume size (uncompressed)**:

```bash
du -h -d 0 storage/postgres/volume
```

**Create backup**:

```bash
# Create timestamped backup archive
tar czf /path/to/backup/postgres-volume-$(date +%F).tar.gz storage/postgres/volume/

# Example output: /path/to/backup/postgres-volume-2025-11-27.tar.gz
```

The backup includes:

- All indexed document chunks and embeddings
- Indexing history and file actions
- Database configuration and metadata

### Restore PostgreSQL Data

**Prerequisites**: Stop all services:

```bash
docker compose down
```

**Restore from backup**:

```bash
# Remove existing data (if any)
rm -rf storage/postgres/volume

# Extract backup to the postgres data directory (run in project root directory)
tar xzf /path/to/backup/postgres-volume-2025-11-27.tar.gz -C .
# Verify files extracted as ./storage/postgres/volume/18/docker/...

# Start services
docker compose up -d
```

**Verify restoration**:

```bash
# Check database statistics
docker compose exec indexer python -m src.debugger stats

# View recent file actions
docker compose exec indexer python -m src.debugger recent --limit 10
```

### Notes

- **Local only**: The postgres data directory is in `.gitignore` and not tracked by version control
- **Migration**: Backups are portable and can be restored on different machines
- **Disk space**: Each backup typically ranges from 100MB to several GB depending on indexed content

## Project Structure

```plaintext
indexer/src/
├── entrypoint.py        # Main entry point
├── pipeline.py          # Indexing pipeline
├── scheduler.py         # Cron scheduler
├── git_sync.py          # Repository sync
├── document_loader.py   # Markdown processing
├── embeddings.py        # OpenAI embedding generation
├── vector_db.py         # Database operations
├── debugger.py          # Debug utilities
├── models.py            # Data models
└── settings.py          # Configuration
```

## Monitoring

### Check Service Status

```bash
# View logs
docker compose logs -f indexer

# Check if cron is running
docker compose exec indexer ps aux | grep cron

# Verify database has documents
docker compose exec indexer python -m src.debugger stats
```

### Expected Output

After first run, you should see:

- Repository cloned to `indexer/data/bedtimenews-archive-contents/`
- Chunks in `rag.document_chunks`
- File actions logged in `rag.file_actions`

### Performance Metrics

Pipeline outputs after each run:

- Total documents processed
- Total chunks created
- Total tokens processed
- Average tokens per chunk
- Estimated API costs

## Troubleshooting

**No documents indexed:**

```bash
# Check logs for errors
docker compose logs indexer | grep -i error

# Manually run pipeline
docker compose exec indexer python -m src.pipeline

# Verify git clone succeeded
docker compose exec indexer ls -la data/bedtimenews-archive-contents/
```

**OpenAI API errors:**

- Check API key in `.env`
- Verify rate limits not exceeded
- Check API usage in OpenAI dashboard

**Database connection failed:**

- Ensure postgres is running: `docker compose ps postgres`
- Check credentials in `.env`
- Test connection: `docker compose exec indexer python -m src.debugger test`

**Cron not running:**

```bash
# Check cron process
docker compose exec indexer ps aux | grep cron

# View cron logs
docker compose exec indexer python -m src.debugger logs

# Restart service
docker compose restart indexer
```
