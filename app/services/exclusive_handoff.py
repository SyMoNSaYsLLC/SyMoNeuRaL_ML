from __future__ import annotations

import base64
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

from app.services.llama_cpp import build_chat_payload
from app.services.sd_cpp import image_payload_attempts
from app.services.symon_adaptive_profiles import apply_image_profile, apply_runtime_env, choose_profile, profile_log


MANAGER_SYSTEM = """
You are SyMoNeuRaL Writer Manager. You are the only user-facing text model.
Classify the user's request and clean it for the correct worker.
Return strict JSON only:
{
  "route": "writer" | "code" | "image",
  "clean_request": "clear worker-ready request",
  "user_message": "short user-facing message",
  "quality_bar": "what must be true before sending to the user"
}

Rules:
- route "writer" for normal questions, explanations, writing, rewriting, summaries, decisions, planning, and easy prompts.
- route "code" for software, repo, API, frontend/backend, scripts, patches, tests, builds, packaging, BitBake/OpenEmbedded, Docker, systemd, or compressed deliverables.
- route "image" for pictures, photos, art, rendering, stable diffusion, visual generation.
- The code and image workers do not ask questions. They trust your clean_request.
""".strip()

WRITER_FINAL_SYSTEM = """
You are SyMoNeuRaL Writer Manager. Write the final answer for the user.
Be direct. If an artifact or image is ready, explain what was produced and how to use it.
""".strip()

ASSESS_SYSTEM = """
You are SyMoNeuRaL Writer Manager and quality gate.
Assess whether the worker result satisfies the user request.
Return strict JSON only:
{"approved": true|false, "revision_request": "what the worker must fix", "user_status": "short status for user"}
Approve if the artifact/image exists and appears structurally complete. Reject only for clear failure.
""".strip()

CODE_AGENT_SYSTEM = """
You are SyMoNeuRaL Background Code Agent. You are not user-facing.
You do not ask questions. You do not debate requirements.
You fully trust the Writer Manager's clean request and build package instructions.
Return strict JSON only:
{
  "files": [{"path": "relative/path.ext", "content": "file contents"}],
  "test_commands": ["safe command to run inside the workspace"],
  "notes": "short implementation notes for the writer manager"
}
Never use absolute file paths. Never write outside the job workspace.
""".strip()


@dataclass
class HandoffJob:
    id: str
    kind: str = "unknown"
    status: str = "queued"
    user_prompt: str = ""
    clean_request: str = ""
    user_message: str = ""
    quality_bar: str = ""
    result_text: str = ""
    artifact: str | None = None
    image_path: str | None = None
    image_b64: str | None = None
    attempts: list[dict[str, Any]] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    workspace: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str | None = None

    def as_dict(self, include_image: bool = False) -> dict[str, Any]:
        data = {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "user_prompt": self.user_prompt,
            "clean_request": self.clean_request,
            "user_message": self.user_message,
            "quality_bar": self.quality_bar,
            "result_text": self.result_text,
            "artifact": self.artifact,
            "image_path": self.image_path,
            "attempts": self.attempts[-8:],
            "logs": self.logs[-120:],
            "workspace": self.workspace,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }
        if include_image and self.image_b64:
            data["image_b64"] = self.image_b64
        return data


class ExclusiveHandoffManager:
    def __init__(self, work_root: str = "data/symoneural_handoff_jobs"):
        self.work_root = Path(os.getenv("SYMON_HANDOFF_WORKDIR", work_root)).resolve()
        self.artifact_root = self.work_root / "artifacts"
        self.image_root = self.work_root / "images"
        self.jobs: dict[str, HandoffJob] = {}
        self.lock = threading.RLock()
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.image_root.mkdir(parents=True, exist_ok=True)

    def submit(self, *, prompt: str, app: Any, requested_route: str | None = None, image_options: dict[str, Any] | None = None) -> HandoffJob:
        job = HandoffJob(id=str(uuid.uuid4()), user_prompt=prompt.strip())
        job.workspace = str((self.work_root / job.id / "workspace").resolve())
        with self.lock:
            self.jobs[job.id] = job
        thread = threading.Thread(target=self._run, args=(job.id, app, requested_route, image_options or {}), daemon=True)
        thread.start()
        return job

    def list(self) -> list[dict[str, Any]]:
        with self.lock:
            return [j.as_dict() for j in sorted(self.jobs.values(), key=lambda x: x.created_at, reverse=True)]

    def get(self, job_id: str, include_image: bool = False) -> dict[str, Any]:
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(job_id)
            return self.jobs[job_id].as_dict(include_image=include_image)

    def artifact_path(self, job_id: str) -> Path:
        with self.lock:
            job = self.jobs[job_id]
            path = job.artifact or job.image_path
        if not path:
            raise FileNotFoundError("artifact not ready")
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        return p

    def _update(self, job_id: str, **kwargs: Any) -> HandoffJob:
        with self.lock:
            job = self.jobs[job_id]
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.updated_at = time.time()
            return job

    def _log(self, job_id: str, msg: str) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
            job.updated_at = time.time()

    def _run(self, job_id: str, app: Any, requested_route: str | None, image_options: dict[str, Any]) -> None:
        settings = app.state.engine_manager
        engines = app.state.engine_manager.engines
        try:
            job = self._update(job_id, status="manager-routing")
            workspace = Path(job.workspace)
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "USER_PROMPT.md").write_text(job.user_prompt, encoding="utf-8")

            # Keep only writer up while deciding. This is the low-VRAM idle state.
            manager_profile = apply_runtime_env(choose_profile("writer", job.user_prompt, job.user_prompt, image_options, phase="manager"))
            self._log(job_id, profile_log(manager_profile))
            writer_endpoint = engines["writer"]["endpoint"]
            self._switch_and_wait(settings, writer_endpoint, "writer")

            route_info = self._manager_route(writer_endpoint, job.user_prompt, requested_route)
            route = route_info.get("route", requested_route or "writer")
            if route not in {"writer", "code", "image"}:
                route = self._fallback_route(job.user_prompt)
            clean = route_info.get("clean_request") or job.user_prompt
            user_message = route_info.get("user_message") or ""
            quality_bar = route_info.get("quality_bar") or "Result satisfies the user request."

            runtime_profile = apply_runtime_env(choose_profile(route, job.user_prompt, clean, image_options))
            self._log(job_id, profile_log(runtime_profile))
            route_info["runtime_profile"] = {
                "role": runtime_profile.role,
                "name": runtime_profile.name,
                "reason": runtime_profile.reason,
                "env": runtime_profile.env,
                "options": runtime_profile.options,
            }
            self._update(job_id, kind=route, clean_request=clean, user_message=user_message, quality_bar=quality_bar)
            (workspace / "MANAGER_ROUTE.json").write_text(json.dumps(route_info, indent=2), encoding="utf-8")

            if route == "writer":
                self._update(job_id, status="writer-answering")
                answer = self._call_writer(
                    writer_endpoint,
                    system=WRITER_FINAL_SYSTEM,
                    prompt=f"USER REQUEST:\n{job.user_prompt}\n\nGive the user the best direct answer.",
                    max_tokens=int(os.getenv("SYMON_WRITER_MAX_TOKENS", "1200")),
                )
                self._update(job_id, status="done", result_text=answer)
                return

            self._update(
                job_id,
                status="handoff-running",
                result_text="This task requires a lot of processing power, but please wait — your code/image is coming soon.",
            )

            max_rounds = int(os.getenv("SYMON_HANDOFF_MAX_ROUNDS", "2"))
            revision = ""
            for round_idx in range(1, max_rounds + 1):
                self._log(job_id, f"handoff round {round_idx} route={route}")

                if route == "code":
                    runtime_profile = apply_runtime_env(choose_profile("code", job.user_prompt, clean, image_options))
                    self._log(job_id, profile_log(runtime_profile))
                    self._switch_and_wait(settings, engines["code"]["endpoint"], "code")
                    result = self._run_code_worker(job_id, engines["code"]["endpoint"], clean, quality_bar, revision)
                else:
                    profiled_image_options = apply_image_profile(clean, image_options)
                    self._log(job_id, f"[profile] image/{profiled_image_options.get('_profile')}: {profiled_image_options.get('width')}x{profiled_image_options.get('height')} steps={profiled_image_options.get('steps')} reason={profiled_image_options.get('_profile_reason')}")
                    self._switch_and_wait(settings, engines["image"]["endpoint"], "image")
                    result = self._run_image_worker(job_id, engines["image"]["endpoint"], {**profiled_image_options, "prompt": clean}, revision)

                # Bring writer back as quality gate and wait until llama-server finishes model warmup.
                manager_profile = apply_runtime_env(choose_profile("writer", job.user_prompt, clean, image_options, phase="manager"))
                self._log(job_id, profile_log(manager_profile))
                self._switch_and_wait(settings, writer_endpoint, "writer")
                approved, revision, final_msg = self._assess(writer_endpoint, job.user_prompt, clean, route, result, quality_bar)
                self._log(job_id, f"writer assessment approved={approved}: {final_msg[:180]}")
                self._update(job_id, attempts=[*self.jobs[job_id].attempts, {"round": round_idx, "approved": approved, "revision": revision, "message": final_msg}])

                if approved:
                    self._update(job_id, status="done", result_text=final_msg or self._default_done_message(route))
                    return

                self._update(
                    job_id,
                    status="revising",
                    result_text="This task requires a lot of processing power, but please wait — your code/image is coming soon.",
                )

            self._update(job_id, status="needs-review", result_text=final_msg or "The worker produced an output, but the writer manager marked it for review.")
        except Exception as exc:
            self._log(job_id, f"failed: {exc!r}")
            try:
                settings.restart_resident_sync()
            except Exception:
                pass
            self._update(job_id, status="failed", error=repr(exc), result_text=f"Task failed: {exc!r}")


    def _switch_and_wait(self, settings: Any, endpoint: str, engine_name: str, timeout: float | None = None) -> None:
        # Switch to an exclusive engine and wait until its HTTP endpoint is actually usable.
        # llama-server can bind the port before the model is ready. During that window
        # /v1/chat/completions returns 503, which previously caused handoffs to fail.
        settings.switch_exclusive_sync(engine_name)
        self._wait_for_endpoint(endpoint, engine_name, timeout=timeout)

    def _wait_for_endpoint(self, endpoint: str, label: str, timeout: float | None = None) -> None:
        import urllib.parse

        deadline = time.time() + float(timeout or os.getenv("SYMON_ENGINE_READY_TIMEOUT", "240"))
        last_error = ""

        parsed = urllib.parse.urlparse(endpoint)
        root_url = f"{parsed.scheme}://{parsed.netloc}/"

        while time.time() < deadline:
            try:
                with httpx.Client(timeout=12.0) as client:
                    if "/v1/chat/completions" in endpoint:
                        resp = client.post(endpoint, json={
                            "messages": [{"role": "user", "content": "ready"}],
                            "max_tokens": 1,
                            "stream": False,
                            "temperature": 0,
                        })
                        if resp.status_code < 500:
                            return
                        last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                    else:
                        resp = client.get(root_url)
                        if resp.status_code < 500:
                            return
                        last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
            except Exception as exc:
                last_error = repr(exc)

            time.sleep(float(os.getenv("SYMON_ENGINE_READY_POLL", "1.0")))

        raise RuntimeError(f"{label} endpoint not ready after timeout: {endpoint}; last_error={last_error}")

    def _manager_route(self, endpoint: str, prompt: str, requested_route: str | None) -> dict[str, Any]:
        if requested_route in {"writer", "code", "image"}:
            return {
                "route": requested_route,
                "clean_request": prompt,
                "user_message": "I will handle this with the right worker.",
                "quality_bar": "The result should be complete and useful.",
            }
        raw = self._call_writer(endpoint, MANAGER_SYSTEM, prompt, max_tokens=650, temperature=0.1)
        parsed = self._parse_json(raw)
        if parsed:
            return parsed
        return {
            "route": self._fallback_route(prompt),
            "clean_request": prompt,
            "user_message": "I will route this to the correct worker.",
            "quality_bar": "The result should satisfy the request.",
            "raw": raw,
        }

    def _fallback_route(self, prompt: str) -> str:
        text = prompt.lower()
        if any(x in text for x in ["image", "picture", "photo", "draw", "render", "stable diffusion", "generate art"]):
            return "image"
        if any(x in text for x in ["code", "python", "bash", "cpp", "c++", "api", "repo", "script", "build", "test", "patch", "frontend", "backend", "docker", "bitbake", "systemd", "zip", "tar.gz"]):
            return "code"
        return "writer"

    def _call_writer(self, endpoint: str, system: str, prompt: str, max_tokens: int = 900, temperature: float = 0.2) -> str:
        payload = build_chat_payload(
            prompt=prompt,
            system_prompt=system,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            stream=False,
        )
        with httpx.Client(timeout=240.0) as client:
            resp = client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content") or json.dumps(data)

    def _run_code_worker(self, job_id: str, endpoint: str, clean: str, quality_bar: str, revision: str) -> dict[str, Any]:
        job = self.jobs[job_id]
        workspace = Path(job.workspace)
        code_prompt = f"""
WRITER MANAGER CLEAN REQUEST:
{clean}

QUALITY BAR:
{quality_bar}

REVISION REQUEST IF ANY:
{revision or "None"}

Build the code/package now. Do not ask questions. Return strict JSON manifest.
""".strip()
        payload = {
            "messages": [
                {"role": "system", "content": CODE_AGENT_SYSTEM},
                {"role": "user", "content": code_prompt},
            ],
            "stream": False,
            "temperature": 0.15,
            "top_p": 0.95,
            "max_tokens": int(os.getenv("SYMON_CODER_MAX_TOKENS", "2600")),
        }
        self._log(job_id, "calling exclusive code worker")
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
        raw = data.get("choices", [{}])[0].get("message", {}).get("content") or json.dumps(data, indent=2)
        (workspace / "CODE_WORKER_RAW.md").write_text(raw, encoding="utf-8")

        manifest = self._parse_json(raw) or {"files": [{"path": "CODE_WORKER_RAW.md", "content": raw}], "test_commands": [], "notes": "Raw code response saved."}
        files = self._write_manifest_files(workspace, manifest.get("files", []), job_id)
        test_log = self._run_tests(workspace, manifest.get("test_commands", []), job_id)

        (workspace / "HANDOFF_SUMMARY.json").write_text(json.dumps({"files": files, "notes": manifest.get("notes", ""), "test_log": test_log}, indent=2), encoding="utf-8")
        archive = shutil.make_archive(str(self.artifact_root / f"{job_id}_code_package"), "gztar", root_dir=workspace)
        self._update(job_id, artifact=archive)
        return {"artifact": archive, "files": files, "notes": manifest.get("notes", ""), "test_log": test_log}

    def _run_image_worker(self, job_id: str, endpoint: str, data: dict[str, Any], revision: str) -> dict[str, Any]:
        prompt = data.get("prompt") or ""
        if revision:
            prompt = f"{prompt}, correction: {revision}"
        payload_data = {**data, "prompt": prompt}
        errors = []
        self._log(job_id, "calling exclusive image worker")
        with httpx.Client(timeout=300.0) as client:
            for label, payload in image_payload_attempts(payload_data):
                resp = client.post(endpoint, json=payload)
                if resp.status_code >= 400:
                    errors.append({"mode": label, "status": resp.status_code, "body": resp.text[:900]})
                    continue
                try:
                    parsed = resp.json()
                except Exception:
                    errors.append({"mode": label, "status": resp.status_code, "body": resp.text[:900]})
                    continue
                image = (parsed.get("images") or [None])[0]
                if not image:
                    errors.append({"mode": label, "status": resp.status_code, "body": "no image field"})
                    continue
                image = re.sub(r"^data:image/\w+;base64,", "", image)
                raw = base64.b64decode(image)
                out = self.image_root / f"{job_id}.png"
                out.write_bytes(raw)
                self._update(job_id, image_path=str(out), image_b64=image)
                return {"image_path": str(out), "payload_mode": label, "bytes": len(raw)}
        raise RuntimeError(f"image generation failed: {errors}")

    def _assess(self, endpoint: str, user_prompt: str, clean: str, route: str, result: dict[str, Any], quality_bar: str) -> tuple[bool, str, str]:
        assessment_prompt = f"""
USER REQUEST:
{user_prompt}

CLEAN WORKER REQUEST:
{clean}

ROUTE:
{route}

QUALITY BAR:
{quality_bar}

WORKER RESULT SUMMARY:
{json.dumps(result, indent=2)[:4000]}

Approve or request revision.
""".strip()
        raw = self._call_writer(endpoint, ASSESS_SYSTEM, assessment_prompt, max_tokens=450, temperature=0.1)
        parsed = self._parse_json(raw) or {}
        approved = bool(parsed.get("approved", True))
        revision = str(parsed.get("revision_request", "") or "")
        msg = str(parsed.get("user_status", "") or "")
        if not msg:
            msg = self._default_done_message(route)
        return approved, revision, msg

    def _default_done_message(self, route: str) -> str:
        if route == "code":
            return "The background code worker finished and returned a compressed artifact."
        if route == "image":
            return "The image worker finished and returned an image."
        return "Done."

    def _parse_json(self, raw: str) -> dict[str, Any] | None:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
            text = re.sub(r"```$", "", text).strip()
        candidates = [text]
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidates.append(text[start:end + 1])
        for c in candidates:
            try:
                obj = json.loads(c)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        return None

    def _write_manifest_files(self, workspace: Path, files: Any, job_id: str) -> list[str]:
        written: list[str] = []
        if not isinstance(files, list):
            return written
        for item in files:
            if not isinstance(item, dict):
                continue
            rel = str(item.get("path", "")).strip().lstrip("/")
            content = str(item.get("content", ""))
            if not rel or ".." in Path(rel).parts:
                self._log(job_id, f"skipped unsafe path {rel!r}")
                continue
            dest = (workspace / rel).resolve()
            if not str(dest).startswith(str(workspace.resolve())):
                self._log(job_id, f"skipped escaping path {rel!r}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            written.append(rel)
        return written

    def _run_tests(self, workspace: Path, commands: Any, job_id: str) -> str:
        if str(os.getenv("SYMON_CODER_RUN_TESTS", "true")).lower() not in {"1", "true", "yes", "on"}:
            return "test execution disabled"
        if not isinstance(commands, list):
            return "no tests"
        log_path = workspace / "TEST_LOG.txt"
        for command in commands[:8]:
            cmd = str(command).strip()
            if not cmd:
                continue
            self._log(job_id, f"test: {cmd}")
            try:
                result = subprocess.run(cmd, cwd=workspace, shell=True, text=True, capture_output=True, timeout=int(os.getenv("SYMON_CODER_TEST_TIMEOUT", "90")))
                log_path.open("a", encoding="utf-8").write(f"$ {cmd}\nexit={result.returncode}\nSTDOUT:\n{result.stdout[-4000:]}\nSTDERR:\n{result.stderr[-4000:]}\n\n")
            except Exception as exc:
                log_path.open("a", encoding="utf-8").write(f"$ {cmd}\nFAILED TO RUN: {exc!r}\n\n")
        return str(log_path)


EXCLUSIVE_HANDOFF = ExclusiveHandoffManager()
