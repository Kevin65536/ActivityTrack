"""Build a new isolated, validated portable release without touching user data."""
import argparse
import datetime
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

from src.version import __version__

ROOT = Path(__file__).resolve().parent
PACKAGE_FILES = {'ActivityTrack.exe', 'portable.txt', 'config.example.json', 'README.md',
                 'CHANGELOG.md', 'build-info.json'}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_package(directory):
    files = []
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Package symlinks are not allowed: {path.name}')
        if not path.is_file():
            continue
        relative = path.relative_to(directory)
        if relative.parts[0] not in {'_internal', 'licenses'} and relative.as_posix() not in PACKAGE_FILES:
            raise ValueError(f'Unexpected package file: {relative}')
        if path.name.lower() in {'config.json', 'app_trace.txt', 'activitytrack.lock'} or path.suffix.lower() in {'.db', '.db-wal', '.db-shm', '.log'}:
            raise ValueError(f'User data must never be packaged: {relative}')
        files.append(path)
    if not (directory / 'ActivityTrack.exe').is_file():
        raise ValueError('The built executable is missing')
    return files


def collect_licenses(directory):
    for distribution in metadata.distributions():
        name = distribution.metadata['Name']
        for relative in distribution.files or ():
            parts = relative.parts
            if '.dist-info' not in str(relative) or not any('license' in part.lower() or 'copying' in part.lower() for part in parts[1:]):
                continue
            source = Path(distribution.locate_file(relative))
            if source.is_file():
                target = directory / 'licenses' / name / Path(*parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)


def build_environment(*, include_python=True):
    # PyInstaller resolves DLLs through PATH. Keep unrelated desktop-tool DLLs
    # (notably private UCRT copies) out of this subprocess, without changing the
    # user's environment or system configuration.
    environment = os.environ.copy()
    windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    paths = [windows / 'System32', windows]
    if include_python:
        paths[:0] = [Path(sys.executable).parent, Path(sys.base_prefix)]
    environment['PATH'] = os.pathsep.join(map(str, paths))
    for variable in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH'):
        environment.pop(variable, None)
    return environment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-dirty', action='store_true', help='Allow local development builds (marked in manifest)')
    args = parser.parse_args(argv)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    source_status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT)
    source_diff = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=ROOT)
    dirty = bool(source_status.strip())
    if dirty and not args.allow_dirty:
        raise RuntimeError('Commit the source first, or use --allow-dirty for a development build')
    if platform.system() != 'Windows' or platform.machine().upper() != 'AMD64':
        raise RuntimeError('Build on Windows x64')
    if platform.python_version() != (ROOT / '.python-version').read_text().strip():
        raise RuntimeError('Use the Python version pinned in .python-version')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'outputs' / 'releases' / f'{__version__}-{stamp}'
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, '-m', 'PyInstaller', str(ROOT / 'ActivityTrack.spec'),
                    '--distpath', str(output / 'dist'), '--workpath', str(output / 'build'),
                    '--noconfirm'], cwd=ROOT, env=build_environment(), check=True)
    package = output / 'dist' / 'ActivityTrack'
    (package / 'portable.txt').write_text('Keep data beside ActivityTrack.exe. Back up tracker.db and config.json before upgrading.\n', encoding='utf-8')
    for filename in ('config.example.json', 'README.md', 'CHANGELOG.md'):
        shutil.copy2(ROOT / filename, package / filename)
    collect_licenses(package)
    files = validate_package(package)
    info = {
        'version': __version__, 'commit': commit, 'dirty': dirty,
        'python': platform.python_version(), 'platform': 'Windows-x64',
        'created_utc': stamp, 'uv_lock_sha256': sha256(ROOT / 'uv.lock'),
        'dependencies': dict(sorted((dist.metadata['Name'], dist.version) for dist in metadata.distributions())),
        'files': {path.relative_to(package).as_posix(): sha256(path) for path in files},
    }
    (package / 'build-info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    shutil.copy2(package / 'build-info.json', output / 'build-info.json')
    smoke_dir = output / 'smoke'
    result = subprocess.run([str(package / 'ActivityTrack.exe'), '--smoke-test', '--data-dir', str(smoke_dir)],
                            cwd=output, env=build_environment(include_python=False), timeout=90)
    report = json.loads((smoke_dir / 'smoke-result.json').read_text(encoding='utf-8'))
    if result.returncode or not report['ok']:
        raise RuntimeError(f'Packaged smoke test failed: {report}')
    if (subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != commit
            or subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT) != source_status
            or subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=ROOT) != source_diff):
        raise RuntimeError('Source changed during the build; rebuild from a stable revision')
    archive = output / 'ActivityTrack-Portable.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in validate_package(package):
            bundle.write(path, 'ActivityTrack/' + path.relative_to(package).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError('ZIP verification failed')
    (output / 'SHA256SUMS.txt').write_text(f'{sha256(archive)}  {archive.name}\n', encoding='ascii')
    print(json.dumps({'output': str(output), 'archive': str(archive), 'sha256': sha256(archive), 'smoke': report['ok']}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
