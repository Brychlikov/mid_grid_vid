from dataclasses import dataclass

import grid_video.utils as utils


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

    def total_length(self):
        return sum([n.length for n in self if n.code != -1])