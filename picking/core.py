"""PicKing 基础文件名匹配工作流；不读取照片内容，不含授权或模型。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone

SELECTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
ORIGINAL_FORMATS = SELECTED_FORMATS | {
    '.cr3', '.cr2', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.raw'
}


def normalize_stem(name: str) -> str:
    # Extracted from PicKing's filename normalization; no visual recognition.
    stem = Path(name).stem.lower().strip()
    return re.sub(r'\s*[-_ ]\s*(副本|copy)(?:\s*\(\d+\))?$', '', stem, flags=re.I)


def frame_number(name: str) -> str:
    # BR5_7539 must use 7539, never the camera prefix 5.
    nums = [n for n in re.findall(r'\d+', normalize_stem(name)) if len(n) >= 3]
    return nums[-1] if nums else ''


def _folder(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f'不是文件夹：{root}')
    return root


def _files(root: Path, formats: set[str]):
    def onerror(error):
        raise error
    for base, dirs, files in os.walk(root, onerror=onerror, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
        for name in sorted(files):
            path = Path(base) / name
            if not path.is_symlink() and path.suffix.lower() in formats:
                yield path


@dataclass(frozen=True)
class Match:
    selected: str
    relative: str
    original: str | None
    status: str
    method: str
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    selected_root: str
    original_root: str
    rows: tuple[Match, ...]

    def summary(self):
        return {key: sum(row.status == key for row in self.rows)
                for key in ('matched', 'missing', 'ambiguous')}


def match_files(selected_dir: str | Path, original_dir: str | Path) -> Plan:
    selected_root, original_root = _folder(selected_dir), _folder(original_dir)
    if (selected_root == original_root or selected_root.is_relative_to(original_root)
            or original_root.is_relative_to(selected_root)):
        raise ValueError('小图与原图目录必须分开，不能相同或互相包含。')
    exact, numbers = {}, {}
    for path in _files(original_root, ORIGINAL_FORMATS):
        exact.setdefault(normalize_stem(path.name), []).append(path)
        number = frame_number(path.name)
        if number:
            numbers.setdefault(number, []).append(path)
    rows = []
    for path in _files(selected_root, SELECTED_FORMATS):
        relative = path.relative_to(selected_root)
        candidates = exact.get(normalize_stem(path.name), [])
        method = 'filename'
        if not candidates:
            candidates = numbers.get(frame_number(path.name), [])
            method = 'number'
        same_folder = [p for p in candidates
                       if p.parent.relative_to(original_root) == relative.parent]
        if same_folder:
            candidates = same_folder
        candidates = sorted(candidates)
        status = 'matched' if len(candidates) == 1 else ('ambiguous' if candidates else 'missing')
        rows.append(Match(str(path), relative.as_posix(),
                          str(candidates[0]) if status == 'matched' else None,
                          status, method if candidates else '', tuple(map(str, candidates))))
    return Plan(str(selected_root), str(original_root), tuple(rows))


def save_plan(plan: Plan, destination: str | Path):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(asdict(plan), stream, ensure_ascii=False, indent=2)


def _log(stream, record):
    stream.write(json.dumps(record, ensure_ascii=False) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def export_files(plan: Plan, output_dir: str | Path, progress=None) -> dict:
    output = Path(output_dir).expanduser().resolve()
    roots = [_folder(plan.selected_root), _folder(plan.original_root)]
    if any(output == root or output.is_relative_to(root) or root.is_relative_to(output) for root in roots):
        raise ValueError('输出目录必须独立于小图和原图目录，不能互相包含。')
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log_path = output / f'_picking_export_{stamp}.jsonl'
    result = {'selected': len(plan.rows), 'copied': 0, 'unresolved': 0,
              'failed': 0, 'log': str(log_path)}
    with log_path.open('x', encoding='utf-8') as log:
        _log(log, {'event': 'start', 'version': '0.1.0', 'selected': len(plan.rows)})
        for index, row in enumerate(plan.rows):
            if row.status != 'matched' or not row.original:
                result['unresolved'] += 1
                _log(log, {'event': 'unresolved', **asdict(row)})
                continue
            temporary = None
            try:
                src = Path(row.original)
                relative = Path(row.relative)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('非法相对路径')
                if src.is_symlink() or not src.resolve(strict=True).is_relative_to(roots[1]):
                    raise ValueError('原图路径不在原图目录内')
                parent = output / relative.parent
                parent.mkdir(parents=True, exist_ok=True)
                if not parent.resolve().is_relative_to(output):
                    raise ValueError('输出路径超出输出目录')
                name = relative.stem + src.suffix
                destination = parent / name
                fd, tmp_name = tempfile.mkstemp(prefix='.picking-', suffix='.part', dir=parent)
                temporary = Path(tmp_name)
                _log(log, {'event': 'copying', 'selected': row.selected,
                           'source': str(src), 'temporary': str(temporary)})
                digest = hashlib.sha256()
                with os.fdopen(fd, 'wb') as target, src.open('rb') as source:
                    before = os.fstat(source.fileno())
                    for chunk in iter(lambda: source.read(1024 * 1024), b''):
                        target.write(chunk)
                        digest.update(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                    after = os.fstat(source.fileno())
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise OSError('复制期间原图发生变化，请重试该文件')
                check = hashlib.sha256()
                with temporary.open('rb') as copied:
                    for chunk in iter(lambda: copied.read(1024 * 1024), b''):
                        check.update(chunk)
                if check.digest() != digest.digest():
                    raise OSError('复制后校验失败')
                suffix = 0
                while True:
                    try:
                        # Atomic no-overwrite publication on the same filesystem.
                        os.link(temporary, destination)
                        break
                    except FileExistsError:
                        suffix += 1
                        destination = parent / f'{Path(name).stem}_{suffix}{Path(name).suffix}'
                result['copied'] += 1
                _log(log, {'event': 'copied', 'selected': row.selected,
                           'source': str(src), 'destination': str(destination),
                           'sha256': digest.hexdigest(), 'bytes': after.st_size})
            except Exception as error:
                result['failed'] += 1
                _log(log, {'event': 'failed', 'selected': row.selected, 'error': str(error)})
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            if progress:
                progress(index + 1, len(plan.rows))
        _log(log, {'event': 'complete', **result})
    return result
