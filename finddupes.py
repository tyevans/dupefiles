#!/usr/bin/env python3

import argparse
import hashlib
import os
import fnmatch

from logging import getLogger
from multiprocessing.pool import ThreadPool

logger = getLogger(__name__)

DEFAULT_MIN_SIZE = 0
DEFAULT_MAX_SIZE = 1000000000


def options():  # pragma: no cover
    """ Parse command line arguments and return them

    :return: Namespace of application arguments and options
    """
    parser = argparse.ArgumentParser(
        description='Search for duplicated files across a directory structure.')
    parser.add_argument('--min-size', type=int, default=DEFAULT_MIN_SIZE,
                        help='Minimum file size in bytes (files smaller than this will be skipped)')
    parser.add_argument('--max-size', type=int, default=DEFAULT_MAX_SIZE,
                        help='Maximum file size in bytes (files larger than this will be skipped)')
    parser.add_argument('--name', default=None, nargs='+',
                        help='Filename glob. Only files matching this pattern will be considered.')
    parser.add_argument('--exclude', default=None, nargs='+',
                        help='Filename glob of directories or files to exclude')
    parser.add_argument('--followlinks', action="store_true", default=False,
                        help='Follow symlinks')
    parser.add_argument('--json', action="store_true", default=False,
                        help='Use JSON Output')
    parser.add_argument('--workers', type=int, default=16,
                        help='Number of worker threads to spawn')
    parser.add_argument('path', type=str, help='The directory path to search')
    return parser.parse_args()


def walk(path, followlinks=False, globs=None, exclusion_globs=None):
    """ Iterates over `path` and yields os.DirEntry objects for every file in the path.

    this is similar to:

    for root, dirs, files in os.walk(path):
        os.walk

    :param followlinks: If True, traverse symlinked directories (default: False)
    :param path: A directory string (e.g.: '/home/tevans/' or '../..')
    :returns: Yields an `os.DirEntry` instance for every file in path.
    """
    try:
        path_iter = os.scandir(path)
    except OSError as exc:
        logger.warning(f"Skipping Directory (OSError): {path}")
        return

    walk_dirs = []
    with path_iter:
        for entry in path_iter:
            if exclusion_globs and any(
                    fnmatch.fnmatch(entry.name, glob) for glob in
                    exclusion_globs):
                continue
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
            if entry.is_file():
                if not globs or any(
                        fnmatch.fnmatch(entry.name, glob) for glob in globs):
                    yield entry

    for directory in walk_dirs:
        for entry in walk(directory, followlinks=followlinks, globs=globs,
                          exclusion_globs=exclusion_globs):
            yield entry


def read_chunks(file_object, chunk_size=1024):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 1k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def hash_key(hashfunc=hashlib.md5):
    """ Returns a function that uses `hashfunc` to hash files and return the generated hash in bytes.

    If the file cannot be hashed (due to permissions errors, for example), returns `None`

    :param hashfunc: hash function to use (default: hashlib.md5)
    :return: hashing function
    """

    def _(_file):
        try:
            with open(_file.path, 'rb') as fd:
                _h = hashfunc()
                for chunk in read_chunks(fd, chunk_size=1024*1024*10):
                    _h.update(chunk)
                return _h.digest()
        except (OSError, PermissionError):
            logger.warning(
                f"Skipping File (Could Not Open To Read): {_file.path}")

    return _


def size_key(min_size=DEFAULT_MIN_SIZE, max_size=DEFAULT_MAX_SIZE):
    """ Returns a function that stats a file and returns its size.

    If size is less than `min_size` or greater than `max_size` returns `None`

    :param min_size: minimum file size in bytes
    :param max_size: maximum file size in bytes
    :return: `int` or `None`
    """
    def _(_file):
        size = _file.stat().st_size
        if min_size <= size <= max_size:
            return size

    return _


def group_by_key(fileset, keyfunc, min_group_size=2, workers=16):
    """ Groups the provided os.DirEntry instances by the key generated by passing each to `keyfunc`.

    If `keyfunc(entry)` returns None, the item is filtered from the return.

    :param fileset: A list of os.DirEntry instances to group.
    :param keyfunc: A function that takes an os.DirEntry as its sole argument and returns a hashable key.
    :param min_group_size: minimum number of entries a group needs to be returned (default: 2)
    :return: A list of lists of grouped os.DirEntry instances.
    """
    pool = ThreadPool(workers)

    def evaluate(entry):
        return keyfunc(entry), entry

    keyed_fileset = pool.map(evaluate, fileset)
    files_by_key = {}
    for key, entry in keyed_fileset:
        if key is None:
            continue
        files_by_key.setdefault(key, []).append(entry)

    return [group for group in files_by_key.values() if
            len(group) >= min_group_size]


def group_by_hash(fileset, hashfunc=hashlib.md5, min_group_size=2, workers=16):
    """ Takes a list of os.DirEntry instances (`fileset`) and an optional hash function.

    This function groups the os.DirEntry instances in the `fileset` list by hash (using `hashfunc`)
    and returns lists of os.DirEntry instances, grouped by hash.

    Only groups larger than `min_group_size` are returned.

    :param fileset: A list of os.DirEntry instances to group.
    :param hashfunc: hash function to use (default: hashlib.md5)
    :param min_group_size: minimum number of entries a group needs to be returned (default: 2)
    :return: lists of os.DirEntry instances grouped by hash value.
    """
    return group_by_key(fileset, hash_key(hashfunc=hashfunc),
                        min_group_size=min_group_size, workers=workers)


def group_by_size(fileset, min_size=DEFAULT_MIN_SIZE, max_size=DEFAULT_MAX_SIZE,
                  min_group_size=2, workers=16):
    """ Takes a list of os.DirEntry instances (`fileset`) and optional file size bounds.

    This function groups the os.DirEntry instances in the `fileset` list by size
    and returns lists of os.DirEntry instances, grouped by their file size.

    Only groups larger than `min_group_size` are returned.

    :param fileset: A list of os.DirEntry instances to group.
    :param min_size: minimum file size in bytes (files smaller than this will be ignored)
    :param max_size: maximum file size in bytes (files larger than this will be ignored)
    :param min_group_size: minimum number of entries a group needs to be returned (default: 2)
    :return: lists of os.DirEntry instances grouped by size.
    """
    return group_by_key(fileset, size_key(min_size=min_size, max_size=max_size),
                        min_group_size=min_group_size, workers=workers)


def find_dupe_files(path, globs=None, exclusion_globs=None,
                    min_size=DEFAULT_MIN_SIZE,
                    max_size=DEFAULT_MAX_SIZE, min_group_size=2, workers=16):
    """ Walks `path` and returns a list of duplicated files in it.

    :param path: path string that we want to search.
    :param globs: A list of glob strings used to filter the fileset.
    :param exclusion_globs: Files matching globs in this list will not be evaluated.
    :param min_size: minimum file size in bytes (files smaller than this will be ignored)
    :param max_size: maximum file size in bytes (files larger than this will be ignored)
    :param min_group_size: minimum number of entries a group needs to be returned (default: 2)
    :return: lists of os.DirEntry instances pointing to duplicated files.
    """
    dir_iter = walk(path, globs=globs, exclusion_globs=exclusion_globs)
    dupes = []
    for group in group_by_size(dir_iter, min_size=min_size, max_size=max_size,
                               min_group_size=min_group_size, workers=workers):
        dupes.extend(group_by_hash(group, min_group_size=min_group_size, workers=workers))
    return dupes


if __name__ == "__main__":
    import json

    args = options()
    dupes = find_dupe_files(args.path, args.name, args.exclude, args.min_size,
                            args.max_size, workers=args.workers)
    if args.json:
        print(json.dumps([[entry.path for entry in d] for d in dupes]))
    else:
        for group in dupes:
            for entry in group:
                print(entry.path)
            print()
