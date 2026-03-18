#!/usr/bin/env python3
import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_WORKFLOW = ROOT / "WF01_final.json"
OUTPUT_WORKFLOW = ROOT / "WF02_final.json"
IMPORT_BUNDLE = ROOT / "WF02_final_import.json"


def make_node(name, node_type, position, parameters, type_version=1):
    return {
        "parameters": parameters,
        "type": node_type,
        "typeVersion": type_version,
        "position": position,
        "id": str(uuid.uuid4()),
        "name": name,
    }


def upsert_node(nodes, new_node):
    for index, node in enumerate(nodes):
        if node["name"] == new_node["name"]:
            nodes[index] = new_node
            return
    nodes.append(new_node)


def get_node(nodes, name):
    for node in nodes:
        if node["name"] == name:
            return node
    raise KeyError(f"Missing node: {name}")


def make_upload_log_node(name, position, platform):
    return make_node(
        name,
        "n8n-nodes-base.code",
        position,
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": f"""const fs = require('fs');

const logDir = '/files/logs/upload';
if (!fs.existsSync(logDir)) {{
  fs.mkdirSync(logDir, {{ recursive: true }});
}}

const date = $json.date || new Date().toISOString().slice(0, 10);
const logEntry = {{
  timestamp: new Date().toISOString(),
  platform: '{platform}',
  success: Boolean($json.success),
  upload_status: $json.upload_status || null,
  message: $json.message || $json.error || null,
  task_file: $json.task_file || null,
  queue_file: $json.queue_file || null,
  base_name: $json.base_name || null,
  video_file: $json.video_file || null
}};

fs.appendFileSync(`${{logDir}}/${{date}}_n8n_upload.log`, JSON.stringify(logEntry) + '\\n', 'utf8');
return $json;
""",
        },
        type_version=2,
    )


def main() -> None:
    workflow = json.loads(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
    workflow["name"] = "WF02_final"
    workflow["meta"] = workflow.get("meta", {})
    workflow["meta"]["templateCredsSetupCompleted"] = True

    nodes = copy.deepcopy(workflow["nodes"])
    connections = copy.deepcopy(workflow["connections"])

    assign_variants = get_node(nodes, "assign_variants")
    assign_variants["position"] = [2060, -180]
    assign_variants["parameters"]["jsCode"] = """const voiceMap = {
  female: { voice: 'en-US-JennyNeural', image_dir: 'female_host' },
  male: { voice: 'en-US-GuyNeural', image_dir: 'male_host' },
  psych: { voice: 'en-US-AriaNeural', image_dir: 'psych_host' }
};

const today = new Date().toISOString().slice(0, 10);

return $input.all().flatMap(item =>
  Object.entries(voiceMap).map(([variant, config]) => ({
    date: today,
    topic: item.json.topic,
    hook: item.json.hook,
    variant,
    voice: config.voice,
    voice_id: config.voice,
    image_dir: config.image_dir
  }))
);
"""

    script_generator = get_node(nodes, "script generator")
    script_generator["position"] = [2280, 0]
    script_generator["type"] = "n8n-nodes-base.httpRequest"
    script_generator["typeVersion"] = 4.4
    script_generator["parameters"] = {
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "openAiApi",
        "method": "POST",
        "url": "https://api.openai.com/v1/chat/completions",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": """={{ JSON.stringify((() => {
  const guides = {
    female: {
      tone: 'Write from a female perspective with an emotional, validating, highly relatable tone for American short-form relationship psychology content.',
      style: 'Make it feel intimate, self-aware, and deeply resonant without sounding cheesy.',
    },
    male: {
      tone: 'Write from a male perspective with a direct, blunt, reality-based tone for American short-form relationship psychology content.',
      style: 'Make it practical, sharp, and honest like someone explaining what really changes attraction.',
    },
    psych: {
      tone: 'Write as a psychology narrator with an analytical, insightful, pattern-driven tone for American short-form relationship psychology content.',
      style: 'Explain the emotional mechanism clearly and land on a strong psychological insight.',
    },
  };

  const variant = $json.variant || 'psych';
  const guide = guides[variant] || guides.psych;

  return {
    model: 'gpt-4.1-mini',
    messages: [
      {
        role: 'system',
        content: `You write viral 15-30 second scripts for U.S. TikTok, Reels, and YouTube Shorts about dating and relationship psychology. ${guide.tone} ${guide.style} Every script must have 3 parts: a scroll-stopping hook in line 1, a concise body in the middle, and a CTA in the final line. Output only plain spoken English. No labels, no bullets, no emojis, no hashtags, no quotation marks.`,
      },
      {
        role: 'user',
        content: `Topic: ${$json.topic}
Hook direction: ${$json.hook}
Variant: ${variant}

Write one script with these rules:
- 6 to 8 short lines total
- Line 1 must be a strong hook that stops the scroll in under 3 seconds
- Lines 2 to 6 should be the body and explain the psychology clearly
- Final line must be a CTA that invites comments or a follow
- Keep the language natural for American short-form content
- Use the hook direction as the first line or a sharper version of it
- No filler, no generic advice, no labels`,
      },
    ],
    temperature: 0.9,
    max_tokens: 280,
  };
})()) }}""",
        "options": {},
    }
    script_generator["credentials"] = {"openAiApi": {"name": "GPT-OAuth"}}

    clean_scripts = get_node(nodes, "clean_scripts")
    clean_scripts["position"] = [2500, 0]
    clean_scripts["parameters"]["jsCode"] = """const script = $json.choices?.[0]?.message?.content || '';
const item = $('assign_variants').item.json;

return {
  date: item.date,
  topic: item.topic,
  hook: item.hook,
  variant: item.variant,
  voice: item.voice,
  voice_id: item.voice_id,
  image_dir: item.image_dir,
  script: script.trim()
};
"""

    build_slug = get_node(nodes, "build_slug")
    build_slug["position"] = [2720, 0]
    build_slug["parameters"]["jsCode"] = """function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\\s-]/g, '')
    .trim()
    .replace(/\\s+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 60);
}

return {
  ...$json,
  slug: slugify($json.topic),
  hook_slug: slugify($json.hook)
};
"""

    save_script_json = get_node(nodes, "save_script_json")
    save_script_json["position"] = [2940, 0]
    save_script_json["parameters"]["jsCode"] = """const fs = require('fs');
const path = require('path');

const filename = `${$json.date}_${$json.slug}_${$json.hook_slug}_${$json.variant}.json`;
const filepath = `/files/scripts/${filename}`;
const dir = path.dirname(filepath);

if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

const content = JSON.stringify({
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  script: $json.script,
  slug: $json.slug,
  hook_slug: $json.hook_slug,
  variant: $json.variant,
  voice: $json.voice
}, null, 2);

fs.writeFileSync(filepath, content, 'utf8');

return {
  ...$json,
  script_file: filepath
};
"""

    prepare_variant_job = get_node(nodes, "prepare_variant_job")
    prepare_variant_job["position"] = [3160, 0]

    for node in nodes:
        if node["name"] == "log_completion":
            node["parameters"]["jsCode"] = """const fs = require('fs');

const logDir = '/files/logs/generation';
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

const logEntry = {
  timestamp: new Date().toISOString(),
  status: 'upload_tasks_built',
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  variant: $json.variant,
  voice: $json.voice,
  script_file: $json.script_file,
  audio_file: $json.audio_file,
  srt_file: $json.srt_file,
  ass_file: $json.ass_file,
  video_file: $json.video_file,
  queue_file: $json.queue_file,
  background_type: $json.background_type,
  subtitle_mode: $json.subtitle_mode,
  video_width: $json.video_width,
  video_height: $json.video_height,
  upload_task_count: $json.upload_task_count
};

const logFile = `${logDir}/${$json.date}_generation.log`;
fs.appendFileSync(logFile, JSON.stringify(logEntry) + '\\n', 'utf8');

return {
  success: true,
  status: 'upload_tasks_built',
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  variant: $json.variant,
  audio_file: $json.audio_file,
  srt_file: $json.srt_file,
  ass_file: $json.ass_file,
  video_file: $json.video_file,
  queue_file: $json.queue_file,
  background_type: $json.background_type,
  subtitle_mode: $json.subtitle_mode,
  video_width: $json.video_width,
  video_height: $json.video_height,
  upload_task_count: $json.upload_task_count,
  upload_tasks: $json.upload_tasks
};
"""
            break

    split_upload_tasks = make_node(
        "split_upload_tasks",
        "n8n-nodes-base.code",
        [4920, 220],
        {
            "mode": "runOnceForAllItems",
            "language": "javaScript",
            "jsCode": """return $input.all().flatMap(item => {
  const tasks = item.json.upload_tasks || [];
  return tasks.map(task => ({
    date: item.json.date,
    hook: item.json.hook,
    variant: item.json.variant,
    queue_file: item.json.queue_file,
    base_name: item.json.base_name,
    video_file: item.json.video_file,
    task_file: task.task_file,
    upload_platform: task.platform,
    upload_task_id: task.job_id
  }));
});
""",
        },
        type_version=2,
    )

    route_youtube_upload = make_node(
        "route_youtube_upload",
        "n8n-nodes-base.code",
        [5140, 60],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """if ($json.upload_platform !== 'youtube_shorts') {
  return [];
}

return $json;
""",
        },
        type_version=2,
    )

    route_tiktok_upload = make_node(
        "route_tiktok_upload",
        "n8n-nodes-base.code",
        [5140, 220],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """if ($json.upload_platform !== 'tiktok') {
  return [];
}

return $json;
""",
        },
        type_version=2,
    )

    route_instagram_upload = make_node(
        "route_instagram_upload",
        "n8n-nodes-base.code",
        [5140, 380],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """if ($json.upload_platform !== 'instagram_reels') {
  return [];
}

return $json;
""",
        },
        type_version=2,
    )

    upload_youtube = make_node(
        "upload_youtube",
        "n8n-nodes-base.httpRequest",
        [5360, 60],
        {
            "method": "POST",
            "url": "http://host.docker.internal:8010/upload/youtube",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={{ JSON.stringify({
  date: $json.date,
  base_name: $json.base_name,
  queue_file: $json.queue_file,
  task_file: $json.task_file,
  upload_platform: $json.upload_platform
}) }}""",
            "options": {},
        },
        type_version=4.4,
    )

    upload_tiktok = make_node(
        "upload_tiktok",
        "n8n-nodes-base.httpRequest",
        [5360, 220],
        {
            "method": "POST",
            "url": "http://host.docker.internal:8010/upload/tiktok",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={{ JSON.stringify({
  date: $json.date,
  base_name: $json.base_name,
  queue_file: $json.queue_file,
  task_file: $json.task_file,
  upload_platform: $json.upload_platform
}) }}""",
            "options": {},
        },
        type_version=4.4,
    )

    upload_instagram = make_node(
        "upload_instagram",
        "n8n-nodes-base.httpRequest",
        [5360, 380],
        {
            "method": "POST",
            "url": "http://host.docker.internal:8010/upload/instagram",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={{ JSON.stringify({
  date: $json.date,
  base_name: $json.base_name,
  queue_file: $json.queue_file,
  task_file: $json.task_file,
  upload_platform: $json.upload_platform
}) }}""",
            "options": {},
        },
        type_version=4.4,
    )

    log_youtube_upload = make_upload_log_node("log_youtube_upload", [5580, 60], "youtube_shorts")
    log_tiktok_upload = make_upload_log_node("log_tiktok_upload", [5580, 220], "tiktok")
    log_instagram_upload = make_upload_log_node("log_instagram_upload", [5580, 380], "instagram_reels")

    for node in (
        split_upload_tasks,
        route_youtube_upload,
        route_tiktok_upload,
        route_instagram_upload,
        upload_youtube,
        upload_tiktok,
        upload_instagram,
        log_youtube_upload,
        log_tiktok_upload,
        log_instagram_upload,
    ):
        upsert_node(nodes, node)

    connections["validate_upload_queue"] = {
        "main": [[
            {"node": "log_completion", "type": "main", "index": 0},
            {"node": "split_upload_tasks", "type": "main", "index": 0},
        ]]
    }
    connections["rename_hook"] = {"main": [[{"node": "assign_variants", "type": "main", "index": 0}]]}
    connections["assign_variants"] = {"main": [[{"node": "script generator", "type": "main", "index": 0}]]}
    connections["script generator"] = {"main": [[{"node": "clean_scripts", "type": "main", "index": 0}]]}
    connections["clean_scripts"] = {"main": [[{"node": "build_slug", "type": "main", "index": 0}]]}
    connections["build_slug"] = {"main": [[{"node": "save_script_json", "type": "main", "index": 0}]]}
    connections["save_script_json"] = {"main": [[{"node": "prepare_variant_job", "type": "main", "index": 0}]]}
    connections["split_upload_tasks"] = {
        "main": [[
            {"node": "route_youtube_upload", "type": "main", "index": 0},
            {"node": "route_tiktok_upload", "type": "main", "index": 0},
            {"node": "route_instagram_upload", "type": "main", "index": 0},
        ]]
    }
    connections["route_youtube_upload"] = {"main": [[{"node": "upload_youtube", "type": "main", "index": 0}]]}
    connections["route_tiktok_upload"] = {"main": [[{"node": "upload_tiktok", "type": "main", "index": 0}]]}
    connections["route_instagram_upload"] = {"main": [[{"node": "upload_instagram", "type": "main", "index": 0}]]}
    connections["upload_youtube"] = {"main": [[{"node": "log_youtube_upload", "type": "main", "index": 0}]]}
    connections["upload_tiktok"] = {"main": [[{"node": "log_tiktok_upload", "type": "main", "index": 0}]]}
    connections["upload_instagram"] = {"main": [[{"node": "log_instagram_upload", "type": "main", "index": 0}]]}

    workflow["nodes"] = nodes
    workflow["connections"] = connections
    OUTPUT_WORKFLOW.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    import_payload = [
        {
            "updatedAt": now,
            "createdAt": now,
            "id": uuid.uuid4().hex[:16],
            "name": workflow["name"],
            "description": None,
            "active": False,
            "isArchived": False,
            "nodes": workflow["nodes"],
            "connections": workflow["connections"],
            "settings": workflow.get("settings", {}),
            "staticData": None,
            "meta": workflow.get("meta"),
            "pinData": workflow.get("pinData", {}),
            "versionId": str(uuid.uuid4()),
            "activeVersionId": None,
            "versionCounter": 1,
            "triggerCount": 0,
            "tags": workflow.get("tags", []),
            "shared": [],
            "versionMetadata": {"name": None, "description": None},
        }
    ]
    IMPORT_BUNDLE.write_text(json.dumps(import_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
