import random
from math import ceil, sqrt
import json
from itertools import repeat, chain
import shutil
import os.path
from utils import split_path
import subprocess
from abc import ABCMeta, abstractmethod, abstractproperty


# TODO Add common base class with methods such as
# separate_raw_audio
# result_fname
# write_to

CLEANUP = True

class FFMPEGErrorException(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__("FFMPEG error: " + msg, *args, **kwargs)

def erlambda(): raise NotImplementedError("This property should have been overloaded")

class BaseClip(metaclass=ABCMeta):

    suffix = "_"

    def __init__(self, cleanup=True):
        self.cleanup = cleanup
        self.executed = False

        # These two should be overriden in child classes
        self.name_base = None
        self.dependencies = None

    
    def separate_raw_audio(self):
        return RawAudioClip(self)

    @abstractproperty
    def result_fname(self):
        return

    def write_to(self, path):
        shutil.copy(self.result_fname, path)

    def get_resolution(self):
        if self.__dict__.get('dependencies'):
            return self.dependencies[0]
        else:
            return None

    def __del__(self):
        if self.cleanup and self.executed:
            print("cleaning up", self.name_base)
            os.remove(self.result_fname)



class RawAudioClip(BaseClip):

    suffix = "_audioonly"

    def __init__(self, source):
        super().__init__()
        self.name_base = source.name_base + "_audioonly"
        self.output_path = self.name_base + ".wav"
        self.source = source
        self.executed = False

    def _run_ffmpeg(self):
        print("Executing", self.name_base)
        args = [
                "ffmpeg", "-y",
                "-i", self.source.result_fname,
                "-vn", 
                "-acodec", "pcm_s16le",
                self.output_path
        ]
        res = subprocess.run(args, capture_output=True)
        if res.returncode != 0:
            raise FFMPEGErrorException(res.stderr.decode())

    @property
    def result_fname(self):
        if not self.executed:
            self._run_ffmpeg()
            self.executed = True
        return self.output_path

    def get_resolution(self):
        return None



class FilterClip(BaseClip):

    suffix = "_filter"

    def __init__(self, filter_string, dependencies, video_streams=1, audio_streams=1):
        super().__init__()
        self.dependencies = dependencies
        self.filter_string = filter_string
        self.map_list = []
        self.name_base = dependencies[0].name_base + "_filter-" + self.filter_string[:self.filter_string.find('=')]
        self.extention = '.avi'
        self.output_path = self.name_base + self.extention
        self.video_streams = video_streams
        self.audio_streams = audio_streams
        self.executed = False

    def _run_ffmpeg(self):
        print("Executing", self.name_base)
        print("Executing", self.name_base)

        fname_list = [d.result_fname for d in self.dependencies]
        input_args = []
        for fname in fname_list:
            input_args += ("-i", fname)
                
        args = [
            "ffmpeg", "-y",
            *input_args,
            "-filter_complex", self.filter_string,
            self.output_path
        ]
        res = subprocess.run(args, capture_output=True)
        if res.returncode != 0:
            raise FFMPEGErrorException(res.stderr.decode())

    @property
    def result_fname(self):
        if not self.executed:
            self._run_ffmpeg()
            self.executed = True
        return self.output_path



class AudioMixClip(BaseClip):
    # TODO Rewrite as Filter and FilterClip

    def __init__(self, dependencies):
        super().__init__()
        self.dependencies = dependencies
        self.name_base = self.dependencies[0].name_base + "_audiomix"
        self.extention = '.wav'
        self.output_path = self.name_base + self.extention
        self.executed = False

    def _run_ffmpeg(self):
        print("Executing", self.name_base)
        print("Executing", self.name_base)
        def flatten(l):
            return chain.from_iterable(l)
        input_list = flatten(zip(repeat("-i"), (c.result_fname for c in self.dependencies)))
        args = [
                "ffmpeg", "-y",
                *input_list,
                "-filter_complex", f"amix=inputs={len(self.dependencies)}",
                "-vn",
                "-ac", "2",
                self.output_path
        ]

        res = subprocess.run(args, capture_output=True)
        if res.returncode != 0:
            raise FFMPEGErrorException(res.stderr.decode())

    @property
    def result_fname(self):
        if not self.executed:
            self._run_ffmpeg()
            self.executed = True
        return self.output_path
    


class FileClip(BaseClip):

    suffix = "_nonreachable"

    def __init__(self, fname):
        super().__init__(cleanup=False)
        self.output_path = fname
        self.executed = True
        _directory, base, _ext = split_path(fname)
        self.name_base = 'tmp_' + base
        self.video_streams = 1
        self.audio_streams = 1

    @property
    def result_fname(self):
        return self.output_path
    
    def get_resolution(self):
        res = subprocess.run([
            'ffprobe', 
            '-hide_banner',
            # '-v', 'quiet',
            '-print_format', 'json', 
            '-show_streams',
            self.result_fname
        ], capture_output=True)

        if res.returncode != 0:
            raise FFMPEGErrorException(res.stderr.decode())
        
        data = json.loads(res.stdout)
        width = data["streams"][0]["width"]
        height = data["streams"][0]["height"]

        return width, height



class ConcatFilter:

    def __init__(self, c1, c2):
        self.clip_list = [c1, c2]
        input_string = " ".join([
                                 f"[{file_num}:{stream_num}]" 
                                 for file_num, c in enumerate(self.clip_list)
                                 for stream_num in range(c.audio_streams + c.video_streams)
                                ])
        # self.filter_complex = "[0:0] [0:1] [1:0] [1:1] concat=a=1"
        self.filter_complex = input_string + " concat=a=1"

    def build(self):
        return FilterClip(self.filter_complex, self.clip_list)



class DemuxAudioClip(BaseClip):

    suffix = "_conaudio"

    def __init__(self, concat_template, dependencies):
        super().__init__()
        self.concat_template = concat_template
        self.dependencies = [c.separate_raw_audio() for c in dependencies]
        self.name_base = dependencies[0].name_base + self.suffix
        self.extention = '.avi'
        self.output_path = self.name_base + self.extention
        self.executed = False

    def _run_ffmpeg(self):
        print("Executing", self.name_base)
        print("Executing", self.name_base)
        args = [
                "ffmpeg", "-y",
                "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-protocol_whitelist", "file,http,https,tcp,tls,pipe",  # Fixes "Protocol 'file' not on whilelist 'crypto' error"
                "-segment_time_metadata", "1",
                "-i", "pipe:",
                "-vn", 
                "-af", "asetnsamples=1,aselect=concatdec_select",
                self.output_path
        ]


        res = subprocess.run(args, capture_output=True, input=self.concat_template.format(
            *[os.path.abspath(c.result_fname) for c in self.dependencies])
            .encode())

        if res.returncode != 0:
            raise FFMPEGErrorException(res.stderr.decode())

    @property
    def result_fname(self):
        if not self.executed:
            self._run_ffmpeg()
            self.executed = True
        return self.output_path



class DemuxVideoClip(BaseClip):

    suffix = "_convideo"

    def __init__(self, concat_template, dependencies):
        super().__init__()
        self.concat_template = concat_template
        self.dependencies = dependencies
        self.name_base = dependencies[0].name_base + self.suffix
        self.extention = '.avi'
        self.output_path = self.name_base + self.extention
        self.executed = False

    def _run_ffmpeg(self):
        print("Executing", self.name_base)
        args = [
                "ffmpeg", "-y",
                "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-protocol_whitelist", "file,http,https,tcp,tls,pipe",  # Fixes "Protocol 'file' not on whilelist 'crypto' error"
                "-segment_time_metadata", "1",
                "-i", "pipe:",
                "-an", 
                "-vf", "select=concatdec_select",
                "-c:v", "mpeg4",  # Don't remember why its necessary
                self.output_path
        ]


        res = subprocess.run(args, capture_output=True, input=self.concat_template.format(
            *[os.path.abspath(c.result_fname) for c in self.dependencies])
            .encode())

        if res.returncode != 0:
            raise FFMPEGErrorException(res.stderr.decode())

    @property
    def result_fname(self):
        if not self.executed:
            self._run_ffmpeg()
            self.executed = True
        return self.output_path



class AudioVideoMergeClip(BaseClip):

    suffix = "_mergeaudio"

    def __init__(self, video_clip, audio_clip):
        super().__init__()
        self.video_clip = video_clip
        self.audio_clip = audio_clip
        self.name_base = video_clip.name_base + self.suffix
        self.extention = '.avi'


        self.output_path = self.name_base + self.extention
        self.executed = False

    def _run_ffmpeg(self):
        print("Executing", self.name_base)
        print("Merging", self.video_clip.name_base, self.audio_clip.name_base)
        args = [
                "ffmpeg", "-y",
                "-i", self.video_clip.result_fname,
                "-i", self.audio_clip.result_fname,
                "-map", "0:0",
                "-map", "1:0",
                "-c", "copy",
                "-shortest",
                self.output_path
        ]

        res = subprocess.run(args, capture_output=True)
        if res.returncode != 0:
            raise FFMPEGErrorException(res.stderr.decode())

    def write_to(self, output_path):
        self.output_path = output_path
        self._run_ffmpeg()

    @property
    def result_fname(self):
        if not self.executed:
            self._run_ffmpeg()
            self.executed = True
        return self.output_path



class ConcatDemux:
    def __init__(self, durlist):
        """durlist - list of tuples in form of (clip, inpoint, outpoint)"""
        self.dependencies = [entry[0] for entry in durlist]
        self.durlist = durlist

        # better hope i dont miss any {}
        self.template = ""
        for _clip, inpoint, outpoint in self.durlist:
            self.template += "file '{}'\n"
            self.template += f"inpoint {inpoint}\n"
            self.template += f"outpoint {outpoint}\n"
            self.template += "\n"

    def build(self):
        return AudioVideoMergeClip(
                DemuxVideoClip(self.template, self.dependencies),
                DemuxAudioClip(self.template, self.dependencies))

class ScaleFilter:
    
    def __init__(self, source, target):
        self.source = source
        if isinstance(target, tuple):
            self.width, self.height = target
            self.filter_string = f"scale=w={self.width}:h={self.height}"
        elif isinstance(target, int):
            source_width, source_height = source.get_resolution()
            self.filter_string = f"scale=w=iw/{target}:h=ih/{target}"
            self.width, self.height = source_width // target, source_height // target
        else:
            raise ValueError("Invalid value of target")

    def build(self):
        result = FilterClip(self.filter_string, [self.source])
        # TODO rewrite this thing
        # its absolutely disgusting
        # i feel dirty
        result.get_resolution = lambda: (self.width, self.height)
        return result

class GridFilter:

    def __init__(self, sources, shrink_to_original_size=True):
        size = ceil(sqrt(len(sources)))
        def coords(index):
            return index // size, index % size
        
        def string_coords(index):
            temp = coords(index)
            return f"{temp[0]}-{temp[1]}"

        clip_width, clip_height = sources[0].get_resolution()
        if shrink_to_original_size:
            final_width, final_height = clip_width, clip_height
            sources = [ScaleFilter(c, size).build() for c in sources]
            width, height = clip_width // size, clip_height // size
        else:
            final_width, final_height = clip_width * size, clip_height * size
            width, height = clip_width, clip_height

        self.filter_complex = f"color=size={final_width}x{final_height}:color=Black [base]; \n"

        for i, _c in enumerate(sources):
            self.filter_complex += f"[{i}:v] setpts=PTS-STARTPTS, scale={width}x{height} [single{string_coords(i)}]; \n"

        self.sources = sources

        previous_step = "[base]"
        
        for i in range(len(sources) - 1):  # overlay entries for all but last step
            # this would be simpler if I got rid of FilterClip and/or added -map support
            y, x = coords(i)
            self.filter_complex += f"{previous_step}[single{string_coords(i)}] overlay=shortest=1:x={x*width}:y={y*height} [stage{i}]; \n"
            previous_step = f"[stage{i}]"

        last = len(sources) - 1
        y, x = coords(last)
        self.filter_complex += f"{previous_step}[single{string_coords(last)}] overlay=shortest=1:x={x*width}:y={y*height}\n"
    
    def build(self):
        print("EXECUTING FINAL FILTER")
        print(self.filter_complex)
        grid_video = FilterClip(self.filter_complex, self.sources)
        audio_clip = AudioMixClip([c.separate_raw_audio() for c in self.sources])
        return AudioVideoMergeClip(grid_video, audio_clip)




if __name__ == "__main__":
    clip1 = FileClip("./soundbanks/copy_guitar/a3.avi")
    clip2 = FileClip("./soundbanks/copy_guitar/c4.avi")
    clip3 = FileClip("./soundbanks/copy_guitar/e4.avi")
    clip4 = FileClip("./soundbanks/copy_guitar/a4.avi")

    print(clip1.dependencies)


    # res = AudioMixClip([ScaleFilter(c, 960, 540) for c in [clip1, clip2, clip3, clip4]])
    # res.write_to('mixtest.wav')
    # res = ConcatDemux([
    #         (clip1, 0, 1) for i in range(120)]).build()
    # res.write_to('concattest2.avi')
    res = GridFilter([clip1, clip2, clip3]).build()
    res.write_to('gridtest.avi')
