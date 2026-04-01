import csv
import re

def parse_splits(splits_path):
    sections = []
    with open(splits_path, 'r') as f:
        for line in f:
            line = line.strip()

            # match splits: .text start:0x800034A0 end:0x800502a4
            m = re.match(
                r'^\.(\w+)\s+start:0x([0-9A-Fa-f]+)\s+end:0x([0-9A-Fa-f]+)',
                line
            )
            if m:
                section = f'.{m.group(1)}'
                start = int(m.group(2), 16)
                end = int(m.group(3), 16)
                sections.append((section, start, end))

    return sections

def find_section(addr, sections):
    for section, start, end in sections:
        if start <= addr < end:
            return section
    return None

def main():
    sections = parse_splits('config/G4ME69/splits.txt')
    with open('functions.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        with open('symbols.txt', 'w') as out:
            for row in reader:
                if len(row) < 2:
                    continue
                name = row[0].strip()
                addr_str = row[1].strip()
                if not addr_str.startswith('0x'):
                    addr = int(addr_str, 16)
                else:
                    addr = int(addr_str, 16)
                section = find_section(addr, sections)
                if section is None:
                    print(f"warning: {name} at 0x{addr:08X} not in any section; skipping")
                    continue
                out.write(f'{name} = {section}:0x{addr:08X}; // type:function\n')

if __name__ == '__main__':
    main()
