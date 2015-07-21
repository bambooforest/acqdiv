# table definitions

# TODO: set the correct values nullable, unique, etc.
# TODO: pull out the Speakers from Session info into a separate table

import sqlalchemy as sa
import sqlalchemy.ext.declarative

create_engine = sa.create_engine


class Model(sa.ext.declarative.declarative_base()):

    __abstract__ = True

class Corpus(Model):

    __tablename__ = 'Corpus'

    PK = sa.Column(sa.Integer, primary_key=True)
    Name = sa.Column(sa.Text, nullable=False, unique=True)


class Session(Model):
    __tablename__ = 'Sessions'

    # fk...
    # SessionID = sa.Column(sa.Text, nullable=False, unique=True)

    SessionID = sa.Column(sa.Text, nullable=False, unique=True)
    Language = sa.Column(sa.Text, nullable=False, unique=True)
    CorpusName = sa.Column(sa.Text, ForeignKey('Corpus.Name'))
    SessionDate = sa.Column(sa.Text, nullable=False, unique=True)
    SessionGenre = sa.Column(sa.Text, nullable=False, unique=True)
    SessionSituation = sa.Column(sa.Text, nullable=False, unique=True)
    SessionAddress = sa.Column(sa.Text, nullable=False, unique=True)
    SessionContinent = sa.Column(sa.Text, nullable=False, unique=True)
    SessionCountry = sa.Column(sa.Text, nullable=False, unique=True)

    Corpus = sa.relationship('Corpus', backref=backref('Sessions', order_by=SessionID))

class Speaker(Model):
    __tablename__ = 'Speakers'

    SessionID = sa.Column(sa.Text, ForeignKey('Sessions.SessionID'))
    SpeakerLabel = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerName = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerAgeInDays = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerAge = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerBirthday = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerGender = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerRole = sa.Column(sa.Text, nullable=False, unique=True)

    Session = sa.relationship('Session', backref=backref('Speakers', order_by=SpeakerLabel))



class Utterance(Model):
    __tablename__ = 'Utterances'

    pk = sa.Column(sa.Integer, primary_key=True)
    SessionID = sa.Column(sa.Text, ForeignKey('Sessions.SessionID'))
    Fingerprint = sa.Column(sa.Text, nullable=False, unique=True)
    ID = sa.Column(sa.Text, nullable=False, unique=True)
    OriginalID = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerID = sa.Column(sa.Text, nullable=False, unique=True)
    SpeakerLabel = sa.Column(sa.Text, nullable=False, unique=True)
    Addressee = sa.Column(sa.Text, nullable=False, unique=True)
    TimeStampStart = sa.Column(sa.Text, nullable=False, unique=True)
    TimeStampEnd = sa.Column(sa.Text, nullable=False, unique=True)
    UtteranceOrthographic = sa.Column(sa.Text, nullable=False, unique=True)
    UtterancePhonetic = sa.Column(sa.Text, nullable=False, unique=True)
    SentenceType = sa.Column(sa.Text, nullable=False, unique=True)
    Translation = sa.Column(sa.Text, nullable=False, unique=True)
    Comment = sa.Column(sa.Text, nullable=False, unique=True)
    Morphemes = sa.Column(sa.Text, nullable=False, unique=True) # concatenated MorphemeIDs per utterance
    Words = sa.Column(sa.Text, nullable=False, unique=True) # concatenated WordIDs per utterance

    Session = sa.relationship('Session', backref=backref('Utterances', order_by=id))

class Word(Model):
    __tablename__ = 'Words'

    # fk...
    # SessionID = sa.Column(sa.Text, nullable=False, unique=True)
    ID = sa.Column(sa.Text, nullable=False, unique=True)
    Word = sa.Column(sa.Text, nullable=False, unique=True)
    UtteranceID = sa.Column(sa.Text, ForeignKey('Utterances.ID'))
    Utterance = sa.relationship('Utterance',  backref=backref('Words', order_by=ID))

class Morpheme(Model):
    __tablename__ = 'Morphemes'

    # fk...
    # SessionID = sa.Column(sa.Text, nullable=False, unique=True)
    ID = sa.Column(sa.Text, nullable=False, unique=True)
    Morpheme = sa.Column(sa.Text, nullable=False, unique=True)
    Gloss = sa.Column(sa.Text, nullable=False, unique=True)
    POS = sa.Column(sa.Text, nullable=False, unique=True)
    WordID = sa.Column(sa.Text, ForeignKey('Words.ID'))
    Word = sa.relationship('Word', backref=backref('Morphemes', order_by=ID))
