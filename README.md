#finddupes

Walk a path and list all duplicate files.

    python finddupes.py -h
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
