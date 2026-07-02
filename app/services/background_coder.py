from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


CODE_AGENT_SYSTEM = """
You are SyMoNeuRaL Background Code Agent. You are not user-facing.
You do not ask questions. You do not debate requirements. You fully trust the writer/decision-maker plan.
Your job is only to create files, helper scripts, tests, and a compressed deliverable-ready workspace.
Return strict JSON only with this schema:
{
  "files": [{"path": "relative/path.ext", "content": "file contents"}],
  "test_commands": ["safe command to run inside the job workspace"],
  "notes": "short implementation notes for the writer agent"
}
Never use absolute paths in file paths. Never write outside the job workspace.
""".strip()


@dataclass
class CoderJob:
    id: str
    status: str = "queued"
    prompt: str = ""
    writer_response: str = ""
    workspace: str = ""
    artifact: str | None = None
    notes: str = ""
    logs: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "prompt": self.prompt,
            "workspace": self.workspace,
            "artifact": self.artifact,
            "notes": self.notes,
            "logs": self.logs[-80:],
            "files": self.files,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }


class BackgroundCoderManager:
    def __init__(self, default_work_root: str = "/mnt/data/symoneural_coder_jobs"):
        self.work_root = Path(os.getenv("SYMON_CODER_WORKDIR", default_work_root)).resolve()
        self.artifact_root = self.work_root / "artifacts"
        self.jobs: dict[str, CoderJob] = {}
        self.lock = threading.Lock()
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def submit(self, *, prompt: str, writer_response: str, code_endpoint: str, model_label: str = "qwen-code") -> CoderJob:
        job = CoderJob(
            id=str(uuid.uuid4()),
            prompt=prompt.strip(),
            writer_response=writer_response.strip(),
        )
        job.workspace = str((self.work_root / job.id / "workspace").resolve())
        with self.lock:
            self.jobs[job.id] = job
        thread = threading.Thread(target=self._run_job, args=(job.id, code_endpoint, model_label), daemon=True)
        thread.start()
        return job

    def list(self) -> list[dict[str, Any]]:
        with self.lock:
            return [job.as_dict() for job in sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)]

    def get(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(job_id)
            return self.jobs[job_id].as_dict()

    def artifact_path(self, job_id: str) -> Path:
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(job_id)
            artifact = self.jobs[job_id].artifact
        if not artifact:
            raise FileNotFoundError("artifact not ready")
        path = Path(artifact)
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    def _update(self, job_id: str, **kwargs: Any) -> CoderJob:
        with self.lock:
            job = self.jobs[job_id]
            for key, value in kwargs.items():
                setattr(job, key, value)
            job.updated_at = time.time()
            return job

    def _log(self, job_id: str, message: str) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.logs.append(f"[{time.strftime('%H:%M:%S')}] {message}")
            job.updated_at = time.time()

    def _run_job(self, job_id: str, code_endpoint: str, model_label: str) -> None:
        job = self._update(job_id, status="running")
        workspace = Path(job.workspace)
        try:
            workspace.mkdir(parents=True, exist_ok=True)
            self._log(job_id, f"workspace ready: {workspace}")

            (workspace / "WRITER_PLAN.md").write_text(job.writer_response or "", encoding="utf-8")
            (workspace / "USER_REQUEST.md").write_text(job.prompt or "", encoding="utf-8")

            spec = self._build_code_prompt(job.prompt, job.writer_response)
            self._log(job_id, f"requesting code package from {model_label}")
            raw = self._call_code_model(code_endpoint, spec)
            (workspace / "CODE_AGENT_RAW_RESPONSE.md").write_text(raw, encoding="utf-8")

            manifest = self._parse_manifest(raw)
            if manifest is None:
                self._log(job_id, "code model did not return valid JSON manifest; saving raw response only")
                manifest = {"files": [{"path": "README_FROM_CODE_AGENT.md", "content": raw}], "test_commands": [], "notes": "Raw response saved because JSON manifest parsing failed."}

            files = self._write_files(workspace, manifest.get("files", []), job_id)
            self._update(job_id, files=files, notes=str(manifest.get("notes", "")))
            self._run_tests(workspace, manifest.get("test_commands", []), job_id)

            artifact_base = self.artifact_root / f"{job_id}_code_package"
            archive = shutil.make_archive(str(artifact_base), "gztar", root_dir=workspace)
            self._log(job_id, f"artifact created: {archive}")
            self._update(job_id, status="done", artifact=archive)
        except Exception as exc:
            self._log(job_id, f"failed: {exc!r}")
            self._update(job_id, status="failed", error=repr(exc))

    def _build_code_prompt(self, prompt: str, writer_response: str) -> str:
        return f"""
USER REQUEST:
{prompt}

WRITER / DECISION-MAKER PLAN:
{writer_response}

Build the requested code/package now. Do not ask questions. Do not change requirements.
Create a complete compressed-deliverable workspace using relative file paths only.
Return strict JSON only with files, test_commands, and notes.
""".strip()

    def _call_code_model(self, endpoint: str, prompt: str) -> str:
        payload = {
            "messages": [
                {"role": "system", "content": CODE_AGENT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "temperature": 0.15,
            "top_p": 0.95,
            "max_tokens": int(os.getenv("SYMON_CODER_MAX_TOKENS", "2200")),
        }
        try:
            with httpx.Client(timeout=240.0) as client:
                resp = client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content")
            if text:
                return text
            return json.dumps(data, indent=2)
        except Exception as exc:
            return json.dumps({
                "files": [
                    {"path": "README.md", "content": f"# Background Code Package\n\nThe code model endpoint failed: {exc!r}\n\n## User Request\n\n{prompt}\n"}
                ],
                "test_commands": [],
                "notes": "Fallback package created because the code model request failed.",
            })

    def _parse_manifest(self, raw: str) -> dict[str, Any] | None:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.I).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        for candidate in [cleaned, self._first_json_object(cleaned)]:
            if not candidate:
                continue
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return None

    def _first_json_object(self, text: str) -> str | None:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end + 1]
        return None

    def _write_files(self, workspace: Path, files: Any, job_id: str) -> list[str]:
        written: list[str] = []
        if not isinstance(files, list):
            return written
        for item in files:
            if not isinstance(item, dict):
                continue
            rel = str(item.get("path", "")).strip().lstrip("/")
            content = str(item.get("content", ""))
            if not rel or ".." in Path(rel).parts:
                self._log(job_id, f"skipped unsafe path: {rel!r}")
                continue
            dest = (workspace / rel).resolve()
            if not str(dest).startswith(str(workspace.resolve())):
                self._log(job_id, f"skipped escaping path: {rel!r}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written.append(rel)
        return written

    def _run_tests(self, workspace: Path, commands: Any, job_id: str) -> None:
        if str(os.getenv("SYMON_CODER_RUN_TESTS", "true")).lower() not in {"1", "true", "yes", "on"}:
            self._log(job_id, "test execution disabled by SYMON_CODER_RUN_TESTS")
            return
        if not isinstance(commands, list):
            return
        for command in commands[:8]:
            cmd = str(command).strip()
            if not cmd:
                continue
            self._log(job_id, f"test: {cmd}")
            try:
                result = subprocess.run(cmd, cwd=workspace, shell=True, text=True, capture_output=True, timeout=int(os.getenv("SYMON_CODER_TEST_TIMEOUT", "90")))
                log = f"$ {cmd}\nexit={result.returncode}\nSTDOUT:\n{result.stdout[-4000:]}\nSTDERR:\n{result.stderr[-4000:]}"
                (workspace / "TEST_LOG.txt").open("a", encoding="utf-8").write(log + "\n\n")
                self._log(job_id, f"test exit {result.returncode}: {cmd}")
            except Exception as exc:
                self._log(job_id, f"test failed to run {cmd!r}: {exc!r}")


BACKGROUND_CODER = BackgroundCoderManager()
