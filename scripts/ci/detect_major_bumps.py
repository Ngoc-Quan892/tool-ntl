#!/usr/bin/env python3
"""Detect major version bumps between current working tree and origin/main for
backend/requirements.txt and frontend/package.json.

Outputs JSON to stdout: {"major_bump": true/false, "details": { ... }}
"""
import json
import os
import re
import subprocess
import sys

SEMVER_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def parse_requirements_text(text):
    deps = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # handle pkg==x.y.z or pkg>=x.y.z etc
        if "==" in line:
            name, ver = line.split("==", 1)
        elif ">=" in line:
            name, ver = line.split(">=", 1)
        elif "~=" in line:
            name, ver = line.split("~=", 1)
        else:
            # skip non pinned
            continue
        name = name.strip().lower()
        ver = ver.strip().split()[0]
        m = SEMVER_RE.search(ver)
        if m:
            major = int(m.group(1))
            deps[name] = major
    return deps


def parse_package_json_text(text):
    try:
        j = json.loads(text)
    except Exception:
        return {}
    deps = {}
    for section in ("dependencies", "devDependencies"):
        for k, v in j.get(section, {}).items():
            # v can be ^1.2.3, ~2.3.4, 3.4.5
            m = SEMVER_RE.search(v)
            if m:
                deps[k.lower()] = int(m.group(1))
    return deps


def git_show(path):
    try:
        out = subprocess.check_output(["git", "show", f"origin/main:{path}"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def main():
    # ensure origin/main is fetched
    try:
        subprocess.run(["git", "fetch", "origin", "main"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    results = {"major_bump": False, "details": {}}

    # backend requirements
    cur_req = read_file("backend/requirements.txt") or ""
    prev_req = git_show("backend/requirements.txt") or ""
    cur_deps = parse_requirements_text(cur_req)
    prev_deps = parse_requirements_text(prev_req)
    backend_major = []
    for pkg, cur_major in cur_deps.items():
        prev_major = prev_deps.get(pkg)
        if prev_major is not None and cur_major > prev_major:
            backend_major.append({"package": pkg, "from": prev_major, "to": cur_major})
    results['details']['backend_major'] = backend_major
    if backend_major:
        results['major_bump'] = True

    # frontend package.json
    cur_pkg = read_file("frontend/package.json") or ""
    prev_pkg = git_show("frontend/package.json") or ""
    cur_deps = parse_package_json_text(cur_pkg)
    prev_deps = parse_package_json_text(prev_pkg)
    frontend_major = []
    for pkg, cur_major in cur_deps.items():
        prev_major = prev_deps.get(pkg)
        if prev_major is not None and cur_major > prev_major:
            frontend_major.append({"package": pkg, "from": prev_major, "to": cur_major})
    results['details']['frontend_major'] = frontend_major
    if frontend_major:
        results['major_bump'] = True

    print(json.dumps(results))
    if results['major_bump']:
        sys.exit(0)


if __name__ == '__main__':
    main()
