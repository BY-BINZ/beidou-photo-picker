import argparse
import json
import sys
from .core import export_files, match_files, save_plan


def main():
    parser = argparse.ArgumentParser(description='摄影师一键选图 · 北斗免费版')
    parser.add_argument('--selected', help='客户选好的小图目录')
    parser.add_argument('--originals', help='高清图或 RAW 目录')
    parser.add_argument('--output', help='独立输出目录；不填时只预览')
    parser.add_argument('--report', help='另存匹配清单 JSON，不覆盖现有文件')
    args = parser.parse_args()
    if not args.selected and not args.originals:
        from .gui import main as gui
        gui()
        return 0
    if not args.selected or not args.originals:
        parser.error('--selected 和 --originals 必须同时提供')
    try:
        plan = match_files(args.selected, args.originals)
        if sys.stdout is not None:
            print(json.dumps(plan.summary(), ensure_ascii=False))
        if args.report:
            save_plan(plan, args.report)
        if args.output:
            result = export_files(plan, args.output)
            if sys.stdout is not None:
                print(json.dumps(result, ensure_ascii=False))
            return 2 if result['failed'] or result['unresolved'] else 0
        return 2 if any(row.status != 'matched' for row in plan.rows) else 0
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
