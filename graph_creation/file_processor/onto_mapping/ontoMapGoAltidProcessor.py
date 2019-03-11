from graph_creation.file_processor.fileProcessor import FileProcessor
from graph_creation.Types.readerType import ReaderType
from graph_creation.Types.infileType import InfileType
from graph_creation.metadata_infile.mapping.inMetaMapOntoGoAltid import InMetaMapOntoGoAltid



class OntoMapGoAltidProcessor(FileProcessor):
    IN_META_CLASS = InMetaMapOntoGoAltid

    def __init__(self):
        self.use_cols = self.IN_META_CLASS.USE_COLS
        super().__init__(self.use_cols, readerType=ReaderType.READER_ONTO_GO,
                         infileType=InfileType.IN_MAP_ONTO_GO_ALT_ID, mapping_sep=self.IN_META_CLASS.MAPPING_SEP)