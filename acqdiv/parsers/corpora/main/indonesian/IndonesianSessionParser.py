from acqdiv.parsers.corpora.main.indonesian.IndonesianReader import \
    IndonesianReader
from acqdiv.parsers.metadata.CHATParser import CHATParser
from acqdiv.parsers.toolbox.ToolboxParser import ToolboxParser
from acqdiv.model.Speaker import Speaker
import os


class IndonesianSessionParser(ToolboxParser):

    def get_metadata_reader(self):
        return CHATParser(self.metadata_path)

    def add_session_metadata(self):
        self.session.source_id = os.path.splitext(os.path.basename(
            self.toolbox_path))[0]
        metadata = self.metadata_reader.metadata['__attrs__']
        self.session.date = metadata.get('Date', None)

        return self.session

    def add_speakers(self):
        for speaker_dict in self.metadata_reader.metadata['participants']:
            speaker = Speaker()
            speaker.birth_date = speaker_dict.get('birthday', None)
            speaker.gender_raw = speaker_dict.get('sex', None)
            speaker.code = speaker_dict.get('id', None)
            speaker.age_raw = speaker_dict.get('age', None)
            speaker.role_raw = speaker_dict.get('role', None)
            speaker.name = speaker_dict.get('name', None)
            speaker.languages_spoken = speaker_dict.get('language', None)

            self.session.speakers.append(speaker)

    def get_record_reader(self):
        return IndonesianReader(self.toolbox_path)
