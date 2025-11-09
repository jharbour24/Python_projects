# Automated TikTok & Instagram Collection Guide

## 🎯 Quick Start (5 Minutes Setup)

### Option 1: Apify (Recommended)

```bash
# 1. Setup
python setup_apify.py

# 2. Install client
pip install apify-client

# 3. Run automated collection
python collect_automated.py
```

**Cost:** $4-8 for 200 items (Free tier includes $5 credit)

---

### Option 2: RapidAPI

```bash
# 1. Setup
python setup_rapidapi.py

# 2. Run automated collection
python collect_automated.py
```

**Cost:** $9.99/month subscription (includes 5000 requests)

---

## 📋 Complete Workflow

### Step 1: Choose Your Service

| Feature | Apify | RapidAPI |
|---------|-------|----------|
| **Pricing** | Pay-per-use | Monthly subscription |
| **Free tier** | $5 credit | No free tier |
| **Cost for 200 items** | $4-8 | $9.99/month |
| **Best for** | One-time analysis | Regular scraping |
| **Setup** | Instant | Requires plan selection |

**Recommendation:** Use **Apify** for this one-time analysis (free $5 credit covers it).

---

### Step 2: Set Up API Credentials

#### Apify Setup (Recommended)

1. **Create account:** https://apify.com/sign-up
2. **Get API token:** https://console.apify.com/account/integrations
3. **Run setup:**
   ```bash
   python setup_apify.py
   ```
4. **Enter your API token when prompted**

The script will test your connection and confirm it works.

#### RapidAPI Setup (Alternative)

1. **Create account:** https://rapidapi.com/auth/sign-up
2. **Subscribe to scrapers:**
   - TikTok: https://rapidapi.com/ti-services/api/tiktok-scraper7
   - Instagram: https://rapidapi.com/social-api1-instagram/api/instagram-scraper-api2
3. **Get API key:** https://rapidapi.com/developer/security
4. **Run setup:**
   ```bash
   python setup_rapidapi.py
   ```

---

### Step 3: Install Dependencies

```bash
pip install apify-client requests
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

---

### Step 4: Run Automated Collection

```bash
python collect_automated.py
```

#### What it does:

1. **Asks which platforms** to collect (TikTok, Instagram, or both)
2. **Asks for hashtags** (e.g., `OhMary, OhMaryBroadway`)
3. **Asks how many items** per platform (recommended: 50-100)
4. **Shows cost estimate** based on your inputs
5. **Confirms** before charging your account
6. **Collects data** automatically (5-15 minutes)
7. **Saves to CSV** files in `data/raw/`

#### Example session:

```
Which platforms?
1. TikTok only
2. Instagram only
3. Both TikTok and Instagram

Choice (1-3): 3

Enter hashtags to search (comma-separated):
Example: OhMary, OhMaryBroadway
Hashtags: OhMary, OhMaryBroadway, ColeEscola

How many items per platform?
Recommended: 50-100 per platform
Max items: 100

💰 Cost Estimate
------------------------------------------------------------------
TikTok (100 videos):     $3.50
Instagram (100 posts):  $2.00
------------------------------------------------------------------
Estimated Total:        $5.50

Using: Apify
Check balance: https://console.apify.com/

⚠️  This will charge your API account.
Proceed with collection? (yes/no): yes

STARTING AUTOMATED COLLECTION
This will take 5-15 minutes depending on volume...

[Collection happens automatically...]

✅ COLLECTION COMPLETE!
------------------------------------------------------------------
📊 Results:
   TikTok videos:   100
   Instagram posts: 100
   Total items:     200

⏱️  Time: 420 seconds (7.0 minutes)
💰 Estimated cost: $5.50

🚀 Next step: Run analysis
   python src/main.py
```

---

## 📊 What Gets Collected

### TikTok Data

For each video:
- `video_id` — Unique TikTok video ID
- `url` — Direct link to video
- `author` — TikTok username
- `caption` — Video description/caption
- `hashtags` — Comma-separated hashtags
- `likes` — Like count
- `comments` — Comment count
- `shares` — Share count
- `views` — View count
- `created_at` — Timestamp
- `platform` — "tiktok"
- `scraped_at` — When collected

### Instagram Data

For each post:
- `post_id` — Instagram shortcode
- `url` — Direct link to post
- `author` — Instagram username
- `caption` — Post caption
- `hashtags` — Comma-separated hashtags
- `likes` — Like count
- `comments_count` — Comment count
- `created_at` — Timestamp
- `post_type` — photo/video/carousel
- `platform` — "instagram"
- `scraped_at` — When collected

---

## 💰 Cost Breakdown

### Apify Pricing

**What you pay for:**
- Compute units (processing time)
- Dataset operations (storing results)
- Proxy usage (residential IPs)

**Actual costs for Oh Mary! analysis:**

| Items | TikTok Cost | Instagram Cost | Total |
|-------|-------------|----------------|-------|
| 50 | $1.75 | $1.00 | $2.75 |
| 100 | $3.50 | $2.00 | $5.50 |
| 200 | $7.00 | $4.00 | $11.00 |

**Free tier:** $5 credit = ~90-140 items total

### RapidAPI Pricing

**Monthly subscription:**
- Basic: $9.99/month (5000 requests) = ~500-1000 items
- Pro: $24.99/month (20000 requests) = ~2000-4000 items

**For one-time analysis:** Apify is cheaper (just use free $5 credit)

---

## 🔧 Troubleshooting

### "No API credentials found"

**Solution:**
```bash
# Run setup first
python setup_apify.py
# OR
python setup_rapidapi.py
```

### "Apify client not installed"

**Solution:**
```bash
pip install apify-client
```

### "Insufficient API credits"

**Solution:**
- Apify: Add credits at https://console.apify.com/billing
- RapidAPI: Upgrade plan or wait for monthly reset

### "Connection timeout"

**Solution:**
- Check internet connection
- Try again (APIs can be slow)
- Reduce `max_items` count

### "Rate limit exceeded"

**Solution:**
- Wait 5-10 minutes
- Reduce collection speed (built-in delays)
- For RapidAPI: Check monthly quota

### Collection interrupted

**Solution:**
- Partial data may be saved to CSV
- Can merge with additional runs
- Check `data/raw/collection_log.json` for what was collected

---

## 📈 Performance Tips

### 1. Optimize Hashtag Selection

**Good hashtags:**
- `OhMary` (main hashtag)
- `OhMaryBroadway` (specific)
- `ColeEscola` (creator)

**Avoid:**
- Too generic (`Broadway`, `Musical`) = lots of irrelevant content
- Too rare (`OhMaryFan123`) = no results

### 2. Balance Speed vs. Cost

| Max Items | Time | Cost | Quality |
|-----------|------|------|---------|
| 25 per platform | 3 min | $1-2 | Good enough |
| 50 per platform | 5 min | $3-4 | Recommended |
| 100 per platform | 10 min | $6-8 | Excellent |

### 3. Combine with Reddit

```bash
# Get Reddit data (free, automated)
python setup_reddit.py

# Get TikTok/Instagram (paid, automated)
python collect_automated.py

# Total: 300+ items in ~15 minutes for ~$5
```

---

## 🆚 Comparison: Automated vs. Manual

| Factor | Automated (This Guide) | Manual |
|--------|----------------------|--------|
| **Time** | 10 minutes | 60 minutes |
| **Cost** | $5-10 | Free |
| **Data quality** | Excellent | Excellent |
| **Effort** | Minimal | High |
| **Legal** | ✅ Yes | ✅ Yes |
| **Completeness** | 100% | 95% (human error) |
| **Scalable** | Yes (500+ items easy) | No (max ~100) |

**Recommendation:** For 200+ items, automation is worth the $5-10 cost.

---

## 🔐 Security & Privacy

### What's Safe

✅ **Using third-party APIs:**
- Apify and RapidAPI are legitimate services
- They handle the legal/ToS complexity
- They manage anti-bot detection
- You're not directly accessing platforms

✅ **API tokens:**
- Store locally (not committed to git)
- Can be revoked anytime
- Don't grant account access

### What's NOT Safe (We Don't Do)

❌ **Direct scraping:**
- Violates platform ToS
- Gets detected/blocked
- Legal risk

❌ **Using your login credentials:**
- Risk account ban
- Security exposure
- Unnecessary with APIs

---

## 📚 API Documentation

### Apify TikTok Scraper

- **Docs:** https://apify.com/clockworks/tiktok-scraper
- **Input:** Hashtags, max results
- **Output:** Video metadata, statistics
- **Rate limit:** Handled automatically
- **Cost:** ~$0.035 per video

### Apify Instagram Scraper

- **Docs:** https://apify.com/apify/instagram-scraper
- **Input:** Hashtags, profiles, locations
- **Output:** Post metadata, statistics
- **Rate limit:** More restrictive than TikTok
- **Cost:** ~$0.02 per post

---

## 🎯 Best Practice Workflow

For Oh Mary! analysis, follow this workflow:

### Day 1: Setup (10 min)

```bash
# Reddit (free, automated)
python setup_reddit.py

# Apify (paid, automated)
python setup_apify.py
pip install apify-client
```

### Day 2: Collection (10 min)

```bash
# Run automated collection
python collect_automated.py

# Choose:
# - Both platforms
# - Hashtags: OhMary, OhMaryBroadway
# - 75 items per platform
# = 150 items for ~$4 (within free $5 credit!)
```

### Day 3: Analysis (5 min)

```bash
# Run analysis on all collected data
python src/main.py

# Review results
# - outputs/reports/report.md
# - outputs/visualizations/
```

**Total time:** 25 minutes
**Total cost:** $0 (using free credits)
**Total items:** 250+ (100 Reddit + 150 social)

---

## ✅ Success Checklist

Before running analysis, make sure you have:

- [ ] API credentials configured (Apify or RapidAPI)
- [ ] Dependencies installed (`pip install apify-client`)
- [ ] Enough API credits ($5+ for Apify, active subscription for RapidAPI)
- [ ] Collected data from at least one platform
- [ ] CSV files exist in `data/raw/`
- [ ] At least 50 total items collected

---

## 🚀 Next Steps After Collection

Once you have data:

```bash
# Run complete analysis
python src/main.py

# Results appear in:
# - outputs/reports/report.md (main findings)
# - outputs/visualizations/ (8 charts)
# - data/processed/ (CSV exports)
```

The analysis will automatically:
- Load all CSV files from `data/raw/`
- Process TikTok, Instagram, and Reddit data
- Calculate 8 CMM metrics
- Generate visualizations
- Create comprehensive report

**Analysis time:** ~2 minutes for 200 items

---

## 💡 Pro Tips

1. **Start small:** Test with 10-20 items first to verify everything works
2. **Use free credit:** Apify's $5 credit covers 100-150 items
3. **Combine sources:** Reddit (free) + TikTok/Instagram (paid) = best value
4. **Monitor costs:** Check https://console.apify.com/billing during collection
5. **Save logs:** Collection creates `collection_log.json` with metadata

---

## 📞 Support

If you encounter issues:

1. **Check logs:** `data/raw/collection_log.json`
2. **Test connection:** Rerun `setup_apify.py` or `setup_rapidapi.py`
3. **Verify balance:**
   - Apify: https://console.apify.com/billing
   - RapidAPI: https://rapidapi.com/developer/billing
4. **Reduce load:** Start with fewer items to test

---

**You're now ready for fully automated TikTok & Instagram collection! 🎉**

Run `python collect_automated.py` to get started.
