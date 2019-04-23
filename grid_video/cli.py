import os
import sys
import argparse
import moviepy.editor as mpy
from grid_video.audio import cut_silence
from grid_video.grid import make_grid_vid


def trim_clips():
    parser = argparse.ArgumentParser(description="")
    file_list = sys.argv[1:]
    if len(file_list) == 0:
        print("No files specified")
        sys.exit(1)
    elif len(file_list) == 1:
        prefix = "processed_"
    else:
        os.makedirs("new_processed_clips", exist_ok=True)
        prefix = "new_processed_clips/"

    print(file_list)

    for fname in file_list:
        clip = mpy.VideoFileClip(fname)
        result = cut_silence(clip)
        result.write_videofile(prefix + os.path.split(fname)[1])


def main():
    parser = argparse.ArgumentParser(description="Grid music video making thing")
    parser.add_argument('-i', '--input', help='Midi input file')
    parser.add_argument('-s', '--soundbank', help='Directory containing soundbank')
    parser.add_argument('-o', '--output', help='Output file name')
    parser.add_argument('-t', '--coverage_test', help="Only test if soundbank covers midi file")

    args = parser.parse_args()

    if args.coverage_test:
        raise NotImplementedError("Sorry")
    make_grid_vid(args.input, args.soundbank, args.output)
