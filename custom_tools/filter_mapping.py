import argparse
import json
import sys
from pathlib import Path

def filter_mappings(input_path: Path, output_path: Path, threshold: float) -> None:
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{input_path}': {e}", file=sys.stderr)
        sys.exit(1)

    filtered = {}
    total = 0
    kept = 0

    for src_name, data in mappings.items():
        total += 1
        score = data.get('score', 0)
        if score > threshold:
            filtered[src_name] = data
            kept += 1

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, indent=2)
    except IOError as e:
        print(f"Error: Could not write to '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Filtered {total} entries → kept {kept} with score > {threshold}")
    print(f"Saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Filter mappings.json to keep only matches above a score threshold."
    )
    parser.add_argument(
        '--input', '-i',
        default='mappings.json',
        help='Input mapping JSON file (default: mappings.json)'
    )
    parser.add_argument(
        '--output', '-o',
        default='filtered_mappings.json',
        help='Output JSON file (default: trimmed_mappings.json)'
    )
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=0.6,
        help='Score threshold (keep if score > threshold, default: 0.6)'
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    filter_mappings(input_path, output_path, args.threshold)

if __name__ == '__main__':
    main()
