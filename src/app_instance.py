"""Per-user process ownership; no extra listening port or PID-based killing."""
from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.request
from pathlib import Path


class AppInstance:
    def __init__(self, root: Path, port: int):
        self.path = root / 'app-instance.lock'
        self.port = port
        self.file = None
        self.token = ''

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        stream = os.fdopen(fd, 'r+b', buffering=0)
        try:
            if sys.platform == 'win32':
                import msvcrt
                # The first byte is reserved for the Windows byte-range lock.
                if os.fstat(fd).st_size == 0:
                    stream.write(b' ')
                stream.seek(0)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError):
            stream.close()
            return False
        except OSError as error:
            stream.close()
            if sys.platform == 'win32' and error.errno in (11, 13, 36):
                return False
            raise
        self.file = stream
        self.token = secrets.token_urlsafe(32)
        stream.seek(1)
        stream.write(json.dumps({'port': self.port, 'token': self.token}).encode())
        stream.truncate()
        return True

    def signal_existing(self, action: str = 'activate', timeout: float = 5) -> bool:
        if action not in {'activate', 'quit'}:
            raise ValueError('unsupported instance action')
        deadline = time.monotonic() + timeout
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            try:
                with self.path.open('rb') as stream:
                    stream.seek(1)
                    metadata = json.load(stream)
                if metadata.get('port') != self.port or not isinstance(metadata.get('token'), str):
                    return False
                request = urllib.request.Request(
                    f'http://127.0.0.1:{self.port}/instance/{action}', data=b'',
                    headers={'X-App-Instance': metadata['token']}, method='POST')
                with opener.open(request, timeout=min(1, max(.01, deadline - time.monotonic()))) as response:
                    return response.status == 200
            except (OSError, ValueError):
                time.sleep(.1)
        return False

    def close(self) -> None:
        if self.file is not None:
            # Keep the inode: unlinking a held lock permits two independent owners.
            if sys.platform == 'win32':
                import msvcrt
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            self.file.close()
            self.file = None
