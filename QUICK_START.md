# Quick Start: 5 Steps to Your Data

**Total time: 30-60 minutes** (mostly computer running on its own)

---

## 1. Get the Code (2 minutes)

### Option A: Using Terminal/Command Prompt (Recommended)

**Windows:**
```bash
cd Desktop
git clone -b claude/broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt https://github.com/jharbour24/Python_projects.git
cd Python_projects
```

**Mac:**
```bash
cd Desktop
git clone -b claude/broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt https://github.com/jharbour24/Python_projects.git
cd Python_projects
```

### Option B: Download from Website

Go to: **https://github.com/jharbour24/Python_projects**

Click the green `<> Code` button → Click `Download ZIP`

Unzip it on your Desktop

---

## 2. Install Python (5 minutes)

Go to: **https://www.python.org/downloads/**

Download and install (Windows: check "Add Python to PATH" ✓)

---

## 3. Open Command Prompt/Terminal

**Windows:** Press `Windows Key + R`, type `cmd`, press Enter

**Mac:** Press `Cmd + Space`, type `Terminal`, press Enter

---

## 4. Run These Commands

**Windows:**
```bash
cd Desktop\Python_projects-claude-broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt
pip install -r requirements.txt
python run_full_scrape.py
```

**Mac:**
```bash
cd Desktop/Python_projects-claude-broadway-tony-dataset-01Q2qbxaKfYdfo4zsXzTTrtt
pip3 install -r requirements.txt
python3 run_full_scrape.py
```

---

## 5. Wait for It to Finish (30-60 minutes)

Don't close the window! You'll see progress updates.

When done, your data will be in the `data` folder:
- `show_producer_counts_ibdb.csv` - Producer counts
- `tony_outcomes.csv` - Tony winners (already complete!)

---

## Open Your Data

Right-click the CSV files → Open with Excel or Google Sheets

**Done!** 🎭

---

## Need Help?

See **BEGINNER_SETUP_GUIDE.md** for detailed step-by-step instructions with troubleshooting.
