import json
import re
import requests
from subprocess import run
from collections import defaultdict
import runpy
import tempfile

data = json.loads(
    requests.get('https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json').text)
flutter_versions = data['releases']

# replace these
# git clone flutter repo (git@github.com:flutter/flutter.git) to your flutter path
flutter_repo_path = '../../../../flutterRoot/flutter'
# git clone flutter engine repo (git@github.com:flutter/engine.git) to your flutter engine path
engine_repo_path = '../../../../flutterRoot/engine'
# git clone dart sdk repo ( git@github.com:dart-lang/sdk.git) to your dart sdk path
dart_repo_path = '../../../../flutterRoot/dart-sdk'

def make_cache(fn):
    d = {}

    def caching_fn(x):
        if x not in d:
            d[x] = fn(x)
        return d[x]

    return caching_fn


def get_engine_version(flutter_commit):
    p = run(['git', 'show', flutter_commit + ':bin/internal/engine.version'], check=True, capture_output=True,
            cwd=flutter_repo_path)
    return p.stdout.decode().strip()


def get_dart_version(engine_commit):
    contents = run(['git', 'show', engine_commit + ':DEPS'], check=True, capture_output=True,
                   cwd=engine_repo_path).stdout
    m = re.search(r"'dart_revision': '([a-fA-F0-9]+)'", contents.decode())
    return m.group(1)

#create temp file, set delete false, or is will be permission deny.
sv_template_file = tempfile.NamedTemporaryFile(delete=False)
sv_template_file.write('{{SNAPSHOT_HASH}}'.encode())
sv_template_file.flush()
sv_out_file = tempfile.NamedTemporaryFile(delete=False)

def get_snapshot_hash(dart_commit):
    run(['git', 'checkout', dart_commit], check=True, cwd=dart_repo_path)
    sv_out_file.seek(0)
    run(['python', 'tools/make_version.py', '--input=' + sv_template_file.name, '--output=' + sv_out_file.name], check=True, cwd=dart_repo_path)
    return sv_out_file.read().decode()


get_engine_version = make_cache(get_engine_version)
get_dart_version = make_cache(get_dart_version)
get_snapshot_hash = make_cache(get_snapshot_hash)

# get_engine_version('master')
# get_dart_version('11d756a62ed0ddf87a9ce20b219b55300ec6b67d')
# get_snapshot_version('06536d68ca0f27528b0bf729f4b8d673ed14beda')


print('| Release date | Channel | Version | Commit | Engine commit | Dart SDK commit | Snapshot version |')
print('| ------------ | ------- | ------- | ------ | ------------- | --------------- | ---------------- |')
for v in sorted(flutter_versions, key=lambda x: x['release_date'], reverse=True):
    if v['channel'] not in {'stable', 'beta'}: continue
    engine_commit = get_engine_version(v['hash'])
    dart_commit = get_dart_version(engine_commit)
    snapshot_hash = get_snapshot_hash(dart_commit)
    print(f"| {v['release_date'][:10]} | {v['channel']} | {v['version']} | {v['hash']} | {engine_commit} | {dart_commit} | {snapshot_hash} |")
