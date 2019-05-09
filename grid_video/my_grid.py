import os
import random
import mido
import subprocess
import glob
from grid_video.core import Note, Track
from grid_video.utils import note_code, note_name
from grid_video.parser import parse_midi


TEMP_DIR = '/mnt/Data/grid_tmp'


class NoteClip:
    def __init__(self, fname):
        no_dir_name = os.path.basename(fname)
        name = no_dir_name[:no_dir_name.find('.')]
        code = note_code(name)
        self.name = name
        self.code = code
        self.fname = os.path.abspath(fname)
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
        
        self.silence = self[-1]
        self.prelonging_method = 'silence'
        self.begin_offset = begin_offset

    def make_ffmpeg_entry(self, note: Note, debug=""):
        result = ""
        result += f"# {note} {debug}\n"
        clip = self[note.code]
        actual_clip_duration = clip.duration - self.begin_offset

        if actual_clip_duration >= note.length:
            result += f"file '{clip.fname}'\n"
            if self.begin_offset != 0:
                result += f"inpoint {self.begin_offset}\n"
            result += f"outpoint {note.length + self.begin_offset}\n"

        elif self.prelonging_method == 'silence':
            result += f"file '{clip.fname}'\n"

            excess = note.length - actual_clip_duration
            while excess > self.silence.duration:
                result += f"file '{self.silence.fname}'\n"
                excess -= self.silence.duration

            result += f"file '{self.silence.fname}'\n"
            result += f"outpoint {excess}\n"

        else:
            raise NotImplementedError("Prelonging methods other than silence are not yet supported")

        result += "\n"
        return result

    def make_track_file(self, track: Track, fname=None):
        if fname is None:
            fname = os.path.join(TEMP_DIR, "ffmpeg_concat_" + str(random.randint(1, 10000000)))
        with open(fname, 'w') as file:
            total_time = 0
            for n in track:
                file.write(self.make_ffmpeg_entry(n, debug=total_time))
                total_time += n.length
        return fname

    def __getitem__(self, obj):
        r = super().get(obj)
        if r is None:
            print(f"Warning: Note not found {obj}")
            r = self.silence
        return r


def make_track_vid(soundbank, track: Track, autoshift=False, output_fname=None):
    silence = soundbank[-1]

    bank_min, bank_max = soundbank_boundaries(soundbank)
    if autoshift and (track.lowest_note < bank_min or track.highest_note > bank_max):
        if bank_min.code - track.lowest_note.code >= track.highest_note.code - bank_max.code:
            octave_offset = (bank_min.code - track.lowest_note.code) // 12 + 1
            print("shifting track one octave up")
        else:
            octave_offset = ((track.highest_note.code - bank_max.code) // 12 + 1) * -1
            print("shifting track one octave down")

        track = Track([n.shift(octave_offset * 12) for n in track])

    if output_fname is None:
        output_fname = os.path.join(TEMP_DIR, "track_" + str(random.randint(1, 1000000000)) + ".wav")

    concat_file = soundbank.make_track_file(track, output_fname + ".concat")

    res = subprocess.run([
        "ffmpeg", "-y",
        "-loglevel", "error",
        "-f", "concat",
        "-safe", "0",
        "-segment_time_metadata", "1",
        "-i", concat_file,
        "-vn", 
        "-af", "asetnsamples=1,aselect=concatdec_select,aresample=async=1",
        # "-c:a", "libmp3lame",
        output_fname
    ], capture_output=True)

    if res.returncode != 0:
        raise Exception("FFMPEG error: " + res.stderr.decode())

    return output_fname

    
def soundbank_boundaries(soundbank):
    min_note = None
    for k in soundbank.keys():
        if k != -1 and (min_note is None or k < min_note):
            min_note = k
    max_note = max(soundbank.keys())
    return Note(min_note, 0), Note(max_note, 0)


def make_vid_audio(midi_fname, soundbank_dir, autoshift, output, offset=0):
    soundbank = Soundbank(soundbank_dir, offset)
    parsed = parse_midi(mido.MidiFile(midi_fname))

    clips = []
    for mid_track in parsed:
        clips.extend(mid_track)
    
    midi_basename = os.path.basename(midi_fname)
    midi_name = os.path.splitext(midi_basename)[0]

    clips.sort(key=lambda i: i.total_length(), reverse=True)
    track_vid_fnames = []

    for i, c in enumerate(clips):
        print(f"parsing track {i} out of {len(clips)}")
        track_vid_fnames.append(make_track_vid(soundbank, c, autoshift, output_fname=f"{TEMP_DIR}/temp_{midi_name}_{i}.wav"))

    input_args = []
    for name in track_vid_fnames:
        input_args.extend(("-i", name))
    
    subprocess.run([
        "ffmpeg", "-y",
        "-loglevel", "error",
        *input_args,
        "-filter_complex", "amix=inputs=4",
        "-ac", "2",
        "-c:a", "libmp3lame",
        f"{midi_name}.wav"
    ])




if __name__ == "__main__":
    # sb = Soundbank('soundbanks/copy_guitar', begin_offset=0.04)
    # parsed = parse_midi(mido.MidiFile("midis/undertale.mid"))
    # sb.make_track_file(parsed[1][0])
    # make_track_vid(sb, parsed[1][0])
    make_vid_audio('midis/ngahhh.mid', 'soundbanks/raw_sound_guitar', False, 'osidjf', 0.02)
