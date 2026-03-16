#!/usr/bin/env python3
import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE_WORKFLOW = ROOT / "WF01_content_factory_phase1.json"
OUTPUT_WORKFLOW = ROOT / "WF01_final.json"
IMPORT_BUNDLE = ROOT / "WF01_final_import.json"


def make_node(name, node_type, position, parameters, type_version=1):
    return {
        "parameters": parameters,
        "type": node_type,
        "typeVersion": type_version,
        "position": position,
        "id": str(uuid.uuid4()),
        "name": name,
    }


def replace_node(nodes, name, new_node):
    for index, node in enumerate(nodes):
        if node["name"] == name:
            nodes[index] = new_node
            return
    raise KeyError(name)


def main() -> None:
    workflow = json.loads(BASE_WORKFLOW.read_text(encoding="utf-8"))
    workflow["name"] = "WF01_final"
    workflow["meta"] = workflow.get("meta", {})
    workflow["meta"]["templateCredsSetupCompleted"] = True

    nodes = copy.deepcopy(workflow["nodes"])
    connections = copy.deepcopy(workflow["connections"])

    assign_variants = next(node for node in nodes if node["name"] == "assign_variants")
    assign_variants["parameters"]["mode"] = "runOnceForAllItems"
    assign_variants["parameters"]["jsCode"] = """const voiceMap = {
  female: { voice: 'en-US-JennyNeural', image_dir: 'female_host' },
  male: { voice: 'en-US-GuyNeural', image_dir: 'male_host' },
  psych: { voice: 'en-US-AriaNeural', image_dir: 'psych_host' }
};

return $input.all().flatMap(item =>
  Object.entries(voiceMap).map(([variant, config]) => ({
    date: item.json.date,
    topic: item.json.topic,
    hook: item.json.hook,
    script: item.json.script,
    slug: item.json.slug,
    hook_slug: item.json.hook_slug,
    script_file: item.json.script_file,
    variant,
    voice: config.voice,
    voice_id: config.voice,
    image_dir: config.image_dir
  }))
);
"""

    prepare_variant_job = make_node(
        "prepare_variant_job",
        "n8n-nodes-base.code",
        [3160, 0],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """const fs = require('fs');
const path = require('path');

const baseName = `${$json.date}_${$json.slug}_${$json.hook_slug}_${$json.variant}`;
const queueDir = '/files/queue/pending';
const queueFile = `${queueDir}/${baseName}.json`;

if (!fs.existsSync(queueDir)) {
  fs.mkdirSync(queueDir, { recursive: true });
}

const payload = {
  job_id: baseName,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  status: 'pending',
  retry_count: 0,
  last_error: null,
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  slug: $json.slug,
  hook_slug: $json.hook_slug,
  variant: $json.variant,
  voice: $json.voice,
  script_file: $json.script_file
};

fs.writeFileSync(queueFile, JSON.stringify(payload, null, 2), 'utf8');

return {
  ...$json,
  base_name: baseName,
  queue_file: queueFile
};
""",
        },
        type_version=2,
    )

    edge_tts_generate = make_node(
        "edge_tts_generate",
        "n8n-nodes-base.httpRequest",
        [3380, 0],
        {
            "method": "POST",
            "url": "http://host.docker.internal:8010/tts",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={{ JSON.stringify({
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  script: $json.script,
  slug: $json.slug,
  hook_slug: $json.hook_slug,
  variant: $json.variant,
  voice: $json.voice,
  script_file: $json.script_file,
  base_name: $json.base_name,
  queue_file: $json.queue_file
}) }}""",
            "options": {},
        },
        type_version=4.4,
    )

    save_audio = make_node(
        "save_audio",
        "n8n-nodes-base.code",
        [3600, 0],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """if (!$json.success || !$json.audio_file) {
  return [];
}

return {
  ...$json,
  stage: 'audio_ready'
};
""",
        },
        type_version=2,
    )

    generate_srt = make_node(
        "generate_srt",
        "n8n-nodes-base.code",
        [3820, 0],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """if (!$json.srt_file) {
  return [];
}

return {
  ...$json,
  stage: 'subtitles_ready'
};
""",
        },
        type_version=2,
    )

    render_video = make_node(
        "render_video",
        "n8n-nodes-base.httpRequest",
        [4040, 0],
        {
            "method": "POST",
            "url": "http://host.docker.internal:8010/render",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={{ JSON.stringify({
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  script: $json.script,
  slug: $json.slug,
  hook_slug: $json.hook_slug,
  variant: $json.variant,
  voice: $json.voice,
  base_name: $json.base_name,
  queue_file: $json.queue_file,
  audio_file: $json.audio_file,
  srt_file: $json.srt_file,
  duration_seconds: $json.duration_seconds
}) }}""",
            "options": {},
        },
        type_version=4.4,
    )

    validate_render = make_node(
        "validate_render",
        "n8n-nodes-base.code",
        [4260, 0],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """if (!$json.success || !$json.video_file) {
  return [];
}

return {
  ...$json,
  stage: 'video_ready'
};
""",
        },
        type_version=2,
    )

    build_upload_queue = make_node(
        "build_upload_queue",
        "n8n-nodes-base.httpRequest",
        [4480, 0],
        {
            "method": "POST",
            "url": "http://host.docker.internal:8010/enqueue_upload",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={{ JSON.stringify({
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  script: $json.script,
  slug: $json.slug,
  hook_slug: $json.hook_slug,
  variant: $json.variant,
  voice: $json.voice,
  base_name: $json.base_name,
  queue_file: $json.queue_file,
  video_file: $json.video_file
}) }}""",
            "options": {},
        },
        type_version=4.4,
    )

    validate_upload_queue = make_node(
        "validate_upload_queue",
        "n8n-nodes-base.code",
        [4700, 0],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """if (!$json.success || !$json.upload_tasks || !$json.upload_tasks.length) {
  return [];
}

return {
  ...$json,
  upload_task_count: $json.upload_tasks.length,
  stage: 'ready_to_upload'
};
""",
        },
        type_version=2,
    )

    log_completion = make_node(
        "log_completion",
        "n8n-nodes-base.code",
        [4920, 0],
        {
            "mode": "runOnceForEachItem",
            "language": "javaScript",
            "jsCode": """const fs = require('fs');

const logDir = '/files/logs/generation';
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

const logEntry = {
  timestamp: new Date().toISOString(),
  status: 'ready_to_upload',
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  variant: $json.variant,
  voice: $json.voice,
  script_file: $json.script_file,
  audio_file: $json.audio_file,
  srt_file: $json.srt_file,
  video_file: $json.video_file,
  queue_file: $json.queue_file,
  upload_task_count: $json.upload_task_count
};

const logFile = `${logDir}/${$json.date}_generation.log`;
fs.appendFileSync(logFile, JSON.stringify(logEntry) + '\\n', 'utf8');

return {
  success: true,
  status: 'ready_to_upload',
  date: $json.date,
  topic: $json.topic,
  hook: $json.hook,
  variant: $json.variant,
  audio_file: $json.audio_file,
  srt_file: $json.srt_file,
  video_file: $json.video_file,
  queue_file: $json.queue_file,
  upload_task_count: $json.upload_task_count
};
""",
        },
        type_version=2,
    )

    replace_node(nodes, "elevenlabs_tts", prepare_variant_job)
    replace_node(nodes, "save_audio", edge_tts_generate)
    replace_node(nodes, "generate_srt", save_audio)
    replace_node(nodes, "log_completion", generate_srt)

    nodes.extend([render_video, validate_render, build_upload_queue, validate_upload_queue, log_completion])

    connections["assign_variants"] = {"main": [[{"node": "prepare_variant_job", "type": "main", "index": 0}]]}
    connections["prepare_variant_job"] = {"main": [[{"node": "edge_tts_generate", "type": "main", "index": 0}]]}
    connections["edge_tts_generate"] = {"main": [[{"node": "save_audio", "type": "main", "index": 0}]]}
    connections["save_audio"] = {"main": [[{"node": "generate_srt", "type": "main", "index": 0}]]}
    connections["generate_srt"] = {"main": [[{"node": "render_video", "type": "main", "index": 0}]]}
    connections["render_video"] = {"main": [[{"node": "validate_render", "type": "main", "index": 0}]]}
    connections["validate_render"] = {"main": [[{"node": "build_upload_queue", "type": "main", "index": 0}]]}
    connections["build_upload_queue"] = {"main": [[{"node": "validate_upload_queue", "type": "main", "index": 0}]]}
    connections["validate_upload_queue"] = {"main": [[{"node": "log_completion", "type": "main", "index": 0}]]}
    connections.pop("elevenlabs_tts", None)

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
            "versionMetadata": {
                "name": None,
                "description": None,
            },
        }
    ]
    IMPORT_BUNDLE.write_text(json.dumps(import_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
