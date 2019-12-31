import shutil
import glob
import threading
import os
import numpy as np
import time
from utils import split_path, note_name
import pygame
from pygame import mixer
from pygame.mixer import Sound
from new_audio_utils import AudioClip



volume = 0.1     # range [0.0, 1.0]
SAMPLING_RATE = 44100       # sampling rate, Hz, must be integer
duration = 1.0   # in seconds, may be float
f = 220.0        # sine frequency, Hz, may be float

mixer.init(frequency=SAMPLING_RATE)


def make_sine(f, duration):
    samples = (np.sin(np.pi*np.arange(SAMPLING_RATE*duration)*f/SAMPLING_RATE)).astype(np.float32)
    final_int = (samples * (2 ** 15 - 1)).astype(np.int16)
    s = Sound(final_int)
    return s

def background_two_sounds(s1, s2, t1=None, t2=None):
    # WARNING: times are twice too short
    if t1 is not None:
        n1 = int(SAMPLING_RATE * t1 / 1000)
        b1 = s1.get_raw()[:n1]
        print(len(b1))
    else:
        b1 = s1.get_raw()

    if t2 is not None:
        n2 = int(SAMPLING_RATE * t2 / 1000)
        b2 = s2.get_raw()[:n2]
    else:
        b1 = s2.get_raw()

    s = Sound(b1 + b2)
    return s


def midi_to_hz(note):
    a4_midi= 69  # Nice.
    a4_hz = 440

    return 2 ** ((note - a4_midi)/12) * a4_hz


def get_pitch_from_user(fname, start_from=48):
    """Interactively plays the clip with path fname with different pitches, asking user to specify the correct one"""
    note = start_from 
    sound_pitched = Sound(fname)
    while True:
        sound_ref = make_sine(midi_to_hz(note), duration=10)
        s = background_two_sounds(sound_pitched, sound_ref, t1=7000, t2 = 4000)
        s.play(loops=-1)
        print("Current note:", note)
        ans = input("Lower: j / -<num>\t Higher: k / <num> Good: y\n")
        if ans == 'y':
            s.stop()
            return note
        elif ans == 'j':
            note -= 1
        elif ans == 'k':
            note += 1
        else:
            try:
                note += int(ans)
            except:
                print("You somehow failed to answer correctly")
        s.stop()

        



def process_file(fname, start_from=48, redo=False):
    """Interactively query the user for pitch. Returns the pitch specified by user"""
    directory, basename, ext = split_path(fname)

    ac = AudioClip(fname, cleanup=True)
    pitch = get_pitch_from_user(ac.audio_path, start_from)  # pitch is a midi value
    
    new_fname = os.path.join(directory, f"{note_name(pitch)}{ext}")
    shutil.copy(fname, new_fname)
    print(f"Copied {fname} to {new_fname}\n")
    return pitch

def process_soundband(directory):
    prev = None
    for fname in sorted(glob.glob(os.path.join(directory, "*"))):
        print("Processing", fname)
        if prev is not None:
            prev = process_file(fname, prev + 1)
        else:
            prev = process_file(fname)


# s1 = Sound('./soundbanks/guitar/raw_audio/a3.wav')
# s2 = make_sine(220, 10)

# chosen = get_pitch_from_user('./soundbanks/guitar/raw_audio/a3.wav')
process_soundband('./soundbanks/voice')

