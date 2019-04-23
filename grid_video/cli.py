import os
import sys
import argparse
import moviepy.editor as mpy
import mido
from grid_video.audio import cut_silence
from grid_video.grid import make_grid_vid
from grid_video.parser import parse_midi
from grid_video.core import Track, Note
from grid_video.utils import note_code, note_name


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


def midi_note_pool(midi_fname):
    parsed = parse_midi(mido.MidiFile(midi_fname))
    for mid_track in parsed:
        pool = set()
        for t in mid_track:
            pool |= t.note_pool
        l = sorted(list(pool), key=lambda i: i.code)
        print(" ".join([n.name for n in l]))
        print()
    return pool


def main():
    parser = argparse.ArgumentParser(description="Grid music video making thing")
    parser.add_argument('-i', '--input', help='Midi input file')
    parser.add_argument('-s', '--soundbank', help='Directory containing soundbank')
    parser.add_argument('-o', '--output', help='Output file name')
    parser.add_argument('-t', '--coverage_test', help="Only test if soundbank covers midi file", action='store_true')

    args = parser.parse_args()

    if args.coverage_test:
        midi_note_pool(args.input)
    else:
        make_grid_vid(args.input, args.soundbank, args.output)
