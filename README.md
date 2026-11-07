# Downloads Folder Organizer

A Python script that keeps today's downloads within reach and sorts older files into category folders automatically.

Built with Python's standard library and an object-oriented design, the organizer scans a folder at a configurable interval, classifies files by extension, and moves eligible files into subfolders such as `Audio`, `Images`, and `Documents`.

## Features

- Organizes files by extension using a configurable category mapping.
- Keeps files created today in the main Downloads folder.
- Skips configured temporary download files, shortcuts, and specific filenames.
- Generates numbered filenames when a destination is already occupied.
- Supports a dry run that reports planned moves without creating folders or moving files.
- Reports scanned, moved, planned, skipped, and failed files.
- Repeats scans at a configurable interval and supports stopping with Ctrl+C.
- Scans the top level only; existing subfolders are left untouched.

## Organization rules

A file is eligible for organization when:

1. It is a file directly inside the configured folder.
2. Its name and extension are not excluded.
3. Its creation date is earlier than today's local date.

The date comparison uses **calendar dates**, rather than a rolling 24-hour window. A file created yesterday can be organized even if it is less than 24 hours old. Files dated today or in the future remain in place.

Classification depends on the filename extension, not the contents of the file.

Example with the configuration below:

| File | Creation date | Result |
| --- | --- | --- |
| `song.mp3` | Before today | `Downloads/Audio/song.mp3` |
| `photo.png` | Before today | `Downloads/Images/photo.png` |
| `notes.txt` | Today | Remains in `Downloads` |
| `download.crdownload` | Any date | Excluded |
| `desktop.ini` | Any date | Excluded |

If `Audio/song.mp3` already exists, the organizer looks for an available name such as `song (1).mp3`, `song (2).mp3`, and so on. Unmapped extensions use the classifier's fallback category.

## Requirements

- Windows.
- Python 3.10 or newer.
- An existing folder to organize.

No third-party packages are required.

This version targets Windows, including its filesystem creation-date metadata and the behavior of `Path.rename()` when a destination already exists.

## Getting started

1. Download or clone this repository.
2. Configure the folder, categories, exclusions, and runner options in the script's setup section.
3. Open a terminal in the repository folder and run:

   ```powershell
   py -3 downloads_organizer.py
   ```

The command assumes the entry-point file is named `downloads_organizer.py`. Use the actual filename if yours differs.

Start with `dry_run=True` to review the counts, then set `dry_run=False` to enable moves.

## Configuration

The setup below shows how to connect the classes. Place it after the class definitions in `downloads_organizer.py`, replacing the existing setup block if necessary.

```python
from pathlib import Path


if __name__ == "__main__":
    downloads_folder = Path.home() / "Downloads"

    categories = {
        "Audio": [".mp3", ".wav", ".flac", ".m4a"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "Videos": [".mp4", ".mkv", ".webm", ".avi", ".mov"],
        "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".csv"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    }

    ignored_suffixes = {".crdownload", ".part", ".tmp", ".lnk"}
    ignored_names = {"desktop.ini", "Thumbs.db"}

    scanner = DownloadScanner(
        downloads_folder=downloads_folder,
        ignored_suffixes=ignored_suffixes,
        ignored_names=ignored_names,
    )
    classifier = FileClassifier(categories)
    mover = FileMover(downloads_folder)
    organizer = DownloadOrganizer(scanner, classifier, mover)

    runner = OrganizerRunner(
        organizer=organizer,
        interval_seconds=3600,
        dry_run=True,
    )
    runner.run_forever()
```

### Target folder

`Path.home() / "Downloads"` is a common starting point. If your Downloads folder is stored elsewhere, set `downloads_folder` to its actual path.

To try the organizer on a separate folder:

```python
downloads_folder = Path.cwd() / "downloads_test"
```

Create that folder and add sample files before running the script. `Path.cwd()` refers to the terminal's current working directory.

### Categories and exclusions

Category names become subfolder names. Add or remove extensions in `categories` to change how files are grouped. Extension entries include the leading dot, for example `".mp3"`.

`ignored_suffixes` applies to every file with a listed extension. `ignored_names` applies to specific full filenames.

For example, excluding `desktop.ini` and `Thumbs.db` by name still allows other files such as `settings.ini` or `customers.db` to be organized.

### Scan interval and stopping

`interval_seconds` controls the wait between scans. The example uses `3600` seconds, or one hour. Use a positive integer.

The runner performs an initial scan when started and continues while the Python process is running. Press **Ctrl+C** in the terminal to stop it. Automatic startup with Windows requires a separate operating-system setup.

## Running a single scan

After creating an `organizer` with the setup above, use `organize_once()` instead of starting the runner:

```python
# Preview eligible moves.
report = organizer.organize_once(dry_run=True)
print(report)
```

To move eligible files:

```python
report = organizer.organize_once(dry_run=False)
print(report)
```

When no `today` value is supplied, the organizer determines the current local date for that scan. A continuously running instance therefore evaluates the date again on subsequent scans.

## Understanding the report

Example after a scan with moves enabled:

```python
{
    "scanned": 100,
    "moved": 50,
    "planned": 0,
    "skipped": 50,
    "failed": 0,
}
```

| Field | Meaning |
| --- | --- |
| `scanned` | Files counted at the top level, including excluded files. Directories are not counted. |
| `moved` | Eligible files successfully moved during a real run. |
| `planned` | Eligible files that would be moved during a dry run. |
| `skipped` | Excluded files, plus non-excluded files dated today or in the future. |
| `failed` | Attempted moves that raised a handled filesystem error. |

For example, 50 eligible older files, 20 excluded files, and 30 non-excluded files created today produce 50 moves and 50 skips. In a dry run, the same folder produces `moved=0`, `planned=50`, and `skipped=50`.

A dry run counts planned moves; it does not guarantee that every move will succeed when executed later. A file may become unavailable or inaccessible in the meantime.

## Class design

| Class | Responsibility |
| --- | --- |
| `DownloadFile` | Represents a file and exposes its path, filename, extension, creation date, and size. |
| `FileClassifier` | Maps a file extension to a category. |
| `DownloadScanner` | Reads the target folder and filters configured exclusions. |
| `FileMover` | Builds destination paths, finds available names, creates category folders, and moves files. |
| `DownloadOrganizer` | Applies the date rule, coordinates a single scan, and builds its report. |
| `OrganizerRunner` | Repeats organization at the configured interval and manages stopping. |

The classes work together through composition, keeping classification, scanning, moving, and scheduling separate.

## Planned improvement

- File logging for scan reports and errors. The current version uses console output.
