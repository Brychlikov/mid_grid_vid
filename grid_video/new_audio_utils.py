import os
import numpy as np
from scipy.io.wavfile import read as wav_read
from utils import split_path
import shutil
import subprocess

TEMP_DIR = "/tmp/mid_grid_vid"
if not os.path.exists(TEMP_DIR):
    os.mkdir(TEMP_DIR)




class AudioClip:

    def __init__(self, clip_path, cleanup=False):
        self.clip_path = clip_path
        self.cleanup = cleanup

        _dirname, basename, _ext = split_path(clip_path)
        self.audio_path = os.path.join(TEMP_DIR, f"{basename}.wav")
        self._extract_audio(clip_path, self.audio_path)

        self.array = self._make_array(self.audio_path)
        # self._make_cuts(self.clip_path, self._event_timestamps(13))

    @staticmethod
    def _extract_audio(clip_path, out_path):
        args = [
            "ffmpeg", 
            "-hide_banner",  # no hideous banner polluting stderr
            "-i", clip_path,
            "-vn",               # no video
            "-acodec", "pcm_s16le",
            out_path
        ]
        res = subprocess.run(args, capture_output=True)
        if res.returncode != 0:
            raise Exception("FFMPEG Error: " + res.stderr.decode())

    @staticmethod
    def _make_array(audio_path):
        """Reads wav file as a np.array. Ignores one of the channels"""
        return wav_read(audio_path)[1][:, 0] / (2 ** 15 - 1)

    def _event_timestamps(self, approx_num=None):
        if approx_num is None:
            seconds_per_event = 4
            approx_num = round(len(self.array) / (44100 * seconds_per_event))  
            print(f"Assuming {approx_num} events")


        window_size = 44100 // 4
        window_maxima = []
        for i in range(0, len(self.array), window_size):
            if i + window_size < len(self.array):
                window_maxima.append(np.max(self.array[i : i+window_size]))
            else:
                window_maxima.append(np.max(self.array[i: ]))
        window_maxima = np.array(window_maxima)
        print(f"Window maxima length: {len(window_maxima)}")

        def count(a, threshold):
            return sum(a > threshold)
        
        def contiguous_count(a, threshold):
            result = 0
            i = 0
            while i < len(a):
                while i < len(a) and a[i] < threshold:
                    i += 1

                if i >= len(a):
                    break

                while i < len(a) and a[i] >= threshold:
                    i += 1
                result += 1
            return result

        threshold = None
        for th in range(10, 200, 5):
            th = th / 1000
            if contiguous_count(window_maxima, th) == approx_num:
                threshold = th
                break

            # print("Threshold: {:.3f}\tCount: {}\t Contiguous count: {}".format(
            #                                                                    th, 
            #                                                                    count(window_maxima, th), 
            #                                                                    contiguous_count(window_maxima, th)
            # ))
        else:
            raise Exception("Could not find event threshold. This should not have happened")

        event_timestamps = []
        i = 0
        while(i < len(window_maxima)):
            while i < len(window_maxima) and window_maxima[i] < threshold:
                i += 1

            if i >= len(window_maxima):
                break

            event_timestamps.append(i / (44100 / window_size))
            
            while i < len(window_maxima) and window_maxima[i] >= threshold:
                i += 1
        return event_timestamps

    @staticmethod
    def _make_cuts(in_path, timestamps, marigin=1):
        prev_timestamp = 0
        timestamps = map(lambda x: x - marigin, timestamps)

        for i, timestamp in enumerate(timestamps):
            print("Processing clip ", i)
            directory, basename, ext = split_path(in_path)
            out_path = os.path.join(directory, f"{basename}_cut_{i}{ext}")
            args = [
                    "ffmpeg", "-hide_banner",
                    "-i", in_path,
                    "-ss", str(prev_timestamp),
                    "-t", str(timestamp - prev_timestamp),  # Don't include marigins at the end
                    out_path
            ]
            res = subprocess.run(args, capture_output=True)
            if res.returncode != 0:
                raise Exception("FFMPEG error: ", res.stderr.decode())
            prev_timestamp = timestamp

    def visualize_event_timestamps(self, approx_num=None):
        import matplotlib.pyplot as plt

        timestamps = self._event_timestamps(13)
        begins = map(lambda x: int((x - 1) * 44100), timestamps)
        ends = map(lambda x: int((x) * 44100), timestamps)
        plt.plot(self.array)
        for t1, t2 in zip(begins, ends):
            plt.axvline(x=t1, color='red')
            plt.axvline(x=t2, color='green')
        plt.show()

    def __del__(self):
        if self.cleanup:
            os.remove(self.audio_path)

if __name__ == "__main__":
    ac = AudioClip("../input/VID_20190622_191559.mp4", cleanup=True)
    # ac.visualize_event_timestamps(13)
    ac._make_cuts(ac.clip_path, ac._event_timestamps(13))
    print(ac.array)
    print(ac.array.shape)
    input("Waiting...")
