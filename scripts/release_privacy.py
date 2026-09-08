"""Source and package privacy checks; never print matched secret values."""
import argparse
import json
import re
import subprocess
import marshal
import types
import sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'personal-path': re.compile(rb'(?:/Users/|[A-Z]:\\Users\\)(?!(?:USER|user|username|example|Shared|runner|name)\b)[A-Za-z0-9_.-]+'),
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'provider-key': re.compile(rb'\b(?:sk-(?:proj-|ant-|or-v1-)?[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16})\b'),
    'credential-url': re.compile(rb'https?://[^\s/"\x27<>]+:[^\s/"\x27<>]+@'),
    'credential-literal': re.compile(rb'(?i)["\x27](?:api[_-]?key|password|access_token|refresh_token|client_secret)["\x27]\s*[:=]\s*["\x27]([A-Za-z0-9_+./=-]{20,})["\x27]'),
}
FORBIDDEN = {'settings.json', 'subscriptions.json', 'sources.json', 'pending-diagnostic.json',
             'app-instance.lock', 'sqlite.db', '.env', 'crew-audit-task.json'}


def interpreter_build_roots():
    # Only roots recorded by the installed interpreter's own build metadata.
    # Never exempt this machine's user home, application source or credentials.
    roots = set()
    current_home = str(Path.home()).encode()
    for value in sysconfig.get_config_vars().values():
        if isinstance(value, str):
            for hit in RULES['personal-path'].finditer(value.encode()):
                root = hit.group()
                if root != current_home and not current_home.startswith(root + b'/'):
                    roots.add(root)
    return roots


def scan_bytes(raw, upstream_native=False, python_runtime=False):
    findings = []
    for name, rule in RULES.items():
        hits = list(rule.finditer(raw))
        # PyObjC wheels contain upstream compiler metadata, not app-user data.
        if name == 'personal-path' and upstream_native:
            hits = [m for m in hits if m.group() != b'/Users/' + b'ronald']
        if name == 'personal-path' and python_runtime:
            approved = interpreter_build_roots()
            hits = [m for m in hits if m.group() not in approved]
        if hits:
            findings.append(name)
    return findings


def scan_frozen(executable):
    from PyInstaller.archive.readers import CArchiveReader
    archive = CArchiveReader(str(executable))
    pyz = archive.open_embedded_archive('PYZ.pyz')
    findings = []
    def inspect_code(code, label, metadata=False):
        if isinstance(code, types.CodeType):
            for rule in scan_bytes(code.co_filename.encode()):
                findings.append(f'{label}: {rule}')
            for const in code.co_consts:
                inspect_code(const, label, metadata)
        elif isinstance(code, (str, bytes)):
            for rule in scan_bytes(code.encode() if isinstance(code, str) else code, python_runtime=metadata):
                findings.append(f'{label}: {rule}')
        elif isinstance(code, (tuple, frozenset)):
            for const in code:
                inspect_code(const, label, metadata)
    for name in pyz.toc:
        inspect_code(pyz.extract(name), 'frozen module ' + name, metadata=name.startswith('_sysconfigdata_'))
    for name, entry in archive.toc.items():
        if entry[-1] == 's':
            inspect_code(marshal.loads(archive.extract(name)), 'entry module ' + name)
    return sorted(set(findings))


def source_files():
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            cwd=ROOT, capture_output=True, check=True)
    return sorted({ROOT / p.decode() for p in result.stdout.split(b'\0') if p})


def scan(paths, root):
    findings = []
    for path in paths:
        relative = path.relative_to(root)
        if path.name in FORBIDDEN or any(part in {'private', 'screenshots', 'outputs', 'output', 'deploy'} for part in relative.parts):
            findings.append(f'{relative}: runtime/private file')
        if path.is_symlink() and not path.resolve().is_relative_to(root.resolve()):
            findings.append(f'{relative}: external symlink')
            continue
        if not path.is_file():
            continue
        raw = path.read_bytes()
        upstream = path.suffix == '.so' and path.parent.name in {'objc', 'AppKit', 'Foundation', 'CoreFoundation'}
        runtime = path.name == 'Python' or (path.suffix == '.so' and path.parent.name == 'lib-dynload')
        for rule in scan_bytes(raw, upstream_native=upstream, python_runtime=runtime):
            findings.append(f'{relative}: {rule}')
        if path.name == 'pricing.json' and json.loads(raw).get('subscriptions'):
            findings.append(f'{relative}: populated subscriptions')
        if path.name == 'update-settings.example.json' and json.loads(raw).get('telemetry_endpoint'):
            findings.append(f'{relative}: nonempty diagnostics endpoint')
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path)
    args = parser.parse_args()
    if args.package:
        root = args.package.resolve()
        if not root.is_dir():
            parser.error('package must be an existing directory')
        paths = [p for p in root.rglob('*') if p.is_file() or p.is_symlink()]
    else:
        root, paths = ROOT, source_files()
    findings = scan(paths, root)
    if args.package:
        executables = [p for p in paths if p.name in {'AI Subscription Usage', 'AI Subscription Usage.exe'} and p.is_file()]
        if not executables:
            findings.append('package: missing application executable')
        for executable in executables:
            findings.extend(scan_frozen(executable))
    if findings:
        print('Privacy check failed (values redacted):\n' + '\n'.join(findings))
        return 1
    print(f'Privacy check passed: {len(paths)} files checked; no configured sensitive-data patterns found')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
