# finddupes 

Walk a path and list all duplicate files.

[![CircleCI](https://circleci.com/gh/tyevans/dupefiles.svg?style=svg)](https://circleci.com/gh/tyevans/dupefiles)

    usage: finddupes.py [-h] [--min-size MIN_SIZE] [--max-size MAX_SIZE]
                        [--name NAME] [--followlinks]
                        path
    
    Search for duplicated files across a directory structure.
    
    positional arguments:
      path                 The directory path to search
    
    optional arguments:
      -h, --help           show this help message and exit
      --min-size MIN_SIZE  Minimum file size in bytes (files smaller than this
                           will be skipped)
      --max-size MAX_SIZE  Maximum file size in bytes (files larger than this will
                           be skipped)
      --name NAME          Filename glob. Only files matching this pattern will be
                           considered.
      --followlinks        Follow symlinks


### Example Usage:
    
    python finddupes.py ./test_data
    ./test_data\12bytes.txt
    ./test_data\dir1\12bytes.txt
    ./test_data\dir1\folder\12bytes.txt
    ./test_data\dirb\12bytes.txt
    
    ./test_data\8bytes.txt
    ./test_data\dir1\8bytes.txt
    ./test_data\dir1\folder\8bytes.txt
    ./test_data\dirb\8bytes.txt
    
    ./test_data\empty.txt
    ./test_data\dir1\empty.txt
    ./test_data\dir1\folder\empty.txt
    ./test_data\dirb\empty.txt
