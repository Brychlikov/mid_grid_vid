MIDI_NOTE_NUM = {
    'c': 0,
    'c#': 1,
    'df': 1,
    'd': 2,
    'd#': 3,
    'ef': 3,
    'e': 4,
    'f': 5,
    'f#': 6,
    'gf': 6,
    'g': 7,
    'g#': 8,
    'af': 8,
    'a': 9,
    'a#': 10,
    'bf': 10,
    'b': 11
}

MIDI_NUM_NOTE = {
    0: 'c',
    1: 'c#',
    2: 'd',
    3: 'd#',
    4: 'e',
    5: 'f',
    6: 'f#',
    7: 'g',
    8: 'g#',
    9: 'a',
    10: 'bf',
    11: 'b'
}


def check_note_pool(rec):
    pool = set()
    for track in rec:
        for subtrack in track:
            for note in subtrack:
                pool.add(note.name)

    if 'silence' in pool:
        pool.remove('silence')

    l = sorted(list(pool))
    return l


def note_name(midi_num):
    if midi_num == -1:
        return 'silence'
    octave = midi_num // 12 - 1
    note = MIDI_NUM_NOTE[midi_num % 12]
    return note + str(octave)


def note_code(name):
    if name == 'silence':
        return -1
    octave = int(name[-1])
    return MIDI_NOTE_NUM[name[:-1]] + (octave + 1) * 12



