import moviepy.editor as mpy
import glob
import mido
import os
import sys
from math import ceil

from grid_video.core import Note, Track
from grid_video.parser import parse_midi
from grid_video.utils import note_name, note_code


def make_track_clip(note_bank, track, autoshift=False) -> mpy.VideoClip:
    clip_array = []
    silence = note_bank[-1]

    bank_min, bank_max = soundbank_boundaries(note_bank)
    if autoshift and (track.lowest_note < bank_min or track.highest_note > bank_max):
        if bank_min.code - track.lowest_note.code >= track.highest_note.code - bank_max.code:
            octave_offset = (bank_min.code - track.lowest_note.code) // 12 + 1
            print("shifting track one octave up")
        else:
            octave_offset = ((track.highest_note.code - bank_max.code) // 12 + 1) * -1
            print("shifting track one octave down")

        oldtrack = track
        track = Track([n.shift(octave_offset * 12) for n in track])

    for note in track:
        note_clip = note_bank.get(note.code)
        if note_clip is None:
            print(f'note not found: {note}')
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


def make_simple_soundbank(directory, begin_offset=0):
    """makes soundbank based on given directory, assuming that each file name is <soundname>.mp4"""
    result = {}

    for fname in glob.glob(os.path.join(directory, "*")):
        try:
            no_dir_name = os.path.basename(fname)
            name = no_dir_name[:no_dir_name.find('.')]
            code = note_code(name)
            result[code] = mpy.VideoFileClip(fname, target_resolution=(1080//5, 1920//5)).subclip(begin_offset)
        except ValueError:
            print(f"Couldn't parse file {fname}")

    
    return result


def soundbank_boundaries(soundbank):
    min_note = None
    for k in soundbank.keys():
        if k != -1 and (min_note is None or k < min_note):
            min_note = k
    max_note = max(soundbank.keys())
    return Note(min_note, 0), Note(max_note, 0)



def make_grid_vid(midi_fname, soundbank_dir, autoshift, output=None, offset=0):
    soundbank = make_simple_soundbank(soundbank_dir, begin_offset=offset)
    silence = soundbank[-1]
    mfile = mido.MidiFile(midi_fname)
    parsed = parse_midi(mfile)
    clips = []
    row = []
    track_counter = 0
    for i in parsed:
        for t in i:
            track_counter += 1
    columns = ceil(track_counter ** 0.5)
    counter = 0
    for i_midi, midi_track in enumerate(parsed):
        for i_track, t in enumerate(midi_track):
            if not t:
                continue
            counter += 1
            clip = make_track_clip(soundbank, t, autoshift=autoshift)
            # clip.write_videofile(f'tmp/track{i_midi}-{i_track}.mp4')
            row.append(clip)
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
        final.write_videofile(output, threads=10)
