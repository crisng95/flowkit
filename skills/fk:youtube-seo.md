# fk:youtube-seo — Generate YouTube Metadata (SEO-Optimized)

Generate SEO-optimized YouTube metadata: hook title, description, hashtags, and niche keywords.

Usage: `/fk:youtube-seo <project_id> [--language vi] [--niche military-documentary]`

## Step 1: Load project context + channel rules

```bash
curl -s http://127.0.0.1:8100/api/projects/<PID>
curl -s "http://127.0.0.1:8100/api/videos?project_id=<PID>"
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```

Extract:
- **Story**: full narrative arc — what happens, conflict, resolution
- **Characters**: key names (for title/description keyword density)
- **Language**: target audience language (vi, en, etc.)
- **Material/genre**: realistic, anime, etc. → determines niche
- **Video duration**: from scene count × avg duration

### Load channel rules (if channel specified)

If `--channel <name>` is provided (or inferred from context), load SEO defaults from channel rules:

```bash
cat youtube/channels/<CHANNEL>/channel_rules.json
```

Extract from `seo` section:
- **`niche`** → use as niche in Step 2 (skip guessing)
- **`default_tags`** → merge into generated tags in Step 6
- **`always_include_hashtags`** → prepend to hashtag list in Step 5
- **`hashtag_language`** → controls language mix strategy (e.g., `mixed_vi_en`)
- **`title_max_chars`** → enforce as hard limit in Step 3 (default: 65)
- **`default_category`** → use as YouTube category ID
- **`content_policy.ai_disclosure`** → insert verbatim in Zone 3 of description (before footer keywords). If present, this AI disclosure MUST appear in every generated description. This discloses that visuals are AI-generated while content is based on real events.

If no channel rules file exists, fall back to detecting niche from project content and using skill defaults.

## Step 2: Identify the NICHE

The niche determines which keywords, hashtags, and competitors to target.

**If channel rules loaded** and `seo.niche` exists, use it directly (e.g., `geopolitics-military-documentary`). Skip classification below.

**Otherwise**, based on project genre + content, classify into a niche:

| Content Type | Niche | Example Keywords |
|-------------|-------|-----------------|
| Military story | military-documentary | chiến tranh, hải quân, tàu chiến, quân sự |
| Romance | drama-romance | tình yêu, phim tình cảm, cảm động |
| Action/Heist | action-thriller | hành động, kịch tính, phim hành động |
| Historical | history-education | lịch sử, sự kiện, phim tài liệu |
| Fantasy | fantasy-animation | phép thuật, phiêu lưu, anime |
| Horror | horror-suspense | kinh dị, rùng rợn, bí ẩn |

## Step 3: Generate HOOK TITLE

The title is the #1 SEO factor. It must:

### Rules:
- **`seo.title_max_chars` from channel rules** (default: 65) — hard limit. YouTube truncates at ~70
- **Primary keyword in first 5 words** (YouTube weighs early words higher)
- **Power word** to trigger click: SHOCKING, SECRET, IMPOSSIBLE, ATTACK, DEADLY, LAST
- **Curiosity gap** — promises information viewer doesn't have yet
- **Number or specificity** — "2 Million Barrels" is stronger than "lots of oil"
- **Brackets/parentheses** boost CTR: [FULL MOVIE] (Eng Sub) {4K}
- **Language match** — title in target language, but include English keywords if audience searches bilingually

### Title formulas (pick best fit):

1. **Question hook**: `Tại Sao Iran Tấn Công Tàu Dầu Mỹ? | Chiến Dịch Hormuz Shield [Phim Tài Liệu]`
2. **Statement shock**: `Iran Tấn Công Tàu Dầu Mỹ — Hải Quân Mỹ Phản Ứng Thế Nào? [4K]`
3. **Number + stakes**: `2 Triệu Thùng Dầu vs 6 Tàu Tấn Công Iran | Eo Biển Tử Thần Hormuz`
4. **Challenge/Impossible**: `Vượt Qua Eo Biển Tử Thần — Nhiệm Vụ Bất Khả Thi Của Hải Quân Mỹ`
5. **Revelation**: `Bí Mật Chiến Dịch Hormuz Shield — Khi Iran Phong Tỏa Eo Biển Hormuz`

### Generate 3 title variants, ranked by SEO strength.

For each title, explain:
- Primary keyword and position
- Power word used
- Estimated search volume reasoning
- Character count

## Step 4: Generate DESCRIPTION

YouTube description has 3 zones with different SEO purposes:

### Zone 1: Above the fold (first 150 chars — visible without "Show more")

```
[HOOK SENTENCE — restate the title promise with more detail]
[CALL TO ACTION — subscribe/like]
```

This zone MUST contain:
- Primary keyword (same as title)
- Secondary keyword
- Emotional hook matching title

### Zone 2: Main body (150-2000 chars)

```
[STORY SUMMARY — 3-5 sentences, keyword-rich but natural]

[CHAPTER TIMESTAMPS — if video has clear sections]
00:00 — [Section name with keyword]
01:23 — [Section name with keyword]
...

[CONTEXT/FACTS — educational value, real-world context]
```

Rules:
- **Timestamps** boost SEO (YouTube indexes them as chapters)
- **Keyword density**: primary keyword 3-5 times, secondary 2-3 times
- **Natural language** — don't keyword-stuff, write for humans
- **Links to related videos** (placeholder for user to fill)

### Zone 3: Footer (2000-5000 chars)

```
[TAGS/KEYWORDS — natural sentence form]
[CREDITS]
[SOCIAL LINKS — placeholder]
[COPYRIGHT/DISCLAIMER]
```

### Full description template:

```
[Zone 1 — Hook + CTA]
{hook_sentence}

Like & Subscribe for more {niche} content!
Turn on notifications 🔔 to never miss a video.

[Zone 2 — Body]
{story_summary_3_5_sentences}

⏱️ Timestamps:
{auto_generated_timestamps_from_scenes}

📖 Background:
{real_world_context_2_3_sentences}

[Zone 3 — AI Disclosure + Footer]
{ai_disclosure_from_content_policy_if_present}

{keyword_rich_sentences}

#hashtag1 #hashtag2 #hashtag3 ... #hashtag15

© {year} {channel_name} — All rights reserved.
Generated with Flow Kit
```

## Step 5: Generate HASHTAGS

YouTube allows up to 15 hashtags (first 3 shown above title).

**If channel rules loaded**: prepend `seo.always_include_hashtags` (e.g., `#PhimTàiLiệu #QuânSự`) as the first hashtags in Tier 1. Use `seo.hashtag_language` to control language mix (`mixed_vi_en` = Vietnamese + English).

### Hashtag strategy (3 tiers):

**Tier 1 — High volume, broad (5 hashtags):**
Niche-level tags that get massive search. Place first 3 here (shown above title).
Start with `always_include_hashtags` from channel rules if available.
```
#PhimTàiLiệu #QuânSự #HảiQuân
```

**Tier 2 — Medium volume, specific (5 hashtags):**
Topic-specific tags matching this video's content.
```
#EoBiểnHormuz #IranVsMỹ #TàuChiến #ChiếnDịchHormuzShield #TàuDầu
```

**Tier 3 — Long-tail, niche (5 hashtags):**
Highly specific tags with less competition — easier to rank.
```
#USSArleighBurke #IRGC #StraitOfHormuz #NavalEscort #OilTanker
```

### Hashtag rules:
- NO spaces in hashtags: `#PhimTàiLiệu` not `#Phim Tài Liệu`
- Mix languages if audience is bilingual: Vietnamese + English
- First 3 hashtags = most important (shown above title)
- Don't use irrelevant trending tags (YouTube penalizes this)
- Include both Vietnamese and English versions of key terms

## Step 6: Generate KEYWORDS (Tags)

YouTube tags (different from hashtags) are hidden metadata. Max 500 characters total.

**If channel rules loaded**: merge `seo.default_tags` (e.g., `["phim tài liệu", "quân sự", "lịch sử", ...]`) into the generated tag list. Place channel default tags first, then add video-specific tags. Deduplicate.

### Keyword research approach:

**1. Primary keywords (exact match — highest priority):**
What would someone TYPE to find this video?
```
eo biển hormuz, iran tấn công tàu dầu, hải quân mỹ, chiến dịch hormuz shield
```

**2. Secondary keywords (broad match):**
Related topics that expand reach.
```
phim tài liệu quân sự, chiến tranh iran mỹ, tàu khu trục, strait of hormuz
```

**3. Long-tail keywords (low competition, high intent):**
Specific phrases people search for.
```
iran đóng cửa eo biển hormuz, uss arleigh burke, tàu dầu vlcc, irgc navy
```

**4. Trending/seasonal keywords:**
Current events that make this topic relevant.
```
iran 2024, trung đông căng thẳng, giá dầu tăng, chiến tranh trung đông
```

**5. English crossover keywords:**
For bilingual audiences and international reach.
```
strait of hormuz, iran navy, us navy, oil tanker escort, hormuz shield
```

### Keyword rules:
- Total max 500 characters
- Most important keywords first
- Mix exact match + broad match
- Include common misspellings if relevant
- Include both singular and plural forms
- Don't repeat keywords already in title/description

## Step 7: Generate TIMESTAMPS

Auto-generate from scene data:

```python
For each scene group (every 4-5 scenes = 1 chapter):
  timestamp = sum of previous scene durations
  chapter_name = summarize what happens in those scenes (keyword-rich)
```

Format:
```
00:00 Giới thiệu — Eo biển Hormuz tử thần
00:25 Lầu Năm Góc ra lệnh — Chiến dịch Hormuz Shield
01:05 Hải quân Mỹ xuất kích — USS Arleigh Burke
01:45 Iran triển khai IRGC — Căng thẳng leo thang
02:20 Đối đầu trên biển — Tàu cao tốc Iran tấn công
03:00 Phát hiện thủy lôi — Nguy hiểm chết người
03:35 Kết thúc — Vượt qua eo biển tử thần
```

## Step 8: Output all metadata

**CRITICAL: Print ALL metadata directly to terminal as plain text.**
The user needs to copy-paste from the terminal into YouTube Studio.
Do NOT just save to file — the user should NOT need to open any file.
Print each section with clear separators so they can copy individual parts.

```
═══════════════════════════════════════════
  YouTube SEO Metadata — {project_name}
═══════════════════════════════════════════

📌 TITLE OPTIONS (pick one):

  1. {title_v1} ({char_count} chars)
     Keywords: {primary}, {secondary}
     
  2. {title_v2} ({char_count} chars)
     Keywords: {primary}, {secondary}
     
  3. {title_v3} ({char_count} chars)
     Keywords: {primary}, {secondary}

📝 DESCRIPTION:
─────────────────
{full_description}

#️⃣ HASHTAGS (copy all):
─────────────────
{all_15_hashtags_on_one_line}

🏷️ TAGS (paste into YouTube Studio):
─────────────────
{comma_separated_tags_under_500_chars}

⏱️ TIMESTAMPS (paste into description):
─────────────────
{timestamp_list}

📊 SEO SCORE:
─────────────────
  Title keyword position: {1st/2nd/3rd word}
  Description keyword density: {X}%
  Hashtag coverage: {broad}% / {specific}% / {longtail}%
  Tag character usage: {N}/500
  Timestamp chapters: {N}
  Estimated niche: {niche_name}
```

## Step 9: Save backup (optional)

Also save a backup copy to project directory for reference:

```bash
# Get project output directory
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
cat > "${OUTDIR}/youtube_seo.md" << 'EOF'
{all_metadata_formatted}
EOF
```

The primary output is the terminal print in Step 8 — the file is just a backup.

## SEO Best Practices Reference

| Factor | Weight | Optimization |
|--------|--------|-------------|
| Title | 30% | Primary keyword in first 5 words, power word, 60-70 chars |
| Description | 25% | Keyword in first 150 chars, timestamps, 2000+ chars total |
| Tags | 15% | Mix exact + broad + long-tail, max 500 chars |
| Hashtags | 10% | First 3 = broad niche, next 12 = specific + long-tail |
| Timestamps | 10% | Chapter markers boost watch time + SEO |
| Thumbnail | 10% | (Handled by /fk:thumbnail) |

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---------|-------------|-----|
| Keyword stuffing in title | YouTube penalizes unnatural titles | Use 1-2 keywords naturally |
| Generic description | Missed SEO opportunity | Write 2000+ chars with keywords |
| No timestamps | Loses chapter indexing benefit | Add timestamps every 30-60s |
| English-only tags for VN audience | Misses local search | Mix Vietnamese + English |
| Too many broad hashtags | Competes with giant channels | Use 5 broad + 10 specific/long-tail |
| Title > 70 chars | Gets truncated on mobile | Keep under 65 chars ideally |
| No CTA in description | Lower engagement signals | Add subscribe/like CTA above fold |
