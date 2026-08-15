#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[1] / "powershell-stdin.sh"


class PowerShellStdinLauncherTests(unittest.TestCase):
    def make_fake_powershell(self, directory: Path) -> tuple[Path, Path, Path]:
        arguments = directory / "arguments.json"
        standard_input = directory / "stdin.bin"
        invoked = directory / "invoked"
        fake = directory / "powershell.exe"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['FAKE_ARGUMENTS']).write_text(json.dumps(sys.argv[1:]))\n"
            "pathlib.Path(os.environ['FAKE_STDIN']).write_bytes(sys.stdin.buffer.read())\n"
            "pathlib.Path(os.environ['FAKE_INVOKED']).touch()\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        return arguments, standard_input, invoked

    def test_forwards_readable_stdin_with_exact_powershell_arguments(self) -> None:
        payload = b"$ErrorActionPreference = 'Stop'\nWrite-Output 'readable'\n"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            arguments, standard_input, invoked = self.make_fake_powershell(directory)
            environment = os.environ.copy()
            environment.update({
                "PATH": str(directory) + os.pathsep + environment.get("PATH", ""),
                "FAKE_ARGUMENTS": str(arguments),
                "FAKE_STDIN": str(standard_input),
                "FAKE_INVOKED": str(invoked),
            })

            result = subprocess.run(
                [str(LAUNCHER)], input=payload, capture_output=True, env=environment,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(
                json.loads(arguments.read_text(encoding="utf-8")),
                ["-NoProfile", "-NonInteractive", "-File", "-"],
            )
            self.assertEqual(standard_input.read_bytes(), payload)
            self.assertTrue(invoked.exists())

    def test_rejects_arguments_before_invoking_powershell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            arguments, standard_input, invoked = self.make_fake_powershell(directory)
            environment = os.environ.copy()
            environment.update({
                "PATH": str(directory) + os.pathsep + environment.get("PATH", ""),
                "FAKE_ARGUMENTS": str(arguments),
                "FAKE_STDIN": str(standard_input),
                "FAKE_INVOKED": str(invoked),
            })

            result = subprocess.run(
                [str(LAUNCHER), "Write-Output 'not stdin'"],
                capture_output=True, env=environment, check=False,
            )

            self.assertEqual(result.returncode, 64)
            self.assertIn(b"arguments are not accepted", result.stderr)
            self.assertFalse(invoked.exists())

    def test_fails_clearly_when_powershell_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                ["/bin/bash", str(LAUNCHER)], input=b"Write-Output 'safe'\n",
                capture_output=True, env={"PATH": temporary}, check=False,
            )

            self.assertEqual(result.returncode, 127)
            self.assertIn(b"powershell.exe was not found on PATH", result.stderr)


if __name__ == "__main__":
    unittest.main()
