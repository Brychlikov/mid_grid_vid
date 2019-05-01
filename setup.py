from setuptools import setup

setup(name='grid_video',
      version='0.1',
      description='This thing makes grid-style music videos from a given set of one note clips',
      url='https://gitlab.com/Brych/mid_grid_vid',
      author='Brych',
      author_email='brychlikow@gmail.com',
      license='MIT',
      packages=['grid_video'],
      zip_safe=False,
      entry_points={
            'console_scripts': ['prepare_grid_audio=grid_video.cli:trim_clips',
                                'grid_video=grid_video.cli:main']
      },
      install_requires=[
            'moviepy',
            'numpy',
            'mido',
            'aubio'
      ])

