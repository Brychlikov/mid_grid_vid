import os
import sys
import argparse
import moviepy.editor as mpy
import mido
import glob
import aubio
from grid_video.audio import cut_silence
# from grid_video.grid import make_grid_vid
from grid_video.my_grid import make_grid_vid
from grid_video.parser import parse_midi
from grid_video.core import Track, Note
from grid_video.utils import note_code, note_name


def trim_clips(input, output):
    if type(input) == list and len(input) == 1:
        input = input[0]
    print('branch')
    if type(input) == list:
        print(1)
        file_list = input
    elif os.path.isdir(input):
        print(2)
        file_list = glob.glob(os.path.join(input, '*'))
    elif os.path.isfile(input):  # Should be a single file right there
        print(3)
        clip = mpy.VideoFileClip(input)
        cut_silence(clip).write_videofile(output)
        return
    else:
        raise ValueError("Unrecognized argument: " + input)

    # prepare output dir
    os.makedirs(output, exist_ok=True)

    for fname in file_list:
        clip = mpy.VideoFileClip(fname)
        result = cut_silence(clip)
        result.write_videofile(os.path.join(output, os.path.basename(fname)))


def midi_note_pool(midi_fname):
    parsed = parse_midi(mido.MidiFile(midi_fname))
    print("")
    for mid_track in parsed:
        pool = set()
        for t in mid_track:
            pool |= t.note_pool
        l = sorted(list(pool), key=lambda i: i.code)
        print(" ".join([n.name for n in l]))
        print()
    return pool


def test_pitch(fname):
    hop_size = 8192
    win_size = 2 ** 14
    s = aubio.source(fname, 0, hop_size)
    pitch_o = aubio.pitch('yin', win_size, hop_size, samplerate=s.samplerate)
    pitch_o.set_unit('midi')
    sample, read = s()
    res = pitch_o(sample)[0]
    print(res)
    



def main():
    parser = argparse.ArgumentParser(description="Grid music video making thing")
    parser.add_argument('-i', '--input', help='Midi input file')
    parser.add_argument('-s', '--soundbank', help='Directory containing soundbank')
    parser.add_argument('-o', '--output', help='Output file/dir name')
    parser.add_argument('-t', '--coverage_test', help="Only test if soundbank covers midi file", action='store_true')

    subs = parser.add_subparsers(dest='command')
    trim_parser = subs.add_parser("trim", help="Automaticly trim clips to correct length")
    trim_parser.add_argument('fname', nargs='+', help="File or dir to trim")
    trim_parser.add_argument('-o', '--output', help='Output file/dir name')

    pitch_parser = subs.add_parser('pitch')
    pitch_parser.add_argument('fname', nargs='+', help="File(s) or dir to pitch test")

    cover_parser = subs.add_parser("coverage", help="Check how many notes you need for the clip")
    cover_parser.add_argument('-v', '--verbose', action='store_true', help="More detailed output")

    make_parser = subs.add_parser("make", help="Flagship feature")
    make_parser.add_argument('--no-autoshift', action='store_true')

    args = parser.parse_args()

    if args.command == 'coverage':
        midi_note_pool(args.input)
    
    elif args.command == 'make':
        make_grid_vid(args.input, args.soundbank, not args.no_autoshift, args.output, offset=0.02)

    elif args.command == 'trim':
        trim_clips(args.fname, args.output)
    elif args.command == 'pitch':
        test_pitch(args.fname)


if __name__ == "__main__":
    main()
