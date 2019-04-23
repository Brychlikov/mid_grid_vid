import moviepy.editor as mpy
import glob
import mido
import os
import sys
from math import ceil

from grid_video.core import Note
from grid_video.parser import parse_midi
from grid_video.utils import note_name, note_code


def make_track_clip(note_bank, track) -> mpy.VideoClip:
    clip_array = []
    silence = note_bank[-1]
    for note in track:
        note_clip = note_bank.get(note.code)
        if note_clip is None:
            print(f'note not found: {note.code}')
            note_clip = silence

        if note.length <= note_clip.duration:
            clip_array.append(note_clip.subclip(0, note.length))
        
        else:
            clip_array.append(note_clip)
            remaining_duration = note.length - note_clip.duration
            while remaining_duration > silence.duration:
                clip_array.append(silence)
                remaining_duration -= silence.duration
            clip_array.append(silence.subclip(0, remaining_duration))

    return mpy.concatenate_videoclips(clip_array)


def make_simple_soundbank(directory):
    """makes soundbank based on given directory, assuming that each file name is <soundname>.mp4"""
    result = {}

    for fname in glob.glob(os.path.join(directory, "*")):
        try:
            no_dir_name = os.path.basename(fname)
            name = no_dir_name[:no_dir_name.find('.')]
            code = note_code(name)
            result[code] = mpy.VideoFileClip(fname, target_resolution=(1080//5, 1920//5))
        except ValueError:
            print(f"Couldn't parse file {fname}")

    
    return result


def make_grid_vid(midi_fname, soundbank_dir, output=None):
    soundbank = make_simple_soundbank(soundbank_dir)
    silence = soundbank[-1]
    mfile = mido.MidiFile(midi_fname)
    parsed = parse_midi(mfile)
    clips = []
    row = []
    columns = ceil(len(parsed) ** 0.5)
    counter = 0
    for t in parsed:
        if not t:
            continue
        counter += 1
        row.append(make_track_clip(soundbank, t))
        if counter % columns == 0:
            clips.append(row)
            row = []
    if row:
        for i in range(columns - len(row)):
            row.append(silence)
        clips.append(row)

    final = mpy.clips_array(clips)
    if output is None:
        return final
    else:
        final.write_videofile(output)
