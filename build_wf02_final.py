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


def main() -> None:
    workflow = json.loads(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
    workflow["name"] = "WF02_final"
    workflow["meta"] = workflow.get("meta", {})
    workflow["meta"]["templateCredsSetupCompleted"] = True

    nodes = copy.deepcopy(workflow["nodes"])
    connections = copy.deepcopy(workflow["connections"])

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

    for node in (
        split_upload_tasks,
        route_youtube_upload,
        route_tiktok_upload,
        route_instagram_upload,
        upload_youtube,
        upload_tiktok,
        upload_instagram,
    ):
        upsert_node(nodes, node)

    connections["validate_upload_queue"] = {
        "main": [[
            {"node": "log_completion", "type": "main", "index": 0},
            {"node": "split_upload_tasks", "type": "main", "index": 0},
        ]]
    }
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
