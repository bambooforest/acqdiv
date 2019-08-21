from acqdiv.util.MorphemeMappingCSVParser import MorphemeMappingCSVParser
from acqdiv.util.util import get_full_path


class YucatecGlossMapper:

    gloss_dict = MorphemeMappingCSVParser.parse(
                    get_full_path(
                        'parsers/corpora/main/yucatec/resources/gloss.csv'))

    @classmethod
    def map(cls, gloss):
        return cls.gloss_dict.get(gloss, '')