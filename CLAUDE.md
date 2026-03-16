# SNS Automation Project - Codex Context

## Project Goal
Build a fully automated AI short-form content pipeline that generates and publishes videos to TikTok, YouTube Shorts, and Instagram Reels.

## Key Paths (read/write as needed)
- n8n Docker: `/Users/bigmac/.openclaw/workspace/content_factory/n8n/docker-compose.yml`
- Content folder: `/Users/bigmac/.openclaw/workspace/content_factory/`
- Workflow files: `/Users/bigmac/openclaw/workspace/sns_auto/`
- n8n volume mount: `/files` → `/Users/bigmac/.openclaw/workspace/content_factory/`

## Current Infrastructure
- n8n container: `content-factory-n8n` (port 5678)
- MLX server: `localhost:8000` (Qwen2.5-7B-Instruct-4bit)
- edge-tts: installed
- n8n env: `NODE_FUNCTION_ALLOW_BUILTIN=*`, `NODE_FUNCTION_ALLOW_EXTERNAL=*`, `N8N_RESTRICT_FILE_ACCESS_TO=/`

## Content Strategy
- 3 accounts: female podcast / male podcast / psychology narrator
- 1 topic → 3 variant videos (female, male, psych)
- Target: 5 topics/day = 15 videos/day = 45 uploads/day (TikTok + YouTube + Instagram)
- File naming: `YYYY-MM-DD_topic-slug_variant.ext`

## Voice Mapping (edge-tts)
- female: `en-US-JennyNeural`
- male: `en-US-GuyNeural`
- psych: `en-US-AriaNeural`

## Folder Structure
```
content_factory/
├── scripts/     # JSON script files
├── audio/       # MP3 files
├── subs/        # SRT subtitle files
├── videos/      # MP4 rendered videos
├── images/
│   ├── female_host/
│   ├── male_host/
│   └── psych_host/
├── queue/
│   ├── pending/
│   ├── rendering/
│   ├── ready_to_upload/
│   ├── uploaded/
│   └── failed/
└── logs/
    └── generation/
```

## Full Pipeline to Complete
1. ✅ topic → hook → script (MLX, working)
2. ❌ edge-tts audio generation (female/male/psych)
3. ❌ SRT subtitle generation
4. ❌ ffmpeg video rendering (image + audio + subtitles)
5. ❌ TikTok / YouTube Shorts / Instagram Reels upload
6. ❌ failure logging and retry

## Current Workflow File
`/Users/bigmac/openclaw/workspace/sns_auto/WF01_content_factory_phase1.json`
- elevenlabs_tts node needs to be replaced with edge-tts
- save_audio, generate_srt, log_completion nodes need to match edge-tts output

## Reference Files
- Master plan: `/Users/bigmac/openclaw/workspace/sns_auto/SNS_automation_masterplan_n8n_revised_260307.txt`
- Phase 1 guide: `/Users/bigmac/openclaw/workspace/sns_auto/SNS_automation_phase1_workflow_n8n_mlx_260307.txt`

## Task
Complete the entire pipeline end-to-end. Fix all errors automatically. Save final workflow as:
`/Users/bigmac/openclaw/workspace/sns_auto/WF01_final.json`
Then import to n8n and verify audio + srt + video files are generated successfully.
