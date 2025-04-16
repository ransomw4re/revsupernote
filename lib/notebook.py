from lib.converter import Converter
import lib.parser as sn

PAGE_HEIGHT = 1872
PAGE_WIDTH = 1404


class Layer:
    def __init__(self, metadata):
        self.metadata = metadata
        self.content = None

    def set_content(self, value: bytes) -> None:
        self.content = value

    def get_content(self) -> bytes:
        return self.content
    
    def get_type(self):
        return self.metadata['LAYERTYPE']
    
    def get_protocol(self):
        return self.metadata['LAYERPROTOCOL']
    
    def is_background(self):
        return self.metadata['LAYERNAME'] == 'BGLAYER'

    def get_name(self):
        return self.metadata['LAYERNAME']
    
    def get_bitmap_address(self):
        return int(self.metadata['LAYERBITMAP'])
    

class Page:
    HORIZONTAL = 1000
    VERTICAL = 1090

    def __init__(self, metadata):
        self.metadata = metadata
        self.layers = []
    
    def set_layer(self, layer: Layer):
        self.layers.append(layer)

    def get_layers(self) -> list:
        return self.layers
    
    def get_total_layers(self):
        return len(self.layers)

    def get_layer_sequence(self) -> str:
        return self.metadata['LAYERSEQ']

    def get_orientation(self) -> str:
        return self.metadata['ORIENTATION']
    
    def is_horizontal(self):
        return self.metadata['ORIENTATION'] == self.HORIZONTAL

    def get_page_id(self) -> str:
        return self.metadata['PAGEID']



class Notebook:
    def __init__(self, filename: str):
        _, extension = filename.split('.')
        if extension != 'note':
            raise Exception("Incompatilble file type, .note expected")

        self.parser = sn.SupernoteParser()
        self.file_path = filename
        self.metadata = self.parser.parse_metadata(self.file_path)
        self.json_metadata = self.metadata.serialize()
        self.page_height = PAGE_HEIGHT
        self.page_width = PAGE_WIDTH
        self.type = self.metadata.type
        self.signature = self.metadata.signature
        self.header = self.metadata.header
        self.footer = self.metadata.footer
        self.keywords = self.footer[sn.KEY_KEYWORDS] if self.footer[sn.KEY_KEYWORDS] is not None else []
        self.links = self.footer[sn.KEY_LINKS] if self.footer[sn.KEY_LINKS] is not None else []
        
        self.pages = []
        for page in self.metadata.pages:

            page_obj = Page(page)
            self.pages.append(page_obj)

            for layer in page.get(sn.KEY_LAYERS):
                layer_obj = Layer(layer)
                
                page_obj.set_layer(layer_obj)

                content = self.parser.get_content_by_address(layer_obj.get_bitmap_address())
                layer_obj.set_content(content)


    def get_filename(self):
        return self.file_path.split('.')[0]

    def get_page_height(self):
        return self.page_height

    def get_page_width(self):
        return self.page_width

    def get_pages(self):
        return self.pages
    
    def get_page(self, page_num: int) -> Page:
        if page_num < 0 or page_num > len(self.pages):
            raise IndexError(f"Index {page_num} out of bound")

        return self.pages[page_num]

    def export_pdf(self):
        conv = Converter()
        conv.convert_to_pdf(self)

    def print_metadata(self):
        print(self.json_metadata)

    def export_metadata(self, file_path: str):
        with open(file_path, "w") as out:
            out.write(self.json_metadata)

