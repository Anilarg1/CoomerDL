![Windows Compatibility](https://img.shields.io/badge/Windows-10%2C%2011-blue)
![Downloads](https://img.shields.io/github/downloads/Anilarg1/CoomerDL/total)

# SimpCity Scraper

**SimpCity Scraper** is a Python desktop downloader focused on SimpCity threads and supported embedded file hosts such as Bunkr, PixelDrain, TurboVid, GoFile, Filester, and JPG6/JPG5.

The app now uses a **PySide6 / Qt** interface. The old Tkinter / CustomTkinter UI is no longer the active desktop UI.

---

## Features

- Modern **PySide6** desktop interface
- Download images, videos, and compressed files from supported sites
- Multithreaded downloads with configurable limits
- Per-file and global progress tracking
- Exportable logs
- Cookies support for SimpCity
- SQLite download database
- Configurable naming modes
- Configurable folder structure
- English-only interface

### Supported file types

**Videos**
- `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.flv`, `.wmv`, `.m4v`

**Images**
- `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`

**Documents**
- `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`

**Compressed**
- `.zip`, `.rar`, `.7z`, `.tar`, `.gz`

---

## Supported sites

- [coomer.su](https://coomer.su/)
- [kemono.su](https://kemono.su/)
- [erome.com](https://www.erome.com/)
- [bunkr-albums.io](https://bunkr-albums.io/)
- [simpcity.su](https://simpcity.su/)
- [jpg5.su](https://jpg5.su/)
- [jpg6.su](https://jpg6.su/)
- [pixeldrain.com](https://pixeldrain.com/)
- [turbo.cr / turbovid.cr](https://turbo.cr/)
- [gofile.io](https://gofile.io/)
- Filester domains such as `filester.si` and `filester.gg`

---

## Screenshots / usage

1. Launch the application
2. Paste a supported URL
3. Select your download folder
4. Choose the content types you want
5. Click **Download**

https://github.com/user-attachments/assets/f11a4681-4c6f-4797-a8a5-8eabe5e2cdfa



---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Anilarg1/CoomerDL.git
cd CoomerDL
```

### 2. Create and activate a virtual environment

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (CMD)**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python main.py
```

---

## Requirements

- Python 3.10+
- Windows 10 or Windows 11

---

## Architecture

Downloader internals are documented in [docs/architecture.md](docs/architecture.md).

File-host support can be tested with:

```bash
python -m pytest tests/filehosts
```

---

## Settings overview

The Settings window currently includes:

- **General**: English-only application info
- **Downloads**: max downloads, retries, retry interval, naming mode, folder structure
- **Cookies**: SimpCity cookies import/save/clear
- **Database**: browse, export, and manage download records

---

## Fork guide

If you want to customize the project:

### 1. Fork on GitHub
Use the GitHub **Fork** button on the repository page.

### 2. Clone your fork

```bash
git clone https://github.com/YOUR_USERNAME/CoomerDL.git
cd CoomerDL
```

### 3. Add the original repository as upstream

```bash
git remote add upstream https://github.com/Anilarg1/CoomerDL.git
```

### 4. Keep your fork updated

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

### 5. Create your own branch

```bash
git checkout -b my-changes
```

---

## SimpCity cookies

SimpCity may require cookies for access depending on the content or session state.

The app includes a **Cookies** tab where you can:

- paste cookies JSON
- import cookies from a file
- save cookies
- clear saved cookies

These cookies are only intended for SimpCity support inside the app.

---

## Download database

SimpCity Scraper stores downloaded file records in a local SQLite database so it can:

- avoid re-downloading known files
- export database records
- manage entries from the Settings window

Default database location:

```text
resources/config/downloads.db
```

---

## Logs

The app keeps exportable logs and uses a domain-aware log format in the UI.

Example:

```text
bunkr: Resolving /f/ URL ...
coomer: Fetching user posts ...
erome: Processing album URL ...
system: Download settings were applied successfully.
```

Default logs folder:

```text
resources/config/logs/
```

---

## Community

Join the Discord server:

[![Join Discord](https://img.shields.io/badge/Join-Discord-7289DA.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ku8gSPsesh)

---

## Downloads

You can find the latest public builds on the GitHub Releases page:

- [Releases](https://github.com/Anilarg1/CoomerDL/releases)
