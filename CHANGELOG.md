# Changelog

## 0.2.16 — 2026-10-25

This release repairs recording consistency, screen-time accounting, data removal, shutdown, and portable packaging.

- Native input callbacks enqueue events without waiting for SQLite, process metadata or recorder locks. Queue overflow and hook errors are visible in the status footer.
- Persist each batch in one transaction; failed writes retain the full batch for retry. Export readers use separate SQLite snapshots.
- Count active and idle intervals once, preserve fractional seconds, and split events at their captured local date/hour. Reset time around clock changes and suspend gaps; pause on Windows lock, disconnect and suspend notifications.
- Clear all recorded tables, executable metadata, caches and queued/buffered activity. Apply retention immediately and daily, including orphan metadata cleanup.
- Validate configuration values, save settings/exports atomically, quote autostart paths, and escape spreadsheet formula-like CSV text.
- Use one shutdown path for the window and tray, stop workers before closing SQLite, keep the app open if saving fails, and prevent two recorders from sharing a data directory. Deliver tray notifications on the Qt UI thread.
- Upgrade to Python 3.13.17 and pinned dependencies, including Pillow 13.0.0. Add Windows CI, fault-injection regression tests, source/native-hook smoke tests, and packaged smoke validation.
- Build in new isolated output directories. Exclude personal configuration, databases and logs; include a clean example, dependency/build manifest, licenses and SHA-256 checksum.

### Upgrade notes

Exit and back up the existing installation before replacing program files. Preserve `tracker.db` and `config.json`.

The configured retention period is now enforced at startup. The default keeps 365 days, including today. Choose Forever before upgrading if you need all history. Retained historical screen-time aggregates are preserved; previously inflated values cannot be reconstructed reliably.

Portable data stays beside the executable. A new non-portable installation uses `%LOCALAPPDATA%/ActivityTrack`; `--data-dir` can select another location. See README for build and validation commands.
