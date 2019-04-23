import moviepy.editor as mpy
import moviepy
import numpy as np

import os
import sys
import argparse

TEST_RESOLUTION = 1000


def cut_silence(clip):
    ar = clip.audio.to_soundarray()[:, 0]  # I will ignore one of the channels for now
    ar: np.ndarray = ar[:len(ar) - len(ar) % TEST_RESOLUTION]
    ar = abs(ar)

    shape = (len(ar) // TEST_RESOLUTION, TEST_RESOLUTION)

    ar = ar.reshape(shape)

    volume = np.mean(ar, axis=1)

    for i, v in enumerate(volume):
        if v > volume.max() * 0.5:
            start_index = i
            break

    start_time = start_index * TEST_RESOLUTION / clip.audio.fps
    return clip.subclip(start_time)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="")
    file_list = sys.argv[1:]
    if len(file_list) == 0:
        print("No files specified")
        sys.exit(1)
    elif len(file_list) == 1:
        prefix = "processed_"
    else:
        os.makedirs("new_processed_clips", exist_ok=True)
        prefix = "new_processed_clips/"
    
    print(file_list)
    
    for fname in file_list:
        clip = mpy.VideoFileClip(fname)
        result = cut_silence(clip)
        result.write_videofile(prefix + os.path.split(fname)[1])
