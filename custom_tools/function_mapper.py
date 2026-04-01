import argparse
import json
import logging
import re
import subprocess
import sys
import os
import time
import hashlib
import pickle
from collections import defaultdict, Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import capstone

logger = logging.getLogger(__name__)

# helpers =============================================================================================================

def progress_bar(length: int, progress: float) -> str:
    progress = max(0.0, min(1.0, progress))
    filled = int(progress * length)
    empty = length - filled
    bar = '#' * filled + '-' * empty
    percent = round(progress * 100)
    return f"[{bar}] ({percent}%)"

def format_time(seconds: float) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

# DOL Parsing & disassembly ===========================================================================================

class DOLSection:
    def __init__(self, file_offset: int, load_addr: int, size: int):
        self.file_offset = file_offset
        self.load_addr = load_addr
        self.size = size

def parse_dol(binary_path: str) -> List[DOLSection]: # todo: allow bypassing this if it fails for a given rom? works on my rom :shrug:
    """returns sections"""
    with open(binary_path, 'rb') as f:
        header = f.read(0x100)
        if len(header) < 0x100:
            logger.debug(f"Failed to read DOL header? Good luck, lol")
            return []
        sections = []
        # Text sections
        for i in range(7):
            off = int.from_bytes(header[0x00 + i*4:0x04 + i*4], 'big')
            addr = int.from_bytes(header[0x48 + i*4:0x4c + i*4], 'big')
            size = int.from_bytes(header[0x90 + i*4:0x94 + i*4], 'big')
            if off != 0 and size != 0:
                sections.append(DOLSection(off, addr, size))
                logger.debug(f"Text section {i}: offset=0x{off:x}, addr=0x{addr:x}, size=0x{size:x}")
        # Data sections
        for i in range(11):
            off = int.from_bytes(header[0x1c + i*4:0x20 + i*4], 'big')
            addr = int.from_bytes(header[0x64 + i*4:0x68 + i*4], 'big')
            size = int.from_bytes(header[0xb4 + i*4:0xb8 + i*4], 'big')
            if off != 0 and size != 0:
                sections.append(DOLSection(off, addr, size))
                logger.debug(f"Data section {i}: offset=0x{off:x}, addr=0x{addr:x}, size=0x{size:x}")
        return sections

def address_to_file_offset(sections: List[DOLSection], addr: int) -> Optional[int]:
    for sec in sections:
        if sec.load_addr <= addr < sec.load_addr + sec.size:
            offset = sec.file_offset + (addr - sec.load_addr)
            logger.debug(f"Address 0x{addr:x} maps to file offset 0x{offset:x} (section at 0x{sec.load_addr:x})")
            return offset
    logger.debug(f"Address 0x{addr:x} not found in any DOL section")
    return None

def disassemble_range(binary: str, start: int, end: int, sections: List[DOLSection] = None) -> List[str]:
    if not sections:
        logger.debug("No DOL sections provided, cannot map address to file offset")
        return []
    offset = address_to_file_offset(sections, start)
    if offset is None:
        return []
    size = end - start
    with open(binary, 'rb') as f:
        f.seek(offset)
        code = f.read(size)
    if len(code) < size:
        logger.debug(f"Read only {len(code)} bytes, expected {size} at offset 0x{offset:x}")
    cs = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    cs.detail = False
    instructions = []
    try:
        for i in cs.disasm(code, start):
            instructions.append(i.mnemonic + ' ' + i.op_str)
    except Exception as e:
        logger.debug(f"Capstone disassembly error: {e}")
        return []
    if instructions:
        logger.debug(f"Capstone disassembled {len(instructions)} instructions for {hex(start)}-{hex(end)}")
    else:
        logger.debug(f"Capstone produced no instructions for {hex(start)}-{hex(end)}")
    return instructions


# caching shiz ========================================================================================================

CACHE_DIR = Path.home() / '.function_mapper_cache'
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_key(binary_path: str, addr: int, size: int) -> str:
    path_hash = hashlib.sha256(binary_path.encode()).hexdigest()[:8]
    return f"{path_hash}_{addr:x}_{size:x}"

def load_cache(binary_path: str) -> Dict[str, List[str]]:
    cache_file = CACHE_DIR / f"{Path(binary_path).stem}.disasm_cache.pkl"
    if not cache_file.exists():
        return {}
    try:
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        bin_mtime = os.path.getmtime(binary_path)
        if data.get('binary_mtime') == bin_mtime:
            return data.get('functions', {})
    except Exception as e:
        logger.debug(f"Failed to load cache: {e}")
    return {}

def save_cache(binary_path: str, cache: Dict[str, List[str]]):
    cache_file = CACHE_DIR / f"{Path(binary_path).stem}.disasm_cache.pkl"
    try:
        bin_mtime = os.path.getmtime(binary_path)
        data = {'binary_mtime': bin_mtime, 'functions': cache}
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        logger.debug(f"Failed to save cache: {e}")


# symbol parsing & analysis
def parse_symbols(symbols_file: str) -> Dict[str, Tuple[int, int]]:
    pattern = re.compile(
        r'^(\w+)\s*=\s*(\.[a-z]+):0x([0-9a-fA-F]+);\s*//\s*type:function(?:\s+size:0x([0-9a-fA-F]+))?'
    )
    symbols = {}
    with open(symbols_file) as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                name = m.group(1)
                addr = int(m.group(3), 16)
                size = int(m.group(4), 16) if m.group(4) else 0
                symbols[name] = (addr, size)
    return symbols

def analyze_symbols_file(symbols_file: str, log_debug: bool = False) -> Tuple[int, int, int, int]:
    func_pattern = re.compile(r'type:function')
    label_pattern = re.compile(r'type:label')
    obj_pattern = re.compile(r'type:object')
    counts = {'func': 0, 'label': 0, 'object': 0, 'unmatched': 0}
    with open(symbols_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            if func_pattern.search(line):
                counts['func'] += 1
            elif label_pattern.search(line):
                counts['label'] += 1
            elif obj_pattern.search(line):
                counts['object'] += 1
            else:
                counts['unmatched'] += 1
                if log_debug:
                    logger.debug(f"Unmatched line in {symbols_file}:{line_num} -> {line}")
    return counts['func'], counts['label'], counts['object'], counts['unmatched']

def fill_missing_sizes(symbols: Dict[str, Tuple[int, int]]) -> Dict[str, Tuple[int, int]]:
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


# normalization & feature extraction ==================================================================================

REG = re.compile(r'r\d+')
IMM = re.compile(r'0x[0-9a-fA-F]+')
OFFSET = re.compile(r'\d+\(r\d+\)')

def normalize_instruction(line: str) -> str:
    line = REG.sub('REG', line)
    line = IMM.sub('IMM', line)
    line = OFFSET.sub('MEM', line)
    return line

def normalize_asm(asm: List[str]) -> List[str]:
    return [normalize_instruction(x) for x in asm]

def extract_mnemonic_counter(asm: List[str]) -> Counter:
    counter = Counter()
    for line in asm:
        parts = line.split()
        if parts:
            counter[parts[0]] += 1
    return counter

def extract_calls(asm: List[str]) -> Counter:
    calls = Counter()
    for line in asm:
        if line.startswith('bl '):
            target = line.split()[-1]
            target = IMM.sub('FUNC', target)
            calls[target] += 1
    return calls

def extract_early_calls(asm: List[str], limit=25) -> Counter:
    calls = Counter()
    for line in asm[:limit]:
        if line.startswith('bl '):
            target = line.split()[-1]
            target = IMM.sub('FUNC', target)
            calls[target] += 1
    return calls


# simsilarity  ========================================================================================================

def multiset_jaccard(c1: Counter, c2: Counter) -> float:
    inter = sum((c1 & c2).values())
    union = sum((c1 | c2).values())
    return inter / union if union else 0.0

def sequence_similarity(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    MAX_LEN = 400
    if len(a) > MAX_LEN:
        a = a[:MAX_LEN // 2] + a[-MAX_LEN // 2:]
    if len(b) > MAX_LEN:
        b = b[:MAX_LEN // 2] + b[-MAX_LEN // 2:]
    return SequenceMatcher(None, a, b).ratio()


# function extraction & mapping =======================================================================================

def extract_functions(binary: str, symbols: Dict[str, Tuple[int, int]], max_instr: Optional[int] = None,
                      use_cache: bool = True, progress_interval: float = 1.0) -> Dict[str, Any]:
    # Parse DOL sections once for this binary
    sections = parse_dol(binary)
    if not sections:
        logger.debug(f"No DOL sections found for {binary}")

    cache = load_cache(binary) if use_cache else {}
    updated_cache = {}

    funcs = {}
    total = len(symbols)
    processed = 0
    start_time = time.time()
    last_print = start_time

    for name, (addr, size) in symbols.items():
        key = get_cache_key(binary, addr, size)
        if key in cache:
            raw = cache[key]
        else:
            raw = disassemble_range(binary, addr, addr + size, sections)
            if use_cache:
                updated_cache[key] = raw

        if max_instr:
            raw = raw[:max_instr]

        if raw:
            norm = normalize_asm(raw)
            funcs[name] = {
                "addr": addr,
                "size": size,
                "norm": norm,
                "mnems": extract_mnemonic_counter(norm),
                "calls": extract_calls(norm),
                "early_calls": extract_early_calls(norm)
            }
        else:
            logger.debug(f"No disassembly for {name} at 0x{addr:x} (size=0x{size:x})")

        processed += 1
        if progress_interval > 0:
            now = time.time()
            if now - last_print >= progress_interval:
                logger.info(f"Extracting functions: {processed}/{total} {progress_bar(50, processed/total)}")
                last_print = now

    if progress_interval > 0 and processed > 0:
        logger.info(f"Extracting functions: {processed}/{total} {progress_bar(50, processed/total)}")

    if use_cache and updated_cache:
        full_cache = {**cache, **updated_cache}
        save_cache(binary, full_cache)

    return funcs

def map_functions(src_funcs: Dict[str, Any], target_funcs: Dict[str, Any], size_tol: float = 0.3,
                  jaccard_threshold: float = 0.0, top_k: int = 10, progress_interval: float = 2.0) -> Dict[str, Any]:
    results = {}
    target_items = list(target_funcs.items())
    total = len(src_funcs)
    processed = 0
    start_time = time.time()
    last_print = start_time

    for source_name, s in src_funcs.items():
        candidates = []
        for t_name, t in target_items:
            # Size similarity
            size_sim = 1 - abs(s["size"] - t["size"]) / max(s["size"], t["size"])
            if size_sim < (1 - size_tol):
                continue
            # Mnemonic similarity
            mnem_sim = multiset_jaccard(s["mnems"], t["mnems"])
            if mnem_sim < jaccard_threshold:
                continue
            # Sequence similarity
            seq_sim = sequence_similarity(s["norm"], t["norm"])
            # Calls similarity – use early calls for short functions
            use_partial = len(s["norm"]) < 30 or len(t["norm"]) < 30
            if use_partial:
                call_sim = multiset_jaccard(s["early_calls"], t["early_calls"])
            else:
                call_sim = multiset_jaccard(s["calls"], t["calls"])
            # Weighted score: sequence dominates
            score = (0.7 * seq_sim + 0.15 * mnem_sim + 0.10 * call_sim + 0.05 * size_sim)
            candidates.append({
                "target": t_name,
                "score": score,
                "seq": seq_sim,
                "mnemonic": mnem_sim,
                "calls": call_sim,
                "size": size_sim
            })
        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        if candidates:
            results[source_name] = {
                "best_match": candidates[0]["target"],
                "score": candidates[0]["score"],
                "top_candidates": candidates[:top_k]
            }
        else:
            results[source_name] = {"best_match": None, "score": 0}
            logger.info(f"No match found for {source_name} (size=0x{s['size']:x})")

        processed += 1
        if progress_interval > 0:
            now = time.time()
            if now - last_print >= progress_interval:
                elapsed = now - start_time
                avg = elapsed / processed
                eta = (total - processed) * avg
                eta_str = format_time(eta)
                logger.info(f"Mapping: {processed}/{total} {progress_bar(50, processed/total)} ETA: {eta_str}")
                last_print = now

    if progress_interval > 0 and processed > 0:
        elapsed = time.time() - start_time
        avg = elapsed / processed
        eta = (total - processed) * avg
        eta_str = format_time(eta)
        logger.info(f"Mapping: {processed}/{total} {progress_bar(50, processed/total)} ETA: {eta_str}")

    return results












# =====================================================================================================================

def main():
    parser = argparse.ArgumentParser(description="Function mapper using config file")
    parser.add_argument('--config', default='function_mapper_config.json',
                        help='Path to JSON configuration file (default: function_mapper_config.json)')
    parser.add_argument('-L', '--log-level', default='info',
                        choices=['debug', 'info', 'warn', 'error'],
                        help='Set logging level (default: info)')
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level,
                        format='[%(levelname)s] %(message)s')
    global logger
    logger = logging.getLogger(__name__)

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file '{config_path}' not found.")
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON config: {e}")
        sys.exit(1)

    required = ['source_symbols', 'source_binary', 'target_symbols', 'target_binary']
    for key in required:
        if key not in config:
            logger.error(f"Missing required key '{key}' in config file.")
            sys.exit(1)

    src_sym_file = config['source_symbols']
    src_bin = config['source_binary']
    target_sym_file = config['target_symbols']
    target_bin = config['target_binary']
    output_file = config.get('output', 'mapping.json')
    start_with = config.get('start_with')
    min_size = config.get('min_size', 0)
    max_instr = config.get('max_instr')
    no_cache = config.get('no_cache', False)

    for file in [src_sym_file, src_bin, target_sym_file, target_bin]:
        if not Path(file).exists():
            logger.error(f"File not found: {file}")
            sys.exit(1)

    logger.info("Analyzing source symbols...")
    src_funcs_cnt, src_labels_cnt, src_objs_cnt, src_unmatched = analyze_symbols_file(
        src_sym_file, log_debug=(log_level <= logging.DEBUG)
    )
    logger.info(f"Source: functions={src_funcs_cnt}, labels={src_labels_cnt}, "
                f"objects={src_objs_cnt}, unmatched={src_unmatched}")

    logger.info("Analyzing target symbols...")
    target_funcs_cnt, target_labels_cnt, target_objs_cnt, target_unmatched = analyze_symbols_file(
        target_sym_file, log_debug=(log_level <= logging.DEBUG)
    )
    logger.info(f"Target: functions={target_funcs_cnt}, labels={target_labels_cnt}, "
                f"objects={target_objs_cnt}, unmatched={target_unmatched}")

    logger.info("Parsing function symbols...")
    src_syms = parse_symbols(src_sym_file)
    target_syms = parse_symbols(target_sym_file)

    src_syms = fill_missing_sizes(src_syms)
    target_syms = fill_missing_sizes(target_syms)

    if start_with:
        src_syms = {k: v for k, v in src_syms.items() if k.startswith(start_with)}
        logger.info(f"Filtered source functions with prefix '{start_with}': {len(src_syms)}")
    if min_size:
        src_syms = {k: v for k, v in src_syms.items() if v[1] >= min_size}
        logger.info(f"Filtered source functions with size >= {min_size}: {len(src_syms)}")

    logger.info(f"Source functions to map: {len(src_syms)}")
    logger.info(f"Target functions available: {len(target_syms)}")

    logger.info("Extracting source functions (disassembly)...")
    src_funcs = extract_functions(src_bin, src_syms, max_instr, not no_cache)

    logger.info("Extracting target functions (disassembly)...")
    target_funcs = extract_functions(target_bin, target_syms, max_instr, not no_cache)

    logger.info(f"Successfully extracted source functions: {len(src_funcs)}")
    logger.info(f"Successfully extracted target functions: {len(target_funcs)}")

    logger.info("Mapping...")
    mapping = map_functions(src_funcs, target_funcs)

    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)

    logger.info(f"Done: {output_file}")


if __name__ == '__main__':
    main()
