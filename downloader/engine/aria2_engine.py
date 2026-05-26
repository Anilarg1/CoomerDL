from pathlib import Path
import math
import shutil
import subprocess

from downloader.engine.download_history import DownloadHistory
from downloader.models.download_job import DownloadJob
from downloader.models.download_result import DownloadResult


class Aria2Engine:
    def __init__(
        self,
        history: DownloadHistory,
        executable: str = "aria2c",
        executable_finder=None,
        command_runner=None,
        queue_folder: str | Path = "resources/config/aria2",
        max_retries: int = 3,
        retry_interval: float = 2.0,
        connections_per_file: int = 4,
    ):
        self.history = history
        self.executable = executable
        self.executable_finder = executable_finder or shutil.which
        self.command_runner = command_runner or subprocess.run
        self.queue_folder = Path(queue_folder)
        self.max_retries = max(0, int(max_retries))
        self.retry_interval = max(0.0, float(retry_interval))
        self.connections_per_file = max(1, int(connections_per_file))

    def download(self, job: DownloadJob) -> DownloadResult:
        if self.history.contains(job.database_key):
            return DownloadResult.skipped(job.media_url, "already downloaded")

        job.target_folder.mkdir(parents=True, exist_ok=True)
        executable_path = self.executable_finder(self.executable)
        if not executable_path:
            queue_file = self.write_queue_file([job])
            return DownloadResult.failed(
                job.media_url,
                f"aria2c was not found; queue file written: {queue_file}",
            )

        command = self._build_command(executable_path, job)
        result = self.command_runner(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or f"aria2c exited with {result.returncode}").strip()
            return DownloadResult.failed(job.media_url, message)

        if not job.final_path.exists():
            return DownloadResult.failed(job.media_url, f"aria2c finished but file was not found: {job.final_path}")

        file_size = job.final_path.stat().st_size
        self.history.record_completed(
            job.database_key,
            str(job.final_path),
            file_size,
            user_id=job.user_id,
            post_id=job.post_id,
        )
        return DownloadResult.completed(job.media_url, job.final_path, file_size)

    def write_queue_file(self, jobs: list[DownloadJob]) -> Path:
        self.queue_folder.mkdir(parents=True, exist_ok=True)
        queue_file = self.queue_folder / "aria2_queue.txt"
        with open(queue_file, "a", encoding="utf-8") as file:
            for job in jobs:
                file.write(f"{job.media_url}\n")
                file.write(f"  dir={job.target_folder}\n")
                file.write(f"  out={job.filename}\n")
                for key, value in job.headers.items():
                    if value:
                        file.write(f"  header={key}: {value}\n")
                file.write("\n")
        return queue_file

    def _build_command(self, executable_path: str, job: DownloadJob) -> list[str]:
        command = [
            executable_path,
            "--continue=true",
            "--auto-file-renaming=false",
            f"--max-tries={self.max_retries + 1}",
            f"--retry-wait={math.ceil(self.retry_interval)}",
            f"--max-connection-per-server={self.connections_per_file}",
            f"--split={self.connections_per_file}",
            f"--dir={job.target_folder}",
            f"--out={job.filename}",
        ]
        for key, value in job.headers.items():
            if value:
                command.append(f"--header={key}: {value}")
        command.append(job.media_url)
        return command
