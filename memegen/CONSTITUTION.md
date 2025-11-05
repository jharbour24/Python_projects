# Memegen Constitution

This document defines the hard rules for meme content. All generated candidates must pass these checks.

## Core Values

1. **Punch up, not down**: Target systems and situations, not people
2. **Protect privacy**: No doxxing, outing, or personal info
3. **Affectionate humor**: In-jokes should feel like shared laughs, not meanness
4. **Local specificity**: Ground content in Brooklyn/NYC culture
5. **Safe for community**: No slurs, hate speech, or explicit content

---

## Rules (Auto-Enforced)

### Rule 1: No Slurs or Hate Speech
**Status:** BLOCKING

**What's blocked:**
- Slurs targeting any protected class
- Hate speech or derogatory language about identity

**Examples:**

❌ **BLOCKED:** Any use of slurs (f-word, t-word, etc.)

✅ **ALLOWED:** "queer Brooklyn," "gay agenda," community-reclaimed terms in affectionate context

---

### Rule 2: No Explicit Sexual Content
**Status:** BLOCKING

**What's blocked:**
- Graphic sexual descriptions
- References that could out people's sexual behavior
- Venue-specific hookup references (could dox spots)

**Examples:**

❌ **BLOCKED:** "best hookup spot in Bushwick" (doxxes venue)

❌ **BLOCKED:** "saw [person] with [person]" (outs people)

✅ **ALLOWED:** "going out to 'network'" (vague innuendo, doesn't target)

---

### Rule 3: No Doxxing or Private Info
**Status:** BLOCKING

**What's blocked:**
- Phone numbers, addresses, personal details
- Specific venue names without permission
- Identifying information about individuals

**Examples:**

❌ **BLOCKED:** "the venue at 123 Main Street"

❌ **BLOCKED:** "Jake from Bushwick who works at [place]"

✅ **ALLOWED:** "a venue in Bushwick"

✅ **ALLOWED:** "someone's friend who's always late"

---

### Rule 4: No Violence or Threats
**Status:** BLOCKING

**What's blocked:**
- References to violence, harm, or threats
- Aggressive or hostile language

**Examples:**

❌ **BLOCKED:** "I'll kill anyone who skips the line"

❌ **BLOCKED:** "assault on my senses" (even metaphorical)

✅ **ALLOWED:** "the MTA's war on punctuality" (systemic critique)

---

### Rule 5: Profanity Limited to PG-13
**Status:** BLOCKING

**What's blocked:**
- F-word, c-word, and other strong profanity
- R-rated language

**What's allowed:**
- Hell, damn, ass (mild)
- Creative workarounds ("freakin'", "what the heck")

**Examples:**

❌ **BLOCKED:** "this fucking sucks"

✅ **ALLOWED:** "this is hell"

✅ **ALLOWED:** "absolutely unhinged"

---

### Rule 6: Local Specificity Required
**Status:** BLOCKING

**What's required:**
At least ONE reference to:
- Brooklyn neighborhoods (Bushwick, Bed-Stuy, Williamsburg, Ridgewood)
- NYC transit (L train, G train, JMZ, MTA)
- Venue culture (cover, line, dress code, etc.)

**Examples:**

❌ **BLOCKED:** "going to a party is hard"

✅ **ALLOWED:** "going to a Bushwick party is a pilgrimage"

---

### Rule 7: ALL CAPS Only for "Slightly Unhinged" Tone
**Status:** BLOCKING

**Rationale:** ALL CAPS should signal intentional chaotic energy, not laziness

**Examples:**

❌ **BLOCKED:** "TAKING THE TRAIN" (tone: dry)

✅ **ALLOWED:** "TAKING THE TRAIN" (tone: slightly unhinged)

✅ **ALLOWED:** "taking the train" (tone: dry)

---

### Rule 8: No Hashtags
**Status:** BLOCKING

**Rationale:** Hashtags feel spammy and break immersion

**Examples:**

❌ **BLOCKED:** "Brooklyn nightlife #brooklyn #queer"

✅ **ALLOWED:** "Brooklyn nightlife"

---

### Rule 9: No Venue Doxxing
**Status:** WARNING (soft block)

**What's discouraged:**
- Naming specific venues, especially for negative content
- Identifying DIY/underground spaces

**What's allowed:**
- Venues that actively promote their events publicly
- Generic references ("a warehouse in Bushwick")

**Examples:**

❌ **AVOID:** "[VenueName]'s cover charge is absurd"

✅ **BETTER:** "cover charge at a Bushwick spot: $25 for a warehouse"

⚠️ **CONTEXT-DEPENDENT:** "[BigPublicVenue] sold out" (public venue, positive context)

---

### Rule 10: Punch Up, Not Down
**Status:** WARNING (soft block)

**Required:** Content should target systems, not individuals or marginalized groups

**Good targets:**
- MTA, transit systems
- Cover charges, venue policies
- Weather, gentrification, rent
- Your own behavior (self-deprecation)

**Bad targets:**
- Specific people
- Body types, appearances
- Tourists, "bridge and tunnel" folks (punches down)

**Examples:**

❌ **AVOID:** "tourists in Brooklyn looking lost"

✅ **BETTER:** "me in Bushwick looking for a venue with no signage"

---

### Rule 11: Affectionate Tone
**Status:** GUIDELINE (not enforced)

**Encouraged:** Humor should feel like you're laughing WITH the community, not AT it

**Examples:**

✅ **GOOD:** "taking the L train: a spiritual journey"

❌ **MEAN:** "people who take the L train are idiots"

---

### Rule 12: No Stereotype Humor
**Status:** GUIDELINE (not enforced)

**Discouraged:** Jokes that rely on stereotypes about queer people, even if "affectionate"

**Examples:**

❌ **AVOID:** "all lesbians drive Subarus" (tired stereotype)

✅ **BETTER:** "Brooklyn lesbian car ownership: Subaru or pure spite"

---

## Enforcement

### Blocking Rules (1-8)
These are **hard blocks**. Content violating these rules is automatically rejected.

### Warning Rules (9-10)
These trigger **warnings** but may not block. Human review recommended.

### Guidelines (11-12)
These are **stylistic recommendations**. Not enforced by code, but preferred.

---

## Exemptions and Context

### Reclaimed Language
Community members may use reclaimed terms (queer, dyke, etc.) in affectionate, self-referential ways. Context matters.

✅ **ALLOWED:** "queer Brooklyn nightlife"

✅ **ALLOWED:** "dyke bars in the city" (historical/cultural reference)

### Systemic Critique
Strong language is allowed when critiquing systems, not people.

✅ **ALLOWED:** "the MTA's cruel and unusual delays"

❌ **BLOCKED:** "MTA workers are awful"

---

## Appeal Process

If a candidate is wrongly blocked:
1. Check which rule triggered
2. Verify the content doesn't actually violate the rule
3. File an issue or adjust constitution.py logic
4. Add to exemption list if appropriate

---

## Version History

- **v1.0** (2025-11-05): Initial constitution
- Future: Add exemption lists, update based on community feedback
