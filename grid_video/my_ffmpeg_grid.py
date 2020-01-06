from video import FileClip, BaseClip, GridFilter, ConcatDemux
from core import Note, Track, TrackAggregate
import glob
import os
from utils import split_path, note_code, note_name
import subprocess


class NoteClip(FileClip):
    def __init__(self, fname):
        super().__init__(self, fname)
        no_dir_name = os.path.basename(fname)
        name = no_dir_name[:no_dir_name.find('.')]
        code = note_code(name)
        self.name = name
        self.code = code
        self.fname = os.path.abspath(fname)
        self.duration = self.check_duration()

    def check_duration(self):
        s = subprocess.run([
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", self.fname], 
                           capture_output=True)
        if s.returncode != 0:
            raise Exception(f"Exception while polling for duration: {s.stderr}")
        return float(s.stdout)


    def __hash__(self):
        return hash(self.fname)


class Soundbank(dict):
    # This class does too much. I think ffmpeg related stuff should be moved to a different class.
    def __init__(self, directory, begin_offset=0):
        for fname in glob.glob(os.path.join(directory, "*")):
            try:
                no_dir_name = os.path.basename(fname)
                name = no_dir_name[:no_dir_name.find('.')]
                code = note_code(name)
                self[code] = NoteClip(fname)
            except ValueError:
                print(f"Couldn't parse file {fname}")
        
        self.path = os.path.abspath(directory)
        self.silence = self[-1]
        self.prelonging_method = 'silence'
        self.begin_offset = begin_offset

    def boundaries(self):
        min_note = None
        for k in self.keys():
            if k != -1 and (min_note is None or k < min_note):
                min_note = k
        max_note = max(self.keys())
        return Note(min_note, 0), Note(max_note, 0)



