import mido
from grid_video.core import Note, Track, TrackAggregate

# TODO
# Change tempo detection. It should detect tempo changes mid-track


class NoTempoException(Exception):
    pass


class TrackBuffer:
    """Buffer for parsing. Ensures non-concurrency"""
    def __init__(self, tempo):

        self.buffer = Track()
        self.next_note = ()
        self.is_free = True
        self.last_timestamp = 0

        self.tempo = tempo
    
    def note_start(self, note, channel, timestamp):
        tick_difference = timestamp - self.last_timestamp
        if tick_difference > 0:
            self.buffer.append(Note('silence', tick_difference * self.tempo))
        
        self.next_note = (note, channel)
        self.is_free = False
        self.last_timestamp = timestamp

    def note_end(self, note, channel, timestamp):
        if (note, channel) != self.next_note:
            raise ValueError("Trying to end different note than the one started")
        
        self.buffer.append(Note(note, (timestamp - self.last_timestamp) * self.tempo))
        self.next_note = ()
        self.is_free = True
        self.last_timestamp = timestamp

    def force_note_end(self, timestamp):
        self.note_end(self.next_note[0], self.next_note[1], timestamp)



def find_tempo_information(mid, track):
    """Tries to extract length of a tick in seconds"""
    for msg in track:
        if msg.type == 'set_tempo':
            return msg.tempo / 1_000_000 / mid.ticks_per_beat
    raise NoTempoException("Couldn't find tempo data in given file. Implementation of this function is not very great, I'm sorry")


def track_iterator(track):
    starts = []
    ends = []
    misc = []
    for msg in track:
        pass


def parse_track(track, tempo):
    """
    Parses single MIDI track. Midi allows for concurrent sounds on a single track/channel, so this function returns
    a list of core.Track objects containing non-concurrent notes
    """

    buffers = []
    timestamp = 0
    for msg in track:
        timestamp += msg.time
        if msg.type == 'note_on' and msg.velocity != 0:
            for tb in buffers:
                if tb.is_free:
                    tb.note_start(msg.note, msg.channel, timestamp)
                    break
            else:
                tb = TrackBuffer(tempo)
                tb.note_start(msg.note, msg.channel, timestamp)
                buffers.append(tb)
        
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            for tb in buffers:
                if (msg.note, msg.channel) == tb.next_note:
                    tb.note_end(msg.note, msg.channel, timestamp)
                    break
            else:
                print("WARNING: Ending a non-started note")

    for tb in buffers:
        if not tb.is_free:
            tb.force_note_end(timestamp)

    return TrackAggregate([tb.buffer for tb in buffers])


def parse_midi(mid):
    """Parse the entire MIDI file. Returns a 2D list of core.Track"""  # TODO document it better

    # I'm gonna make the assumption that track 0 contains tempo information, and that tempo never changes
    tempo = find_tempo_information(mid, mid.tracks[0])
    result = TrackAggregate()
    for t in mid.tracks:
        result.append(parse_track(t, tempo))

    max_length = max([i[0].total_length() for i in result if len(i) > 0])
    result.pad_to_duration(max_length)
    return result


if __name__ == "__main__":
    m = mido.MidiFile('canonpiano.mid')
    res = parse_midi(m)
    utils.serialize_record(res, open('serialized_canon.picle', 'wb'))
    print('done')

