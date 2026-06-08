"""
Minimal, dependency-free MCP stdio client.

MCP over stdio is newline-delimited JSON-RPC 2.0. This client spawns a server
process, performs the `initialize` / `notifications/initialized` handshake, and
lets you issue requests (tools/list, tools/call, resources/list, resources/read,
ping). A background thread drains stdout so async servers (that respond after a
network round-trip) work too; stdin is held open until close().

Usage:
    from lib.mcp_stdio import McpStdioClient
    with McpStdioClient(["node", "server.mjs"]) as c:
        info = c.initialize()
        tools = c.list_tools()
        out = c.call_tool("list_skills", {})

This is intentionally tiny (stdlib only) so it can be vendored into any project.
"""
from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional


class McpError(RuntimeError):
    pass


class McpStdioClient:
    def __init__(self, command: List[str], cwd: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None, timeout: float = 20.0):
        self.command = command
        self.cwd = cwd
        self.env = env
        self.timeout = timeout
        self._proc: Optional[subprocess.Popen] = None
        self._next_id = 0
        self._inbox: "queue.Queue[dict]" = queue.Queue()
        self._stderr: List[str] = []
        self._reader: Optional[threading.Thread] = None
        self._errreader: Optional[threading.Thread] = None
        self._pending: Dict[int, dict] = {}

    # -- lifecycle -----------------------------------------------------------
    def __enter__(self) -> "McpStdioClient":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def start(self) -> None:
        self._proc = subprocess.Popen(
            self.command, cwd=self.cwd, env=self.env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        self._reader = threading.Thread(target=self._drain_stdout, daemon=True)
        self._reader.start()
        self._errreader = threading.Thread(target=self._drain_stderr, daemon=True)
        self._errreader.start()

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass

    # -- io threads ----------------------------------------------------------
    def _drain_stdout(self) -> None:
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._inbox.put(json.loads(line))
            except json.JSONDecodeError:
                # A server that pollutes stdout with non-JSON is a real bug;
                # record it so the smoke test can flag it.
                self._stderr.append(f"[stdout-non-json] {line}")

    def _drain_stderr(self) -> None:
        assert self._proc and self._proc.stderr
        for line in self._proc.stderr:
            self._stderr.append(line.rstrip("\n"))

    @property
    def stderr_text(self) -> str:
        return "\n".join(self._stderr)

    # -- json-rpc ------------------------------------------------------------
    def _send(self, msg: dict) -> None:
        if not self._proc or not self._proc.stdin:
            raise McpError("server not started")
        if self._proc.poll() is not None:
            raise McpError(f"server exited (code {self._proc.returncode}). stderr:\n{self.stderr_text}")
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def notify(self, method: str, params: Optional[dict] = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def request(self, method: str, params: Optional[dict] = None) -> Any:
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                msg = self._inbox.get(timeout=0.2)
            except queue.Empty:
                if self._proc and self._proc.poll() is not None:
                    raise McpError(f"server exited (code {self._proc.returncode}) awaiting '{method}'. "
                                   f"stderr:\n{self.stderr_text}")
                continue
            mid = msg.get("id")
            if mid is None:
                continue  # server-initiated notification; ignore
            if mid == rid:
                if "error" in msg:
                    raise McpError(f"{method} -> error {msg['error']}")
                return msg.get("result")
            self._pending[mid] = msg
        raise McpError(f"timeout after {self.timeout}s awaiting '{method}'")

    # -- convenience ---------------------------------------------------------
    def initialize(self, client_name: str = "mcp-smoke-test") -> dict:
        res = self.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": "0.1.0"},
        })
        self.notify("notifications/initialized")
        return res

    def list_tools(self) -> List[dict]:
        return (self.request("tools/list") or {}).get("tools", [])

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def list_resources(self) -> List[dict]:
        return (self.request("resources/list") or {}).get("resources", [])

    def read_resource(self, uri: str) -> dict:
        return self.request("resources/read", {"uri": uri})
