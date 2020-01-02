import random
import os.path
import subprocess


# TODO Add common base class with methods such as
# separate_raw_audio
# result_fname
# write_to


class FFMPEGErrorException(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__("FFMPEG error: " + msg, *args, **kwargs)


class BaseClip:


class FilterClip:

    def __init__(self, filter_string, dependencies, video_streams=1, audio_streams=1):
        self.dependencies = dependencies
        self.filter_string = filter_string
        self.map_list = []
        self.output_path = "TEMP"
        self.video_streams = video_streams
        self.audio_streams = audio_streams
        self.executed = False

    def _run_ffmpeg(self):

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


    def write_to(self, fname):
        self.output_path = fname
        self._run_ffmpeg()

    @property
    def result_fname(self):
        if not self.executed:
            self._run_ffmpeg()
            self.executed = True
        return self.output_path

    @classmethod
    def concat_filter(cls, c1, c2):
        filter_complex = "[0:0] [0:1] [1:0] [1:1] concat=a=1"
        return FilterClip(filter_complex, [c1, c2])
    
# TODO
# Add a class to abstract separation of audio and video curing cutting
# Also maybe a class for concat demuxer



class FileClip:
    def __init__(self, fname):
        self.result_fname = fname
        self.executed = True
        self.video_streams = 1
        self.audio_streams = 1


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


class DemuxAudioClip:
    def __init__(self, concat_template, dependencies, output_path=None):
        self.concat_template = concat_template
        self.dependencies = dependencies
        self.output_path = output_path
        self.executed = False

    def _run_ffmpeg(self):
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


class DemuxVideoClip:
    def __init__(self, concat_template, dependencies, output_path=None):
        self.concat_template = concat_template
        self.dependencies = dependencies
        self.output_path = output_path
        self.executed = False

    def _run_ffmpeg(self):
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


class AudioVideoMergeClip:

    def __init__(self, video_clip, audio_clip, output_path):
        self.video_clip = video_clip
        self.audio_clip = audio_clip

        self.output_path = output_path
        self.executed = False

    def _run_ffmpeg(self):
        args = [
                "ffmpeg", "-y",
                "-i", self.video_clip.result_fname,
                "-i", self.audio_clip.result_fname,
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
                DemuxVideoClip(self.template, self.dependencies, 'temp_demux_video.avi'),
                DemuxAudioClip(self.template, self.dependencies, 'temp_demux_audio.wav'),
                'temp_demux_full.avi'
                )



if __name__ == "__main__":
    clip1 = FileClip("./soundbanks/copy_guitar/a3.avi")
    clip2 = FileClip("./soundbanks/copy_guitar/c4.avi")
    clip3 = FileClip("./soundbanks/copy_guitar/e4.avi")
    clip4 = FileClip("./soundbanks/copy_guitar/a4.avi")


    res = ConcatDemux([
            (clip1, 0, 1),
            (clip2, 0, 1),
            (clip3, 0, 1),
            (clip4, 0, 1),
            (clip1, 0, 1),
            ]).build()
    res.write_to('concattest2.avi')
