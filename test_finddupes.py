from unittest import TestCase

from finddupes import find_dupe_files, group_by_size, walk, group_by_hash

# def group_by_size(fileset, min_size=DEFAULT_MIN_SIZE, max_size=DEFAULT_MAX_SIZE):
#     files_by_size = {}
#     for entry in fileset:
#         size = entry.stat().st_size
#         if min_size <= size <= max_size:
#             files_by_size.setdefault(size, []).append(entry)
#     return [group for group in files_by_size.values() if len(group) > 1]

TEST_DATA_DIR = './test_data'


class TestWalk(TestCase):

    def test_walk_invalid_dir(self):
        self.assertEqual([], list(walk('doesnt/exist/')))

    def test_walk_file(self):
        self.assertEqual([], list(walk('requirements.txt')))


class TestGroupBySize(TestCase):

    def test_group_files(self):
        file_iter = walk(TEST_DATA_DIR, "*.txt")
        groups = group_by_size(file_iter)
        self.assertEqual(3, len(groups))
        for group in groups:
            self.assertTrue(group[0].name in ['12bytes.txt', '8bytes.txt', 'empty.txt'])
            self.assertEqual(4, len(group))

    def test_group_size_1(self):
        file_iter = walk(TEST_DATA_DIR)
        groups = group_by_size(file_iter, min_group_size=1)
        self.assertEqual(4, len(groups))
        for group in groups:
            if group[0].name in ['12bytes.txt', '8bytes.txt', 'empty.txt']:
                self.assertEqual(4, len(group))
            elif group[0].name == 'unique.gif':
                self.assertEqual(1, len(group))


class TestGroupByHash(TestCase):

    def test_group_files(self):
        file_iter = walk(TEST_DATA_DIR, "*.txt")
        groups = group_by_hash(file_iter)
        self.assertEqual(3, len(groups))
        for group in groups:
            self.assertTrue(group[0].name in ['12bytes.txt', '8bytes.txt', 'empty.txt'])
            self.assertEqual(4, len(group))


class TestFindDupes(TestCase):

    def test_filter_empty_files(self):
        groups = find_dupe_files(TEST_DATA_DIR, min_size=1)
        for group in groups:
            self.assertFalse(group[0].name == "empty.txt")

    def test_only_empty_files(self):
        groups = find_dupe_files(TEST_DATA_DIR, max_size=0)
        self.assertEqual(1, len(groups))
        self.assertEqual(4, len(groups[0]))
        self.assertEqual("empty.txt", groups[0][0].name)

    def test_files_smaller_than_8_bytes(self):
        groups = find_dupe_files(TEST_DATA_DIR, max_size=7)
        self.assertEqual(1, len(groups))
        self.assertEqual(4, len(groups[0]))
        self.assertEqual("empty.txt", groups[0][0].name)

    def test_files_larger_than_8_bytes(self):
        groups = find_dupe_files(TEST_DATA_DIR, min_size=9)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 4)
        self.assertEqual(groups[0][0].name, "12bytes.txt")

    def test_files_8_bytes_or_larger(self):
        groups = find_dupe_files(TEST_DATA_DIR, min_size=8)
        self.assertEqual(len(groups), 2)
        for group in groups:
            self.assertEqual(len(group), 4)
            self.assertTrue(group[0].name in ["8bytes.txt", "12bytes.txt"])

    def test_glob(self):
        groups = find_dupe_files(TEST_DATA_DIR, globs=['*.gif'], min_group_size=1)
        self.assertEqual(len(groups), 1)
        for group in groups:
            self.assertEqual(len(group), 1)
            self.assertEqual(group[0].name, 'unique.gif')

    def test_glob_and_size(self):
        groups = find_dupe_files(TEST_DATA_DIR, globs=['*.txt'], min_size=7, max_size=9)
        self.assertEqual(len(groups), 1)
        for group in groups:
            self.assertEqual(len(group), 4)
            self.assertEqual(group[0].name, '8bytes.txt')

    def test_exclusion_glob(self):
        groups = find_dupe_files(TEST_DATA_DIR, exclusion_globs=['*.txt'], min_group_size=1)
        self.assertEqual(len(groups), 1)
        for group in groups:
            self.assertEqual(len(group), 1)
            self.assertEqual(group[0].name, 'unique.gif')
