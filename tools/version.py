# PlatformIO pre-build script: stamps the firmware with its version (FW_VERSION).
#
#   1. FW_VERSION environment variable, if set (CI sets it from the release tag)
#   2. `git describe --tags --dirty` (e.g. v1.0.0, v1.0.0-3-gabc1234, v1.0.0-dirty)
#   3. "dev" when there is no git history yet
import os
import subprocess

Import("env")  # noqa: F821  (provided by PlatformIO/SCons)


def version():
    v = os.environ.get("FW_VERSION", "").strip()
    if v:
        return v
    try:
        out = subprocess.run(["git", "describe", "--tags", "--dirty", "--always"],
                             cwd=env["PROJECT_DIR"], capture_output=True, text=True, timeout=10)  # noqa: F821
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "dev"


v = version().lstrip("v")
print(f"Firmware version: {v}")
env.Append(CPPDEFINES=[("FW_VERSION", env.StringifyMacro(v))])  # noqa: F821
