import time
from argparse import ArgumentParser
import subprocess
import re
from dataclasses import dataclass
from multiprocessing import Pool

parser = ArgumentParser()

parser.add_argument('mirrorlist', help='Path to mirror list')

args = parser.parse_args()

mirrors = []
with open(args.mirrorlist, 'r') as f:
    for line in f:
        line = line.strip()
        if line == '' or line.startswith('#'):
            continue
        

        parts = tuple(p.strip() for p in line.split('='))
        if len(parts) != 2:
            print('Warning: could not parse line', line)
            continue
        mirrors.append(parts[1])

def parse_mirror(mirror):
    start = mirror.find('//')
    if start == -1:
        print('Warning: could not parse mirror', mirror)
        return None
    # Skip the slashes
    start += 2

    # Find the end of the host
    end = mirror[start:].find('/')
    if end == -1:
        print ('Warning: could not parse mirror', mirror)
        return None

    end += start

    return mirror[start:end]

hosts = [parse_mirror(mirror) for mirror in mirrors]


@dataclass
class PingStats:
    host: str
    min: float
    avg: float
    max: float
    mdev: float


# 8.081/8.346/8.612/0.265 ms
# rtt min/avg/max/mdev = 33.760/35.350/40.101/1.699 ms
PARTS_REGEX = re.compile('rtt min/avg/max/mdev = ([0-9]+\\.[0-9]+)/([0-9]+\\.[0-9]+)/([0-9]+\\.[0-9]+)/([0-9]+\\.[0-9]+)')

def parse_ping_output(s):
    last_line = [line for line in s.decode('utf-8').split('\n') if line != ''][-1]
    match = PARTS_REGEX.match(last_line)
    if match is None:
        print('Warning: failed to parse ping output', last_line)
        return None
    else:
        return match.groups()


def ping_host(host):
    cmd = ['ping', '-c', '10', '-w', '60', host]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print('Warning:', ' '.join(cmd), 'failed with return code', result.returncode)
        print(result.stdout)
        print(result.stderr)
        return None

    ping_result = parse_ping_output(result.stdout)
    if ping_result is None:
        return None

    min, avg, max, mdev = ping_result
    return PingStats(host, min, avg, max, mdev)

start_time = time.time()

ping_stats = []
with Pool(32) as pool:
    for stats in pool.imap_unordered(ping_host, hosts):
        if stats is None:
            continue
        ping_stats.append(stats)


from pprint import pprint
pprint(ping_stats)

end_time = time.time()

print(f'Completed in {end_time - start_time} s')
