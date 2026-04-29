from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from subprocess import Popen
from typing import Any

from app.core.config import Settings
from app.core.enums import (
    LONGVIDEO_FRAME_INTERVAL_OPTIONS,
    LONGVIDEO_SEGMENT_INTERVAL_OPTIONS,
    PreprocessModeEnum,
    SceneEnum,
    default_preprocess_mode_for_scene,
)
from app.core.errors import ApiError
from app.workers.local_jobs import LocalJobRunner


class TaskTerminatedError(RuntimeError):
    pass


class LongVideoService:
    def __init__(self, settings: Settings, job_runner: LocalJobRunner):
        self.settings = settings
        self.job_runner = job_runner
        self.temp_root = Path(settings.preprocess_temp_dir)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def resolve_and_validate(self, scene: str, preprocess_mode: str | None, interval_sec: int | None) -> tuple[str, int]:
        mode = preprocess_mode or default_preprocess_mode_for_scene(scene)
        if mode == PreprocessModeEnum.SEGMENT.value:
            if scene != SceneEnum.TEXT2VIDEO.value:
                raise ApiError(
                    "LONGVIDEO_PREPROCESS_MODE_INVALID",
                    "当前场景不支持 segment 预处理模式",
                    {"scene": scene, "preprocess_mode": mode},
                    retryable=False,
                )
            if interval_sec not in LONGVIDEO_SEGMENT_INTERVAL_OPTIONS:
                raise ApiError(
                    "LONGVIDEO_INTERVAL_INVALID",
                    "切片间隔不合法",
                    {"allowed": sorted(LONGVIDEO_SEGMENT_INTERVAL_OPTIONS), "interval_sec": interval_sec},
                    retryable=False,
                )
        elif mode == PreprocessModeEnum.FRAME.value:
            if scene == SceneEnum.TEXT2VIDEO.value:
                raise ApiError(
                    "LONGVIDEO_PREPROCESS_MODE_INVALID",
                    "视频检索场景必须使用 segment 预处理模式",
                    {"scene": scene, "preprocess_mode": mode},
                    retryable=False,
                )
            if interval_sec not in LONGVIDEO_FRAME_INTERVAL_OPTIONS:
                raise ApiError(
                    "LONGVIDEO_INTERVAL_INVALID",
                    "抽帧间隔不合法",
                    {"allowed": sorted(LONGVIDEO_FRAME_INTERVAL_OPTIONS), "interval_sec": interval_sec},
                    retryable=False,
                )
        else:
            raise ApiError(
                "LONGVIDEO_PREPROCESS_MODE_INVALID",
                "未知的 LongVideo 预处理模式",
                {"preprocess_mode": mode},
                retryable=False,
            )
        return mode, int(interval_sec)

    def preprocess(
        self,
        *,
        scene: str,
        source_video: str,
        job_id: str,
        preprocess_mode: str,
        interval_sec: int,
        cancel_event,
    ) -> list[dict[str, Any]]:
        source = Path(source_video).resolve()
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"LongVideo resource not found: {source_video}")
        duration_sec = self._probe_duration_seconds(str(source), job_id)
        work_dir = self.temp_root / job_id
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            if preprocess_mode == PreprocessModeEnum.SEGMENT.value:
                return self._segment_video(source, duration_sec, interval_sec, work_dir, job_id, cancel_event)
            return self._extract_frames(source, duration_sec, interval_sec, work_dir, job_id, cancel_event)
        except Exception:
            shutil.rmtree(work_dir, ignore_errors=True)
            raise

    def cleanup_job_temp(self, job_id: str) -> None:
        work_dir = self.temp_root / job_id
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

    def ensure_video_readable(self, video_path: str, job_id: str | None = None) -> None:
        path = Path(video_path)
        if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"Invalid video file: {video_path}")

        cmd = [
            self.settings.ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
        stdout, stderr, returncode = self._run_command_capture(cmd, job_id)
        if returncode != 0:
            raise RuntimeError(f"ffprobe validation failed: {stderr.strip() or stdout.strip()}")

        data = json.loads(stdout or "{}")
        streams = data.get("streams") or []
        fmt = data.get("format") or {}
        duration = float(fmt.get("duration") or 0.0)

        if not streams:
            raise RuntimeError(f"No video stream found for segment: {video_path}")
        if duration <= 0:
            raise RuntimeError(f"Invalid segment duration <= 0: {video_path}")

    def _segment_video(self, source: Path, duration_sec: float, interval_sec: int, work_dir: Path, job_id: str, cancel_event) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        total_duration = int(duration_sec + 0.999999)
        start = 0
        while start < total_duration:
            self._raise_if_cancelled(cancel_event)
            end = min(start + interval_sec, total_duration)
            output_name = f"{source.stem}_{start:04d}-{end:04d}.mp4"
            output_path = work_dir / output_name

            # 关键修复：
            # 不再使用 -c copy 快速切片，改为重编码并重置时间戳，
            # 避免生成对 t2v 解码不友好的片段。
            cmd = [
                self.settings.ffmpeg_bin,
                "-y",
                "-ss",
                str(start),
                "-i",
                str(source),
                "-t",
                str(max(1, end - start)),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-fflags",
                "+genpts",
                "-reset_timestamps",
                "1",
                "-avoid_negative_ts",
                "make_zero",
                str(output_path),
            ]
            self._run_process(cmd, job_id)

            if output_path.exists() and output_path.stat().st_size > 0:
                self.ensure_video_readable(str(output_path.resolve()), job_id=job_id)
                items.append(
                    {
                        "source_path": str(output_path.resolve()),
                        "media_type": "video",
                        "parent_video_name": source.name,
                        "segment_start_sec": float(start),
                        "segment_end_sec": float(end),
                        "frame_timestamp_sec": None,
                        "derive_type": "segment",
                    }
                )
            start += interval_sec

        if not items:
            raise RuntimeError("LongVideo segmentation produced 0 valid segments")
        return items

    def _extract_frames(self, source: Path, duration_sec: float, interval_sec: int, work_dir: Path, job_id: str, cancel_event) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        max_second = int(duration_sec)
        for sec in range(0, max_second + 1, interval_sec):
            self._raise_if_cancelled(cancel_event)
            output_name = f"{source.stem}_{sec:04d}.jpg"
            output_path = work_dir / output_name
            cmd = [
                self.settings.ffmpeg_bin,
                "-y",
                "-ss",
                str(sec),
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(output_path),
            ]
            self._run_process(cmd, job_id)
            if output_path.exists() and output_path.stat().st_size > 0:
                items.append(
                    {
                        "source_path": str(output_path.resolve()),
                        "media_type": "image",
                        "parent_video_name": source.name,
                        "segment_start_sec": None,
                        "segment_end_sec": None,
                        "frame_timestamp_sec": float(sec),
                        "derive_type": "frame",
                    }
                )
        return items

    def _probe_duration_seconds(self, source_video: str, job_id: str) -> float:
        cmd = [
            self.settings.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            source_video,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.job_runner.register_process(job_id, proc)
        try:
            stdout, stderr = proc.communicate()
        finally:
            self.job_runner.unregister_process(job_id, proc)
        if proc.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.strip()}")
        return float((stdout or "0").strip())

    def _run_process(self, cmd: list[str], job_id: str) -> None:
        proc: Popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.job_runner.register_process(job_id, proc)
        try:
            stdout, stderr = proc.communicate()
        finally:
            self.job_runner.unregister_process(job_id, proc)
        if proc.returncode != 0:
            raise RuntimeError((stderr or stdout or "ffmpeg command failed").strip())

    def _run_command_capture(self, cmd: list[str], job_id: str | None = None) -> tuple[str, str, int]:
        proc: Popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if job_id:
            self.job_runner.register_process(job_id, proc)
        try:
            stdout, stderr = proc.communicate()
        finally:
            if job_id:
                self.job_runner.unregister_process(job_id, proc)
        return stdout or "", stderr or "", int(proc.returncode or 0)

    @staticmethod
    def _raise_if_cancelled(cancel_event) -> None:
        if cancel_event and cancel_event.is_set():
            raise TaskTerminatedError("任务已被终止")