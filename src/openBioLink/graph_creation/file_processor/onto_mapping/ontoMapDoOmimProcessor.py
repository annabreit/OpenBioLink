from ...file_processor.fileProcessor import FileProcessor
from ...types.readerType import ReaderType
from ...types.infileType import InfileType
from ...metadata_infile.mapping.inMetaMapOntoDoOmim import InMetaMapOntoDoOmim



class OntoMapDoUmlsProcessor(FileProcessor):
    IN_META_CLASS = InMetaMapOntoDoOmim

    def __init__(self):
        self.use_cols = self.IN_META_CLASS.USE_COLS
        super().__init__(self.use_cols, readerType=ReaderType.READER_ONTO_DO,
                         infileType=InfileType.IN_MAP_ONTO_DO_OMIM, mapping_sep=self.IN_META_CLASS.MAPPING_SEP)