#!/usr/bin/env python3
"""
this one is AI'd as fuck

Generate visualizations of mapped functions using a configuration file.
Enhanced with outlier compaction and likely‑complete reporting.
"""

import argparse
import json
import logging
import math
import os
import re
import sys
import statistics
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: Pillow (PIL) is required. Install with: pip install pillow")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Visualization parameters
PIXEL_WIDTH = 128
BYTES_PER_PIXEL = 16
BYTES_PER_ROW = PIXEL_WIDTH * BYTES_PER_PIXEL
BG_COLOR = (40, 40, 40)
FG_COLOR = (0, 255, 0)

def parse_splits(splits_path: str) -> Tuple[List[str], Dict[str, Dict[str, Tuple[int, int]]]]:
    """Parse splits.txt and return header lines and per‑file section ranges."""
    with open(splits_path, 'r') as f:
        lines = f.readlines()

    # Find Sections header
    header_start = None
    for i, line in enumerate(lines):
        if line.strip() == 'Sections:':
            header_start = i
            break
    if header_start is None:
        raise ValueError("No 'Sections:' line found in splits file")

    header_lines = []
    i = header_start
    while i < len(lines):
        line = lines[i]
        if i == header_start or line.startswith('\t'):
            header_lines.append(line.rstrip('\n'))
            i += 1
        else:
            break

    file_sections = {}
    current_file = None
    current_sections = {}

    for line in lines[i:]:
        line = line.rstrip('\n')
        if not line:
            continue
        if line.endswith(':'):
            if current_file is not None:
                file_sections[current_file] = current_sections
                current_sections = {}
            current_file = line[:-1]
        elif current_file is not None and line.startswith('\t'):
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            section = parts[0]
            start_str = parts[1] if 'start:' in parts[1] else parts[2]
            end_str = parts[-1]
            start = int(start_str.split(':')[1], 16)
            end = int(end_str.split(':')[1], 16)
            current_sections[section] = (start, end)

    if current_file is not None:
        file_sections[current_file] = current_sections

    return header_lines, file_sections

def parse_symbols(symbols_path: str) -> Dict[str, Tuple[int, int]]:
    """Parse symbols.txt and return dict name -> (addr, size) for functions."""
    pattern = re.compile(
        r'^(\w+)\s*=\s*\.[a-z]+:0x([0-9a-fA-F]+);\s*//\s*type:function(?:\s+size:0x([0-9a-fA-F]+))?'
    )
    functions = {}
    with open(symbols_path, 'r') as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                name = m.group(1)
                addr = int(m.group(2), 16)
                size = int(m.group(3), 16) if m.group(3) else 0
                functions[name] = (addr, size)
    return functions

def fill_missing_sizes(symbols: Dict[str, Tuple[int, int]]) -> Dict[str, Tuple[int, int]]:
    """
    Estimate missing sizes by taking the distance to the next symbol,
    capped at MAX_FUNC_SIZE (0x2000). Last symbol gets a default size of 0x100.
    """
    items = sorted(symbols.items(), key=lambda x: x[1][0])
    result = {}
    for i, (name, (addr, size)) in enumerate(items):
        if size == 0:
            if i + 1 < len(items):
                next_addr = items[i + 1][1][0]
                MAX_FUNC_SIZE = 0x2000
                size = min(next_addr - addr, MAX_FUNC_SIZE)
            else:
                size = 0x100
        result[name] = (addr, size)
    return result

def map_functions_to_files(
    src_functions: Dict[str, Tuple[int, int]],
    file_sections: Dict[str, Dict[str, Tuple[int, int]]]
) -> Dict[str, List[str]]:
    """Assign each source function to the file whose .text range contains its address."""
    file_to_funcs = defaultdict(list)
    text_ranges = {}
    for file, sections in file_sections.items():
        if '.text' in sections:
            text_ranges[file] = sections['.text']

    for name, (addr, _) in src_functions.items():
        matched = False
        for file, (start, end) in text_ranges.items():
            if start <= addr < end:
                file_to_funcs[file].append(name)
                matched = True
                break
        if not matched:
            logger.debug(f"Function {name} at 0x{addr:x} not in any .text range")
    return dict(file_to_funcs)

def build_file_index(search_roots: List[str]) -> Dict[str, List[str]]:
    """
    Build a map: filename -> list of full paths,
    ONLY within whitelisted directories.
    """
    index = defaultdict(list)

    for root in search_roots:
        if not os.path.exists(root):
            logger.warning(f"Search root does not exist: {root}")
            continue

        logger.debug(f"Indexing root: {root}")

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if fname.endswith(".c"):
                    full_path = os.path.join(dirpath, fname)
                    index[fname].append(full_path)

    logger.info(f"Indexed {len(index)} unique .c filenames from {len(search_roots)} roots")
    return index

def filter_files_by_whitelist_existence(file_to_src_funcs, file_index):
    """
    Keep only files that exist within whitelisted directories.
    """
    filtered = {}

    for file_path, funcs in file_to_src_funcs.items():
        base = os.path.basename(file_path)

        if base in file_index:
            filtered[file_path] = funcs
        else:
            logger.debug(f"No whitelist match for: {file_path}")

    logger.info(f"Whitelist existence kept {len(filtered)} files (out of {len(file_to_src_funcs)})")
    return filtered

def compact_file_mapping(
    functions_data: List[Dict],
    target_functions: Dict[str, Tuple[int, int]],
    score_threshold: float = 0.8
) -> List[str]:
    """
    For a single file, attempt to replace outlier function mappings with better candidates
    to reduce the overall address range.

    functions_data: list of dicts, each containing:
        - src: source function name
        - best_match: best target name
        - candidates: list of candidate target names (full list from top_candidates)
        - candidate_scores: dict mapping target name to score
    Returns: list of chosen target names (same order as input).
    """
    # Gather current addresses and sizes for each function using best_match
    current_addrs = []
    func_info = []  # (src, chosen_target, addr, size, candidates, scores)

    for fd in functions_data:
        best = fd['best_match']
        if best not in target_functions:
            # Fallback: if best not found, skip? but should exist
            current_addrs.append(None)
            func_info.append((fd['src'], best, None, 0, fd['candidates'], fd['candidate_scores']))
            continue
        addr, size = target_functions[best]
        current_addrs.append(addr)
        func_info.append((fd['src'], best, addr, size, fd['candidates'], fd['candidate_scores']))

    # Filter out functions with invalid addresses
    valid_indices = [i for i, addr in enumerate(current_addrs) if addr is not None]
    if len(valid_indices) < 2:
        # Not enough data to detect outliers
        return [info[1] for info in func_info]  # return best_match

    valid_addrs = [current_addrs[i] for i in valid_indices]

    # Compute median and IQR for outlier detection
    median = statistics.median(valid_addrs)
    q1 = statistics.quantiles(valid_addrs, n=4)[0]
    q3 = statistics.quantiles(valid_addrs, n=4)[2]
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    # Identify outliers
    outliers = []
    for idx in valid_indices:
        addr = current_addrs[idx]
        if addr < lower_bound or addr > upper_bound:
            outliers.append(idx)

    if not outliers:
        return [info[1] for info in func_info]

    # For each outlier, try to replace with a candidate that is closer to median
    for idx in outliers:
        src, best, curr_addr, curr_size, candidates, scores = func_info[idx]
        best_score = scores.get(best, 1.0)
        best_candidates = []  # list of (target_name, addr, score)
        for tgt in candidates:
            if tgt == best:
                continue
            if tgt not in target_functions:
                continue
            tgt_score = scores.get(tgt, 0.0)
            if tgt_score < best_score * score_threshold:
                continue
            tgt_addr, _ = target_functions[tgt]
            best_candidates.append((tgt, tgt_addr, tgt_score))

        if not best_candidates:
            continue

        # Choose candidate whose address is closest to current median
        best_candidate = min(best_candidates, key=lambda x: abs(x[1] - median))
        new_target, new_addr, new_score = best_candidate
        # Update
        func_info[idx] = (src, new_target, new_addr, 0, candidates, scores)
        logger.debug(f"Replaced {src}: {best} (0x{curr_addr:x}) -> {new_target} (0x{new_addr:x})")

    # Return chosen targets
    return [info[1] for info in func_info]

def get_coverage_intervals(functions: List[Dict]) -> Tuple[List[Tuple[int, int]], int]:
    """Compute merged intervals (absolute addresses) covered by functions and total covered bytes."""
    intervals = [(f['addr'], f['addr'] + f['size']) for f in functions]
    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    # Convert to tuples
    merged = [(s, e) for s, e in merged]
    covered_bytes = sum(e - s for s, e in merged)
    return merged, covered_bytes

def compute_coverage_info(functions: List[Dict]) -> Dict:
    """Compute coverage info for a list of functions."""
    if not functions:
        return {
            'min_addr': 0,
            'max_end': 0,
            'covered_bytes': 0,
            'coverage_ratio': 0.0,
            'covered_intervals': []
        }
    min_addr = min(f['addr'] for f in functions)
    max_end = max(f['addr'] + f['size'] for f in functions)
    intervals, covered_bytes = get_coverage_intervals(functions)
    total_range = max_end - min_addr
    coverage_ratio = covered_bytes / total_range if total_range > 0 else (1.0 if covered_bytes > 0 else 0.0)
    return {
        'min_addr': min_addr,
        'max_end': max_end,
        'covered_bytes': covered_bytes,
        'coverage_ratio': coverage_ratio,
        'covered_intervals': intervals
    }

def trim_outliers_by_distance(functions: List[Dict], keep_ratio: float = 0.8) -> Tuple[List[Dict], List[Dict], int]:
    """
    Remove up to (1 - keep_ratio) of functions that are furthest from the median address.
    Returns (kept_functions, removed_functions, median_addr).
    """
    if len(functions) <= 1:
        return functions, [], (functions[0]['addr'] if functions else 0)

    # Extract addresses and sort
    addr_list = [(i, f['addr']) for i, f in enumerate(functions)]
    addr_list.sort(key=lambda x: x[1])
    median = statistics.median([a for _, a in addr_list])

    # Compute distances and sort
    dist_list = [(i, abs(addr - median)) for i, addr in addr_list]
    dist_list.sort(key=lambda x: x[1])

    keep_count = max(1, int(math.ceil(keep_ratio * len(functions))))
    keep_indices = {i for i, _ in dist_list[:keep_count]}
    remove_indices = {i for i, _ in dist_list[keep_count:]}

    kept = [functions[i] for i in range(len(functions)) if i in keep_indices]
    removed = [functions[i] for i in range(len(functions)) if i in remove_indices]
    return kept, removed, median

def build_target_text_ranges(
    file_to_src_funcs: Dict[str, List[str]],
    mapping_info: Dict[str, Dict],  # {src_name: {'best_match': str, 'candidates': list, 'candidate_scores': dict}}
    target_functions: Dict[str, Tuple[int, int]],
    compact: bool = False,
    score_threshold: float = 0.8
) -> Dict[str, Dict]:
    """For each source file, collect target functions and compute the overall range."""
    file_data = {}
    for file, src_funcs in file_to_src_funcs.items():
        # Prepare per-function data for this file
        funcs_data = []
        for src_name in src_funcs:
            if src_name not in mapping_info:
                continue
            info = mapping_info[src_name]
            best = info['best_match']
            # Filter candidates that exist in target_functions
            candidates = [c for c in info['candidates'] if c in target_functions]
            # Keep scores for all candidates (even those not in target? we'll filter later)
            scores = {c: s for c, s in info['candidate_scores'].items() if c in target_functions}
            funcs_data.append({
                'src': src_name,
                'best_match': best,
                'candidates': candidates,
                'candidate_scores': scores
            })

        if not funcs_data:
            continue

        # Decide final mapping for each function
        if compact:
            chosen_targets = compact_file_mapping(funcs_data, target_functions, score_threshold)
        else:
            chosen_targets = [fd['best_match'] for fd in funcs_data]

        # Build the final list of function info
        funcs_info = []
        for fd, tgt in zip(funcs_data, chosen_targets):
            if tgt not in target_functions:
                continue
            addr, size = target_functions[tgt]
            if size == 0:
                logger.warning(f"Target function {tgt} still has size 0 after filling, skipping")
                continue
            funcs_info.append({
                'src': fd['src'],
                'tgt': tgt,
                'addr': addr,
                'size': size,
                'score': fd['candidate_scores'].get(tgt, 0.0)  # record chosen score
            })

        if not funcs_info:
            continue

        # Compute coverage for the full set
        full_info = compute_coverage_info(funcs_info)

        file_data[file] = {
            'functions': funcs_info,
            'min_addr': full_info['min_addr'],
            'max_end': full_info['max_end'],
            'covered_intervals': full_info['covered_intervals'],
            'covered_bytes': full_info['covered_bytes'],
            'coverage_ratio': full_info['coverage_ratio']
        }
    return file_data

def create_image(file_data: Dict, output_dir: str, file_path: str):
    """Generate PNG image and JSON metadata for a file."""
    min_addr = file_data['min_addr']
    max_end = file_data['max_end']
    total_bytes = max_end - min_addr
    rows = math.ceil(total_bytes / BYTES_PER_ROW)

    img = Image.new('RGB', (PIXEL_WIDTH, rows), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Use precomputed intervals
    for start_offset, end_offset in file_data['covered_intervals']:
        start_pixel = (start_offset - min_addr) // BYTES_PER_PIXEL
        end_pixel = (end_offset - min_addr + BYTES_PER_PIXEL - 1) // BYTES_PER_PIXEL
        for px in range(start_pixel, end_pixel):
            row = px // PIXEL_WIDTH
            col = px % PIXEL_WIDTH
            if row < rows:
                draw.point((col, row), fill=FG_COLOR)

    rel_dir = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    base_no_ext = os.path.splitext(base_name)[0]
    out_subdir = os.path.join(output_dir, rel_dir) if rel_dir else output_dir
    os.makedirs(out_subdir, exist_ok=True)

    img_path = os.path.join(out_subdir, base_no_ext + '.png')
    img.save(img_path)
    logger.info(f"Saved image: {img_path}")

    json_path = os.path.join(out_subdir, base_no_ext + '.json')
    with open(json_path, 'w') as f:
        json.dump({
            'file': file_path,
            'range': {'start': min_addr, 'end': max_end},
            'bytes_per_pixel': BYTES_PER_PIXEL,
            'image_width': PIXEL_WIDTH,
            'bytes_per_row': BYTES_PER_ROW,
            'rows': rows,
            'functions': file_data['functions'],
            'covered_intervals': [(s - min_addr, e - min_addr) for s, e in file_data['covered_intervals']]
        }, f, indent=2)
    logger.info(f"Saved metadata: {json_path}")

def load_config(config_path: str) -> dict:
    """Load JSON config, return dict."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON config: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Generate visualizations using a config file. Optionally compact address ranges."
    )
    parser.add_argument('--config', default='function_mapping_config.json',
                        help="Path to JSON configuration file (default: function_mapping_config.json)")
    parser.add_argument('--ref-splits', help="Override source splits path")
    parser.add_argument('--ref-symbols', help="Override source symbols path")
    parser.add_argument('--mapping', help="Override mapping.json path")
    parser.add_argument('--target-symbols', help="Override target symbols path")
    parser.add_argument('--img-output', help="Override output directory for images")
    parser.add_argument('--whitelist', help="Comma-separated list of path prefixes to filter source files")
    parser.add_argument('--compact-range', action='store_true',
                        help="Try to replace outlier function mappings to reduce image height")
    parser.add_argument('--score-threshold', type=float, default=0.8,
                        help="Minimum fraction of best score for a candidate to be considered (default 0.8)")
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    config = load_config(args.config)

    # Resolve paths (command line overrides config)
    ref_splits = args.ref_splits or config.get('source_splits')
    ref_symbols = args.ref_symbols or config.get('source_symbols')
    mapping_file = args.mapping or config.get('output', 'mapping.json')
    target_symbols = args.target_symbols or config.get('target_symbols')
    img_output = args.img_output or config.get('img_output', 'visuals')
    whitelist = config.get('whitelist', [])
    if args.whitelist:
        whitelist = [p.strip() for p in args.whitelist.split(',')]
    else:
        if not whitelist:
            whitelist = ['src/sdk/', 'libs/dolsdk2004/src/', 'libs/musyx/src/']

    # Validate required
    if not ref_splits:
        logger.error("Missing source splits path (provide via --ref-splits or config 'source_splits')")
        sys.exit(1)
    if not ref_symbols:
        logger.error("Missing source symbols path (provide via --ref-symbols or config 'source_symbols')")
        sys.exit(1)
    if not mapping_file:
        logger.error("Missing mapping file (provide via --mapping or config 'output')")
        sys.exit(1)
    if not target_symbols:
        logger.error("Missing target symbols path (provide via --target-symbols or config 'target_symbols')")
        sys.exit(1)

    # 1. Parse reference splits
    logger.info("Parsing reference splits...")
    _, ref_file_sections = parse_splits(ref_splits)
    logger.info(f"Found {len(ref_file_sections)} source files")

    # 2. Parse reference symbols
    logger.info("Parsing reference symbols...")
    ref_functions = parse_symbols(ref_symbols)
    logger.info(f"Found {len(ref_functions)} functions")

    # 3. Map reference functions to files
    logger.info("Mapping reference functions to source files...")
    file_to_src_funcs = map_functions_to_files(ref_functions, ref_file_sections)
    logger.info(f"Assigned functions to {len(file_to_src_funcs)} files")

    # 4. Filter files by whitelist
    if whitelist:
        logger.info("Building whitelist-based file index...")
        file_index = build_file_index(whitelist)
        file_to_src_funcs = filter_files_by_whitelist_existence(
            file_to_src_funcs,
            file_index
        )
    else:
        logger.info("No whitelist, processing all files.")

    # 5. Load mapping.json with full candidate info
    logger.info("Loading mapping...")
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)

    mapping_info = {}  # src -> {'best_match': str, 'candidates': list, 'candidate_scores': dict}
    for src_name, info in mapping_data.items():
        best = info.get('best_match')
        candidates = []
        candidate_scores = {}
        if best is not None:
            # Ensure best is in the list (it may not be if top_candidates is limited)
            candidates.append(best)
            candidate_scores[best] = info.get('score', 1.0)
        for cand in info.get('top_candidates', []):
            tgt = cand.get('target')
            if tgt and tgt != best:
                candidates.append(tgt)
                candidate_scores[tgt] = cand.get('score', 0.0)
        mapping_info[src_name] = {
            'best_match': best,
            'candidates': candidates,
            'candidate_scores': candidate_scores
        }
    logger.info(f"Loaded {len(mapping_info)} source functions with candidate lists")

    # 6. Parse target symbols
    logger.info("Parsing target symbols...")
    target_functions_raw = parse_symbols(target_symbols)
    logger.info(f"Found {len(target_functions_raw)} target functions")

    # 7. Fill missing sizes in target symbols
    logger.info("Filling missing target function sizes...")
    target_functions = fill_missing_sizes(target_functions_raw)
    zero_sizes = sum(1 for (_, sz) in target_functions_raw.values() if sz == 0)
    if zero_sizes > 0:
        logger.info(f"Filled sizes for {zero_sizes} functions with missing size")

    # 8. Build target .text ranges for each source file, optionally compacting
    logger.info("Building target .text ranges...")
    file_data = build_target_text_ranges(
        file_to_src_funcs,
        mapping_info,
        target_functions,
        compact=args.compact_range,
        score_threshold=args.score_threshold
    )
    logger.info(f"Found data for {len(file_data)} files")

    # 9. Generate images and JSON
    logger.info("Generating visualizations...")
    for file_path, data in file_data.items():
        create_image(data, img_output, file_path)

    # 10. Generate likely_complete.json (full coverage >= 50%)
    likely_complete = []
    likely_near_candidates = []  # files that didn't meet full coverage

    for file_path, data in file_data.items():
        if data['coverage_ratio'] >= 0.5:
            entry = {
                'file': file_path,
                'min_addr': data['min_addr'],
                'max_end': data['max_end'],
                'covered_bytes': data['covered_bytes'],
                'coverage_ratio': data['coverage_ratio'],
                'functions': data['functions']
            }
            likely_complete.append(entry)
        else:
            likely_near_candidates.append((file_path, data))

    if likely_complete:
        out_path = os.path.join(img_output, 'likely_complete.json')
        with open(out_path, 'w') as f:
            json.dump(likely_complete, f, indent=2)
        logger.info(f"Saved likely_complete.json with {len(likely_complete)} files")
    else:
        logger.info("No file reached 50% coverage, likely_complete.json not written")

    # 11. Generate likely_near_complete.json (trimmed coverage >= 50%)
    likely_near_complete = []
    for file_path, data in likely_near_candidates:
        functions = data['functions']
        if len(functions) < 2:
            # Can't trim meaningfully; skip because it didn't meet full coverage anyway
            continue
        kept, removed, _ = trim_outliers_by_distance(functions, keep_ratio=0.8)
        if not kept:
            continue
        cov_info = compute_coverage_info(kept)
        if cov_info['coverage_ratio'] >= 0.5:
            entry = {
                'file': file_path,
                'min_addr': cov_info['min_addr'],
                'max_end': cov_info['max_end'],
                'covered_bytes': cov_info['covered_bytes'],
                'coverage_ratio': cov_info['coverage_ratio'],
                'functions': kept,
                'total_functions': len(functions),
                'kept_functions': len(kept)
            }
            if removed:
                entry['outliers'] = removed
            likely_near_complete.append(entry)

    if likely_near_complete:
        out_path = os.path.join(img_output, 'likely_near_complete.json')
        with open(out_path, 'w') as f:
            json.dump(likely_near_complete, f, indent=2)
        logger.info(f"Saved likely_near_complete.json with {len(likely_near_complete)} files")
    else:
        logger.info("No file reached 50% coverage after trimming, likely_near_complete.json not written")

    logger.info("Done.")

if __name__ == '__main__':
    main()
