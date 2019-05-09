from dataclasses import dataclass

import grid_video.utils as utils
import grid_video.my_grid.Soundbank as Soundbank


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

    def append(self, element: Note):
        self.note_pool.add(element)
        if element.code != -1 and (self.lowest_note is None or element < self.lowest_note):
            self.lowest_note = element
        if element.code != -1 and (self.highest_note is None or element > self.highest_note):
            self.highest_note = element
        super().append(element)


class TrackAggregate(list):
    """Representation of a midi track containing multiple Track objects"""

    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)

        self.lowest_note = None
        self.highest_note = None
        self.note_pool = set()

        if len(self) > 0:
            self.lowest_note = min((t.lowest_note for t in self))
            self.highest_note = max((t.highest_note for t in self))
            for t in self:
                self.note_pool |= t.note_pool
        
    def append(self, element: Track):

        if element.lowest_note < self.lowest_note:
            self.lowest_note = element.lowest_note
        if element.highest_note > self.highest_note:
            self.highest_note = element.highest_note
        
        super().append(element)

    def is_empty(self):
        if len(self) == 0:
            return True
        for t in self:
            if len(t) > 0:
                return False
        return True

    def adapt_to(sb: Soundbank, mode='octave'):
        if mode == 'octave':
            pass
        elif mode == 'tone':
            raise NotImplementedError("No tone corretion ATM")
        else:
            raise ValueError("Mode has to be 'octave' or 'tone'")


