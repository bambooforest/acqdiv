from acqdiv.parsers.corpora.main.dene.DeneReader import DeneReader
from acqdiv.parsers.metadata.IMDIParser import IMDIParser
from acqdiv.parsers.toolbox.ToolboxParser import ToolboxParser


class DeneParser(ToolboxParser):

    def get_record_reader(self):
        return DeneReader(self.toolbox_file)

    def get_metadata_reader(self):
        temp = self.toolbox_file.replace(self.config['paths']['sessions_dir'],
                                         self.config['paths']['metadata_dir'])
        metadata_file_path = temp.replace('.tbt', '.imdi')
        return IMDIParser(self.config, metadata_file_path)