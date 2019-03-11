from graph_creation.file_processor.fileProcessor import FileProcessor
from graph_creation.Types.readerType import ReaderType
from graph_creation.Types.infileType import InfileType
from graph_creation.metadata_infile.mapping.inMetaMapDrugCentralPubchem import InMetaMapDrugCentralPubchem



class MapDrugCentralPubchemProcessor(FileProcessor):
    IN_META_CLASS = InMetaMapDrugCentralPubchem

    def __init__(self):
        self.use_cols = self.IN_META_CLASS.USE_COLS
        super().__init__(self.use_cols, readerType=ReaderType.READER_MAP_DRUGCENTRAL_PUBCHEM,
                         infileType=InfileType.IN_MAP_DRUGCENTRAL_PUBCHEM, mapping_sep=self.IN_META_CLASS.MAPPING_SEP)

    def individual_preprocessing(self, data):
        data = data[data.id_type == 'PUBCHEM_CID']
        return data