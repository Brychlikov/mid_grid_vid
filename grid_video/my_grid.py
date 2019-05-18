import os
import shutil
import random
import mido
import json
import subprocess
import glob
from math import sqrt, ceil
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
        s = subprocess.run([
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", self.fname], 
                           capture_output=True)
        if s.returncode != 0:
            raise Exception(f"Exception while polling for duration: {s.stderr}")
        return float(s.stdout)

    def extract_raw_audio(self, output):
        args = [
            "ffmpeg",
            "-i", self.fname,
            "-vn",
            output
        ]
        res = subprocess.run(args, capture_output=True)
        if res.returncode != 0:
            raise Exception("FFMPEG Error: " + res.stderr.decode())

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
        self.audiobank = None

    def boundaries(self):
        min_note = None
        for k in self.keys():
            if k != -1 and (min_note is None or k < min_note):
                min_note = k
        max_note = max(self.keys())
        return Note(min_note, 0), Note(max_note, 0)

    def make_ffmpeg_entry(self, note: Note, debug=""):
        # Prolly should move it
        # Should I really tho?
        result = ""
        result += f"# {note} {debug}\n"
        clip = self.get(note.code)
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
        # Prolly should move it
        if fname is None:
            fname = os.path.join(TEMP_DIR, "ffmpeg_concat_" + str(random.randint(1, 10000000)))
        with open(fname, 'w') as file:
            total_time = 0
            for n in track:
                file.write(self.make_ffmpeg_entry(n, debug=total_time))
                total_time += n.length
        return fname

    def make_raw_audiobank(self, overwrite=False):
        new_path = os.path.join(self.path, 'raw_audio')
        if os.path.exists(new_path):
            if overwrite:
                shutil.rmtree(new_path)
            else:
                raise IOError("Raw audiobank directory exists. If you want to overwrite it use overwrite=True")

        os.makedirs(new_path)

        for clip in self.values():
            fname = os.path.basename(clip.fname)
            base_file, extention = os.path.splitext(fname)
            new_fname = os.path.join(new_path, base_file + '.wav')
            clip.extract_raw_audio(new_fname)
        
        self.audiobank = Soundbank(new_path, begin_offset=self.begin_offset)

    def get(self, obj):
        r = super().get(obj)
        if r is None:
            print(f"Warning: Note {obj} not found. Silence used instead")
            r = self.silence
        return r


def make_track_vid(soundbank, track: Track, output_fname=None):

    if output_fname is None:
        output_fname = os.path.join(TEMP_DIR, "track_" + str(random.randint(1, 1000000000)) + ".avi")

    concat_file = soundbank.make_track_file(track, output_fname + ".concat")

    args = [
        "ffmpeg", "-y",
        "-loglevel", "error",
        "-f", "concat",
        "-safe", "0",
        "-segment_time_metadata", "1",
        "-i", concat_file,
        "-an", 
        "-vf", "select=concatdec_select",
        "-c:v", "mpeg4",
        output_fname
    ]
    res = subprocess.run(args, capture_output=True)

    if res.returncode != 0:
        raise Exception("FFMPEG error: " + res.stderr.decode())

    return output_fname


def make_track_audio(soundbank, track: Track, output_fname=None):
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
        "-af", "asetnsamples=1,aselect=concatdec_select",
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


def split_path(path):
    dirname, fname = os.path.split(path)
    basename, ext = os.path.splitext(fname)
    return dirname, basename, ext


def make_vid_audio(soundbank, clips, output_fname):

    out_dir, basename, ext = split_path(output_fname)

    track_vid_fnames = []

    for i, c in enumerate(clips):
        print(f"parsing track {i} out of {len(clips)}")
        track_vid_fnames.append(make_track_audio(soundbank.audiobank, c, output_fname=f"{TEMP_DIR}/temp_{basename}_{i}.wav"))

    input_args = []
    for name in track_vid_fnames:
        input_args.extend(("-i", name))
    
    res = subprocess.run([
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", f"amix=inputs={len(track_vid_fnames)}",
        "-ac", "2",
        "-c:a", "libmp3lame",
        output_fname
    ], capture_output=True)
    if res.returncode != 0:
        raise Exception("FFMPEG Error: " + res.stderr.decode())


def check_resolution(fname):
    res = subprocess.run([
        'ffprobe', 
        '-hide_banner',
        # '-v', 'quiet',
        '-print_format', 'json', 
        '-show_streams',
        fname
    ], capture_output=True)

    if res.returncode != 0:
        raise Exception("FFProbe error: " + res.stderr.decode())
    
    data = json.loads(res.stdout)
    width = data["streams"][0]["width"]
    height = data["streams"][0]["height"]

    return width, height


def build_grid(clip_fnames, output_fname):

    size = ceil(sqrt(len(clip_fnames)))

    def coords(index):
        return index // size, index % size
    
    def string_coords(index):
        temp = coords(index)
        return f"{temp[0]}-{temp[1]}"

    width, height = check_resolution(clip_fnames[0])
    final_width, final_height = width * size, height * size

    filter_complex = f"color=size={final_width}x{final_height}:color=Black [base]; "
    
    # set the same presentation timestamp of the first frame for all of them
    for i, c in enumerate(clip_fnames):
        filter_complex += f"[{i}:v] setpts=PTS-STARTPTS, scale={width}x{height} [single{string_coords(i)}]; "

    previous_step = "[base]"
    for i in range(len(clip_fnames) - 1):  # overlay entries for all but last step
        y, x = coords(i)
        filter_complex += f"{previous_step}[single{string_coords(i)}] overlay=shortest=1:x={x*width}:y={y*height} [stage{i}]; "
        previous_step = f"[stage{i}]"
    
    last = len(clip_fnames) - 1
    y, x = coords(last)
    filter_complex += f"{previous_step}[single{string_coords(last)}] overlay=shortest=1:x={x*width}:y={y*height}"

    input_names = []
    for n in clip_fnames:
        input_names += ["-i", n]

    args = [
        "ffmpeg", "-y", "-hide_banner",
        *input_names,
        "-filter_complex", filter_complex,
        "-c:v", "mpeg4",
        output_fname
    ]
    res = subprocess.run(args, capture_output=False)
    if res.returncode != 0:
        raise Exception("FFMPEG error: " + res.stderr.decode())


def make_grid_vid(midi_fname, soundbank_dir, autoshift, output, offset=0):
    midi_dir, midi_name, _ = split_path(midi_fname)
    soundbank = Soundbank(soundbank_dir, offset)
    print("Generating audiobank")
    try:
        soundbank.make_raw_audiobank()
    except IOError:
        audiobank = Soundbank(os.path.join(soundbank_dir, 'raw_audio'), offset)
        soundbank.audiobank = audiobank
    parsed = parse_midi(mido.MidiFile(midi_fname))

    clips = []
    for mid_track in parsed:
        if autoshift:
            mid_track.adapt_to(soundbank)
        clips.extend(mid_track)
    

    clips.sort(key=lambda i: i.total_sound_length(), reverse=True)


    track_fnames = []
    for i, c in enumerate(clips):
        print(f"Building video {i+1} out of {len(clips)}")
        track_fname = f"{midi_name}_temp_track{i}.avi"
        track_fnames.append(os.path.join(TEMP_DIR, track_fname))
        # input("ATTENTION!!!! Are you dumb? [Y/n]\n")
        make_track_vid(soundbank, c, os.path.join(TEMP_DIR, track_fname))

    grid_fname = os.path.join(TEMP_DIR, f"{midi_name}_TEMP_GRID.avi")
    build_grid(track_fnames, grid_fname)
    print("Grid assembly completed")

    audio_fname = os.path.join(TEMP_DIR, f"{midi_name}_TEMP_AUDIO.wav")
    make_vid_audio(soundbank, clips, audio_fname)
    print("audio completed")

    args = [
        "ffmpeg", "-y",
        "-i", grid_fname,
        "-i", audio_fname,
        "-c", "copy",
        "-shortest",
        output
    ]
    res = subprocess.run(args, capture_output=True)
    if res.returncode != 0:
        raise Exception("FFMPEG Error: " + res.stderr.decode())


if __name__ == "__main__":
    # sb = Soundbank('soundbanks/copy_guitar', begin_offset=0.04)
    # parsed = parse_midi(mido.MidiFile("midis/undertale.mid"))
    # sb.make_track_file(parsed[1][0])
    # make_track_vid(sb, parsed[1][0])
    make_grid_vid('midis/spear.mid', 'soundbanks/copy_guitar', True, 'spear.avi', 0.02)
