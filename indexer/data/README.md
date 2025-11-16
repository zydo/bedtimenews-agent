# Indexer Data Directory

This directory is mounted as `/data` inside the indexer Docker container.

## Purpose

- Used by the indexer service for file processing and incremental loading
- Contains the [bedtimenews-archive-contents](https://github.com/bedtimenews/bedtimenews-archive-contents) repository cloned from GitHub by indexer service and any other output files that may be created during the indexing process

## Git Ignore Rules

- All contents except this README file are ignored in git

## Note

Do not manually add or modify files to this directory - they will be managed by the indexer service.
