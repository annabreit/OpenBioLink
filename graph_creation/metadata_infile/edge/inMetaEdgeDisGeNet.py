from edgeType import EdgeType
from graph_creation.infileType import InfileType
from graph_creation.metadata_infile.infileMetadata import InfileMetadata
from nodeType import NodeType


class InMetaEdgeDisGeNet(InfileMetadata):
    CSV_NAME = "DB_DisGeNet_gene_disease.csv"
    USE_COLS = ['geneID', 'umlsID', 'score']
    NODE1_COL = 0
    NODE2_COL = 1
    QSCORE_COL = 2
    NODE1_TYPE = NodeType.GENE
    NODE2_TYPE = NodeType.DIS
    EDGE_TYPE = EdgeType.GENE_DIS
    INFILE_TYPE = InfileType.IN_EDGE_DISGENET
    MAPPING_SEP = None

    def __init__(self, folder_path):
        super().__init__(csv_name=InMetaEdgeDisGeNet.CSV_NAME,
                         folder_path=folder_path,
                         infileType=InMetaEdgeDisGeNet.INFILE_TYPE)