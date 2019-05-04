import os
import mido
import subprocess
import glob
from grid_video.core import Note, Track
from grid_video.utils import note_code, note_name
from grid_video.parser import parse_midi


class NoteClip:
    def __init__(self, fname):
        no_dir_name = os.path.basename(fname)
        name = no_dir_name[:no_dir_name.find('.')]
        code = note_code(name)
        self.name = name
        self.code = code
        self.fname = fname    
        self.duration = self.check_duration()

    def check_duration(self):
        s = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", self.fname], 
                           capture_output=True)
        if s.returncode != 0:
            raise Exception(f"Exception while polling for duration: {s.stderr}")
        return float(s.stdout)

    def __hash__(self):
        return hash(self.fname)
    

class Soundbank(dict):
    def __init__(self, directory, begin_offset=0):
        for fname in glob.glob(os.path.join(directory, "*")):
            try:
                no_dir_name = os.path.basename(fname)
                name = no_dir_name[:no_dir_name.find('.')]
                code = note_code(name)
                self[code] = NoteClip(fname)
            except ValueError:
                print(f"Couldn't parse file {fname}")
        if begin_offset != 0:
            raise NotImplementedError("Begin offset is not yet implemented")
        
        self.silence = self[-1]
        self.prelonging_method = 'silence'

    def make_ffmpeg_entry(self, note: Note):
        result = ""
        result += f"# {note}\n"
        clip = self[note.code]
        if clip.duration >= note.length:
            result += f"file '{clip.fname}'\n"
            result += f"outpoint {note.length}\n"
        elif self.prelonging_method == 'silence':
            result += f"file '{clip.fname}'\n"
            excess = note.length - clip.duration
            while excess > self.silence.duration:
                result += f"file '{self.silence.fname}'\n"
                excess -= self.silence.duration
            result += f"file '{self.silence.fname}'\n"
            result += f"outpoint {excess}\n"
        else:
            raise NotImplementedError("Prelonging methods other than silence are not yet supported")
        result += "\n"
        return result

    def make_track_file(self, track: Track):
        with open('ffmpegtemp.txt', 'w') as file:
            for n in track:
                file.write(self.make_ffmpeg_entry(n))

    def __getitem__(self, obj):
        r = super().get(obj)
        if r is None:
            print(f"Warning: Note not found {obj}")
            r = self.silence
        return r



def make_simple_soundbank(directory, begin_offset=0):
    """makes soundbank based on given directory, assuming that each file name is <soundname>.mp4"""
    result = {}

    for fname in glob.glob(os.path.join(directory, "*")):
        try:
            no_dir_name = os.path.basename(fname)
            name = no_dir_name[:no_dir_name.find('.')]
            code = note_code(name)
            result[code] = NoteClip(fname)
        except ValueError:
            print(f"Couldn't parse file {fname}")
    if begin_offset != 0:
        raise NotImplementedError("Begin offset is not yet implemented")
    return result

def make_track_vid(soundbank, track: Track, autoshift=False):
    silence = soundbank[-1]

    bank_min, bank_max = soundbank_boundaries(soundbank)
    if autoshift and (track.lowest_note < bank_min or track.highest_note > bank_max):
        if bank_min.code - track.lowest_note.code >= track.highest_note.code - bank_max.code:
            octave_offset = (bank_min.code - track.lowest_note.code + 6) // 12 + 1
            print("shifting track one octave up")
        else:
            octave_offset = ((track.highest_note.code - bank_max.code + 6) // 12) * -1
            print("shifting track one octave down")
        for note in track:
            note.code += octave_offset * 12

    
def soundbank_boundaries(soundbank):
    min_note = None
    for k in soundbank.keys():
        if k != -1 and (min_note is None or k < min_note):
            min_note = k
    max_note = max(soundbank.keys())
    return Note(min_note, 0), Note(max_note, 0)


if __name__ == "__main__":
    sb = Soundbank('soundbanks/copy_guitar')
    parsed = parse_midi(mido.MidiFile("midis/true.mid"))
    sb.make_track_file(parsed[1][0])
