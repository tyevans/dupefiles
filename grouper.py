#!/usr/bin/env python3

import argparse
import hashlib
import os
import fnmatch

from logging import getLogger

logger = getLogger(__name__)

DEFAULT_MIN_SIZE = 0
DEFAULT_MAX_SIZE = 1000000000


def options():
    parser = argparse.ArgumentParser(description='Search for duplicated files across a directory structure.')
    parser.add_argument('--min-size', type=int, default=DEFAULT_MIN_SIZE,
                        help='Minimum file size in bytes (files smaller than this will be skipped)')
    parser.add_argument('--max-size', type=int, default=DEFAULT_MAX_SIZE,
                        help='Maximum file size in bytes (files larger than this will be skipped)')
    parser.add_argument('--name', default=None,
                        help='Filename glob. Only files matching this pattern will be considered.')
    parser.add_argument('--followlinks', action="store_true", default=False,
                        help='Follow symlinks')
    parser.add_argument('path', type=str, help='The directory path to search')
    return parser.parse_args()


def walk(path, glob=None, followlinks=False):
    try:
        path_iter = os.scandir(path)
    except OSError as exc:
        logger.warning(f"Skipping Directory (OSError): {path}")
        return

    walk_dirs = []
    with path_iter:
        for entry in path_iter:
            if entry.is_dir():
                if followlinks:
                    walk_into = True
                else:
                    try:
                        is_symlink = entry.is_symlink()
                    except OSError:
                        # If is_symlink() raises an OSError, consider that the
                        # entry is not a symbolic link, same behaviour than
                        # os.path.islink().
                        is_symlink = False
                    walk_into = not is_symlink

                if walk_into:
                    walk_dirs.append(entry.path)
            if entry.is_file() and (glob is None or fnmatch.fnmatch(entry.name, glob)):
                yield entry

    for directory in walk_dirs:
        for entry in walk(directory, glob):
            yield entry


def group_by_key(fileset, keyfunc, min_group_size=2):
    files_by_key = {}
    for entry in fileset:
        key = keyfunc(entry)
        if key is None:
            continue
        files_by_key.setdefault(key, []).append(entry)
    return [group for group in files_by_key.values() if len(group) >= min_group_size]


def group_by_hash(fileset, hashfunc=hashlib.md5, min_group_size=2):
    def key(_file):
        try:
            with open(_file.path, 'rb') as fd:
                # For particularly large files we should read in chunks and update the hash function.
                # For now lets just do it all in one shot.
                return hashfunc(fd.read()).digest()
        except OSError:
            logger.warning(f"Skipping File (Could Not Open To Read): {_file.path}")

    return group_by_key(fileset, key, min_group_size=min_group_size)


def group_by_size(fileset, min_size=DEFAULT_MIN_SIZE, max_size=DEFAULT_MAX_SIZE, min_group_size=2):
    def key(_file):
        size = _file.stat().st_size
        if min_size <= size <= max_size:
            return size

    return group_by_key(fileset, key, min_group_size=min_group_size)


def find_dupe_files(path, glob=None, min_size=DEFAULT_MIN_SIZE, max_size=DEFAULT_MAX_SIZE, min_group_size=2):
    return [group_by_hash(group, min_group_size=min_group_size) for group in
            group_by_size(walk(path, glob), min_size=min_size, max_size=max_size, min_group_size=min_group_size)]


if __name__ == "__main__":
    args = options()
    for group in find_dupe_files(args.path, args.name, args.min_size, args.max_size):
        for entry in group:
            print(entry.path)
        print()
