from dataclasses import dataclass

import grid_video.utils as utils


PAD_ACCURACY = 1e-6


class Note:
    """Representation of a single note/sound having its own clip"""
    def __init__(self, n, length):
        self.length = length
        if isinstance(n, str):
            self.name = n
            self.code = utils.note_code(n)

        elif isinstance(n, int):
            self.name = utils.note_name(n)
            self.code = n

        else:
            raise ValueError("n should be note name or MIDI code")

    def shift(self, n):
        if self.code == -1:
            return self
        else:
            return Note(self.code + n, self.length)

    def __eq__(self, other):
        return isinstance(other, Note) and self.code == other.code 

    def __lt__(self, other):
        assert(isinstance(other, Note))
        return self.code < other.code

    def __gt__(self, other):
        assert(isinstance(other, Note))
        return self.code > other.code
    
    def __ge__(self, other):
        assert(isinstance(other, Note))
        return not (self < other)

    def __le__(self, other):
        assert(isinstance(other, Note))
        return not (self > other)
    
    def __hash__(self):
        # Not very safe, but hey, should work
        return hash(self.code)
    
    def __repr__(self):
        return f"Note(n={self.name}, length={self.length})"

    def __str__(self):
        return self.__repr__()



class Track(list):
    """Representation of a track - a non-concurrent series of notes"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.lowest_note = None
        self.highest_note = None
        self.note_pool = set()

        if len(self) > 1:
            self.highest_note = max(self)

            for n in self:
                if n.code != -1 and (self.lowest_note is None or n < self.lowest_note):
                    self.lowest_note = n
            
            self.note_pool = set(self)


    def append(self, element: Note):
        self.note_pool.add(element)
        if element.code != -1 and (self.lowest_note is None or element < self.lowest_note):
            self.lowest_note = element
        if element.code != -1 and (self.highest_note is None or element > self.highest_note):
            self.highest_note = element
        super().append(element)

    def total_sound_length(self):
        return sum([n.length for n in self if n.code != -1])

    def total_length(self):
        return sum([n.length for n in self])

    def pad_to_duration(self, duration):
        pad = duration - self.total_length() 
        if pad < PAD_ACCURACY * -1:
            raise ValueError("Track is already longer than specified duration")
        elif pad > PAD_ACCURACY * -1 and pad < PAD_ACCURACY:
            pass
        else:
            self.append(Note('silence', pad))

class TrackAggregate(list):
    """Representation of a midi track containing multiple Track objects"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.lowest_note = None
        self.highest_note = None
        self.note_pool = set()

        if len(self) > 0:
            self.lowest_note = min((t.lowest_note for t in self))
            self.highest_note = max((t.highest_note for t in self))
            for t in self:
                self.note_pool |= t.note_pool
        
    def append(self, element: Track):

        if self.lowest_note is None or element.lowest_note < self.lowest_note:
            self.lowest_note = element.lowest_note
        if self.highest_note is None or element.highest_note > self.highest_note:
            self.highest_note = element.highest_note
        
        super().append(element)

    def is_empty(self):
        if len(self) == 0:
            return True
        for t in self:
            if len(t) > 0:
                return False
        return True

    def pad_to_duration(self, duration):
        for t in self:
            t.pad_to_duration(duration)

    def adapt_to(self, sb, mode='octave', max_correction=1):  # TODO add typehints
        if self.is_empty():
            return

        if mode == 'octave':
            sb_low, sb_high = sb.boundaries()

            left_deficit = sb_low.code - self.lowest_note.code
            right_deficit = self.highest_note.code - sb_high.code

            if left_deficit > 0 and right_deficit > 0:
                print("WARNING: Soundbank too small for one of the tracks")
                return None  # Soundbank is too small for the track, better leave it for now
            
            if left_deficit < 0 and right_deficit < 0:
                return None  # Track fits inside Soundbank

            if left_deficit > right_deficit:
                octave_offset = min((left_deficit // 12 + 1, max_correction))
            elif right_deficit > left_deficit:
                octave_offset = min((right_deficit // 12 + 1, max_correction)) * -1
            else:
                print("WARNING: Can't fit a track into the soundbank. Maybe try mode='tone'")
                return None

            for i, t in enumerate(self):
                temp = Track([n.shift(octave_offset * 12) for n in t])
                self[i] = temp
            
            print("IT ACTUALLY SHIFTED SOMETHING HYPE")
            print(f"shifted track by {octave_offset} octaves")

        elif mode == 'tone':
            raise NotImplementedError("No tone corretion ATM")
        else:
            raise ValueError("Mode has to be 'octave' or 'tone'")


