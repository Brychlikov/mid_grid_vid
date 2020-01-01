import random
import subprocess


class FFMPEGErrorException(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__("FFMPEG error: " + msg, *args, **kwargs)

class FilterClip:

    def __init__(self, filter_string, dependencies):
        self.dependencies = dependencies
        self.filter_string = filter_string
        self.map_list = []
        self.output_path = "TEMP"
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


class ConcatFilter:

    def __init__(self, c1, c2):
        self.clip_list = [c1, c2]
        self.filter_complex = "[0:0] [0:1] [1:0] [1:1] concat=a=1"

    def build(self):
        return FilterClip(self.filter_complex, self.clip_list)


if __name__ == "__main__":
    clip1 = FileClip("./soundbanks/copy_guitar/a3.avi")
    clip2 = FileClip("./soundbanks/copy_guitar/a4.avi")

    res = ConcatFilter(clip1, clip2).build()
    res.write_to('concattest2.avi')
