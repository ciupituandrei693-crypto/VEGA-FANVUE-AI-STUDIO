"""VEGA offline restore. ALWAYS STOP VEGA FIRST. Never overwrite current data."""
import argparse
from pathlib import Path
from vega.backup import restore_offline

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Restore VEGA private backup into EMPTY directory; VEGA MUST be stopped.')
    parser.add_argument('archive',type=Path)
    parser.add_argument('--to',required=True,type=Path,help='Destination must be empty')
    parser.add_argument('--confirm',action='store_true',help='Actually extract (default dry-run)')
    args=parser.parse_args()
    print(restore_offline(args.archive,args.to,args.confirm))
