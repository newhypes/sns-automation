# SNS Automation Project - Phase 2 Improvements

## Current Status (as of 2026-03-15)
- ✅ topic → hook → script (MLX working)
- ✅ edge-tts audio generation
- ✅ SRT subtitle generation  
- ✅ ffmpeg video rendering
- ✅ publish_queue created (138 items)
- ⏳ TikTok / YouTube / Instagram upload (credentials needed)

## Key Paths
- n8n Docker: `/Users/bigmac/.openclaw/workspace/content_factory/n8n/docker-compose.yml`
- Content folder: `/Users/bigmac/.openclaw/workspace/content_factory/`
- Workflow files: `/Users/bigmac/openclaw/workspace/sns_auto/`
- Current workflow: `/Users/bigmac/openclaw/workspace/sns_auto/WF01_final.json`
- n8n volume mount: `/files` → `/Users/bigmac/.openclaw/workspace/content_factory/`
- pipeline_service.py: check location and use it

## Infrastructure
- n8n container: `content-factory-n8n` (port 5678)
- MLX server: `localhost:8000` (Qwen2.5-7B-Instruct-4bit)
- edge-tts: installed
- n8n env: `NODE_FUNCTION_ALLOW_BUILTIN=*`, `NODE_FUNCTION_ALLOW_EXTERNAL=*`

## Content Strategy
- 3 accounts: female podcast / male podcast / psychology narrator
- 1 topic → 3 variant videos (female, male, psych)
- Target: 5 topics/day = 15 videos/day = 45 uploads/day
- File naming: `YYYY-MM-DD_topic-slug_variant.ext`

## Voice Mapping (edge-tts)
- female: `en-US-JennyNeural`
- male: `en-US-GuyNeural`
- psych: `en-US-AriaNeural`

## Problems to Fix

### 1. Background Video/Image (HIGHEST PRIORITY)
Current videos are plain single color background. Need to add:
- Use background video or image per variant
- female_host: warm, lifestyle background
- male_host: clean, modern background
- psych_host: dark, mysterious background
- Images stored in:
  - `/files/images/female_host/`
  - `/files/images/male_host/`
  - `/files/images/psych_host/`
- If no images exist, generate gradient backgrounds using ffmpeg
- ffmpeg render should overlay background behind subtitles

### 2. Subtitle Style Improvement
- Large bold white text with black outline
- Bottom center position
- One sentence at a time
- Font: Arial bold
- Size: large enough for mobile viewing
- Use ffmpeg ASS/SSA subtitle style

### 3. Video Format
- Vertical: 1080x1920 (9:16 for TikTok/Reels/Shorts)
- Duration: match audio length exactly
- Background fills entire frame

### 4. SNS Upload Setup
Set up upload credential scaffolding:
- YouTube Shorts: YouTube Data API v3, OAuth2
  - Store: `~/.openclaw/credentials/youtube_client_secret.json`
- TikTok: TikTok Content Posting API
  - Store: `~/.openclaw/credentials/tiktok_credentials.json`
- Instagram Reels: Instagram Graph API
  - Store: `~/.openclaw/credentials/instagram_credentials.json`

Create upload scripts:
- `pipeline/upload_youtube.sh`
- `pipeline/upload_tiktok.sh`
- `pipeline/upload_instagram.sh`

### 5. n8n Workflow Update
Update workflow to include:
- Improved ffmpeg render (background + styled subtitles)
- Upload nodes per platform after render
- Failed items → `/files/queue/failed/`
- Uploaded items → `/files/queue/uploaded/`

## Tasks (do all in order, fix errors automatically)
1. Fix video background - gradient or image per variant via ffmpeg
2. Fix subtitle style - large bold white, bottom center, mobile-friendly
3. Verify 1080x1920 vertical format
4. Test render one sample and open for visual check
5. Set up YouTube/TikTok/Instagram upload scripts
6. Update n8n workflow with all improvements
7. Save as `/Users/bigmac/openclaw/workspace/sns_auto/WF02_final.json`
8. Run full pipeline and confirm all videos render correctly

## Rules
- Run all terminal commands directly
- Fix errors automatically without asking
- If credentials missing, create placeholder scripts with clear instructions
- Show summary at the end: completed vs needs manual credential input
