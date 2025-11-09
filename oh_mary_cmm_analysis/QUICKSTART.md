# Quick Start Guide — Real Data Collection

**Goal:** Collect 100+ real social media posts about "Oh Mary!" in ~1 hour

## ⚡ Super Quick Start (Recommended)

```bash
cd oh_mary_cmm_analysis
python collect_all_data.py
```

This launches an **interactive menu** that guides you through:
1. ✅ Reddit API setup (10 min, automated)
2. ✅ TikTok manual collection (30 min, safe)
3. ✅ Instagram manual collection (30 min, safe)
4. ✅ Run analysis

---

## 🛡️ Important: Why No Login Required

**You do NOT need to provide your login credentials** for any platform. Here's why:

### ❌ What We WON'T Do (Unsafe/Illegal)
- Use your personal login credentials
- Automate actions with your account
- Violate Terms of Service
- Risk account suspension

### ✅ What We WILL Do (Safe/Legal)
- **Reddit**: Use official API with your own app credentials (not your password)
- **TikTok**: Manual collection of public posts (no login needed)
- **Instagram**: Manual collection via public viewers (no login needed)

---

## 🎯 Three Collection Methods

### Method 1: Reddit API (Automated) — 10 minutes

```bash
python setup_reddit.py
```

**What this does:**
1. Guides you to create a Reddit "app" (not your account password!)
2. Gives you API credentials (client_id, client_secret)
3. Configures the scraper to use official Reddit API
4. Automatically collects 100+ posts

**Steps:**
1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app"
3. Name: `oh_mary_analysis`, Type: `script`
4. Copy client_id (14 chars) and client_secret (27 chars)
5. Paste into setup script when prompted

**Result:** ~100 Reddit posts automatically collected ✅

---

### Method 2: TikTok Manual Collection — 30 minutes

```bash
python collect_tiktok.py
```

**What this does:**
1. Opens interactive form
2. You search TikTok in browser (no login needed!)
3. Copy data from each video into form
4. Script saves to CSV automatically

**Steps:**
1. Open TikTok in browser: https://tiktok.com
2. Search: `#OhMary` or `#OhMaryBroadway`
3. Click each video, copy: URL, likes, comments, caption
4. Enter into script form
5. Repeat for 50 videos (~30 min)

**Tips:**
- You can see TikTok content WITHOUT logging in
- Use incognito mode for clean search results
- Focus on videos with 1k+ likes (high engagement)
- Can pause and resume anytime

**Result:** ~50 TikTok videos collected ✅

---

### Method 3: Instagram Manual Collection — 30 minutes

```bash
python collect_instagram.py
```

**What this does:**
1. Opens interactive form
2. You use Instagram viewers (no login needed!)
3. Copy data from each post into form
4. Script saves to CSV automatically

**Steps:**
1. Use Instagram viewers (NO LOGIN REQUIRED):
   - **Picuki.com** — View any Instagram content
   - **Imginn.com** — Another Instagram viewer
   - **Inflact.com** — Instagram web viewer

2. Search: `#OhMary` or `@colewschooler`

3. Click each post, copy: URL, likes, comments, caption

4. Enter into script form

5. Repeat for 50 posts (~30 min)

**Tips:**
- These viewers show public Instagram WITHOUT login
- Perfectly legal and safe
- Can pause and resume anytime
- Focus on posts with 500+ likes

**Result:** ~50 Instagram posts collected ✅

---

## 📊 Sample Size Guide

| Items | Analysis Quality | Time Required |
|-------|------------------|---------------|
| 25+ | Minimum viable | 30 min |
| 50+ | Good | 1 hour |
| 100+ | Excellent | 1.5 hours |
| 200+ | Professional | 2 hours |

**Recommendation:** Aim for 100+ total items (mix of platforms)

---

## 🚀 Complete Workflow

### Option A: Interactive (Easiest)

```bash
python collect_all_data.py
```

Follow the menu:
1. Setup Reddit API → automated collection
2. Collect TikTok → manual 50 videos
3. Collect Instagram → manual 50 posts
4. Run analysis → get results!

### Option B: Step-by-Step

```bash
# Step 1: Reddit (10 min)
python setup_reddit.py

# Step 2: TikTok (30 min)
python collect_tiktok.py

# Step 3: Instagram (30 min)
python collect_instagram.py

# Step 4: Run analysis
python src/main.py
```

### Option C: Reddit Only (Fastest)

```bash
# Just Reddit API for quick results
python setup_reddit.py
python src/main.py
```

Gets you ~100 posts in 10 minutes!

---

## 🔍 What You'll Search For

### Reddit Keywords
- Subreddits: r/broadway, r/musicals, r/nyc, r/gaybros, r/LGBT
- Search terms: "Oh Mary", "Oh Mary Broadway", "Cole Escola"

### TikTok Hashtags
- `#OhMary` (main hashtag)
- `#OhMaryBroadway`
- `#BroadwayTikTok` + "Oh Mary"

### Instagram Tags
- `#OhMary`
- `#OhMaryBroadway`
- Location: "Lyceum Theatre"
- `@colewschooler` (creator account)

---

## ✅ After Collection

Once you have data collected, run:

```bash
python src/main.py
```

**You'll get:**
- Comprehensive report: `outputs/reports/report.md`
- 8 visualizations: `outputs/visualizations/`
- CSV data: `data/processed/`
- CMM Score: 0-100 movement rating

**Analysis takes ~2 minutes to run**

---

## 🆘 Troubleshooting

### "No data collected"
**Solution:** Make sure files are named:
- `data/raw/reddit_manual.csv` (not reddit_manual_template.csv)
- `data/raw/tiktok_manual.csv`
- `data/raw/instagram_manual.csv`

### "Reddit API error"
**Solution:** Re-run `python setup_reddit.py` and check credentials

### "Not enough data"
**Solution:** Analysis works with as few as 10 posts, but 50+ recommended

### "Can't see TikTok/Instagram without login"
**Solution:**
- TikTok: Most content visible without login (try incognito mode)
- Instagram: Use Picuki.com, Imginn.com, or Inflact.com

---

## 💡 Pro Tips

1. **Start with Reddit API** — Easiest, gets you 100 posts in 10 min
2. **Open browser + script side-by-side** — Makes manual collection faster
3. **Focus on high-engagement posts** — Better quality data
4. **You can pause anytime** — Data saves as you go
5. **Quality > Quantity** — 50 good posts > 100 mediocre ones

---

## 🔐 Security Reminder

✅ **DO:**
- Create Reddit API app (safe, official method)
- Use public Instagram viewers (legal, no login)
- Manually collect public TikTok data

❌ **DON'T:**
- Share your passwords with anyone (including AI)
- Use your personal login for automation
- Scrape with unofficial bots

**This method is 100% safe, legal, and compliant!**

---

## 📈 Expected Results

With **100+ real posts**, you'll see:

- **Overall CMM Score**: 30-80 (likely 50-60 for Oh Mary!)
- **Key behaviors detected**:
  - Identity resonance (queer representation)
  - Evangelism (telling friends to go)
  - Repeat attendance (seeing it multiple times)
  - Community formation (rush line culture)

- **Strategic insights**:
  - Which constituencies are forming movements
  - Whether to lean into movement marketing
  - ROI on community-building vs traditional ads

---

## 🎉 Success Criteria

You're ready to run analysis when you have:
- ✅ At least 50 total items (any mix of platforms)
- ✅ Data saved to `data/raw/*.csv` files
- ✅ Mix of different post types (reviews, photos, discussion)

Then just run: `python src/main.py` and you're done!

---

**Questions? Run:** `python collect_all_data.py` for interactive help
