import moviepy.editor as mpy
import numpy as np
import matplotlib.pyplot as plt
import math

import sys
import os
import shutil


MIMC = 2 ** (1/12)  # The most important music constant


def make_freq_list():
    result = []
    base_octave = [261.626 * MIMC ** i for i in range(12)]
    for i in range(10):
        new_octave = [b * 2 ** (i-4) for b in base_octave]
        result.append(new_octave)
    return result

OCTAVE_FREQUENCIES = make_freq_list()
ACCURACY = 0.01

def name_note(freq):
    note_names = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'b', 'h']
    for i, octave in enumerate(OCTAVE_FREQUENCIES):
        for j, el in enumerate(octave):
            if abs(el - freq) / freq < ACCURACY:
                return str(i) + note_names[j]
    raise ValueError('Could not identify frequency')

for fname in sys.argv[0:]:
    # clip = mpy.VideoFileClip(fname)
    clip = mpy.VideoFileClip('/home/brych/PycharmProjects/0%ProgrammingSkills100%StackOverflowSkills/a4.mp4')
    sound_arr = clip.audio.to_soundarray()[:, 0]
    res = librosa.core.piptrack(sound_arr, sr=clip.audio.fps)


    sine = [math.cos(2 * math.pi * n) for n in range(10)]

    # fft = np.fft.fft(sound_arr)
    fft = np.fft.fft(sound_arr)

    # fft = np.fft.fftshift(fft)
    # p1 = 49636
    n = len(fft)
    p1 = np.argmax(abs(fft[:n//2]))
    f = 44100 * p1 / n
    try:
        name = name_note(f)
    except ValueError:
        print(f'could not identify note in file {fname}. Frequency calculated is {f}', file=sys.stderr)
        continue
    new_path = 'guitar/' + name + '.mp4'
    shutil.copyfile(fname, new_path)
    print(name)


    # plt.plot(fft)
    # plt.show()

