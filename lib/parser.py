import re
import os
import io
import json



KEY_TYPE = 'TYPE'
KEY_SIGNATURE = 'SIGNATURE'
KEY_HEADER = 'HEADER'
KEY_FOOTER = 'FOOTER'
KEY_PAGES = 'PAGES'
KEY_LAYERS = 'LAYERS'
KEY_LAYER_INFOS = 'LAYERINFO'
KEY_KEYWORDS = 'LEYWORDS'
KEY_LINKS = 'LINKS'


class SupernoteMetadata:
    def __init__(self):
        self.__note = {
            KEY_TYPE : None,
            KEY_SIGNATURE : None,
            KEY_HEADER : None,
            KEY_FOOTER : None,
            KEY_PAGES : None
        }

    @property
    def type(self):
        return self.__note[KEY_TYPE]
    
    @type.setter
    def type(self, value: str):
        self.__note[KEY_TYPE] = value

    @property
    def signature(self):
        return self.__note[KEY_SIGNATURE]
    
    @signature.setter
    def signature(self, value: str):
        self.__note[KEY_SIGNATURE] = value

    @property
    def header(self):
        return self.__note[KEY_HEADER]
    
    @header.setter
    def header(self, value: dict):
        self.__note[KEY_HEADER] = value

    @property
    def footer(self):
        return self.__note[KEY_FOOTER]
    
    @footer.setter
    def footer(self, value: dict):
        self.__note[KEY_FOOTER] = value

    @property
    def pages(self):
        return self.__note[KEY_PAGES]
    
    @pages.setter
    def pages(self, value: dict):
        self.__note[KEY_PAGES] = value

    def get_page_num(self):
        return len(self.__note[KEY_PAGES])
    
    def page_has_layer(self, page_num: int):
        if page_num < 0 or page_num >= self.get_page_num():
            raise IndexError(f'The page number passed has parameter is too low or too high')
        return self.__note[KEY_PAGES][page_num].get(KEY_LAYERS) is not None

    def serialize(self):
        return json.dumps(self.__note, indent=4, ensure_ascii=False)



class SupernoteParser:
    WORD_SIZE = 4
    FOOTER_POSITION = 4 # bottom up
    FIELD_PATTERN = r'<([^:<>]+):([^:<>]*)>'
    INFO_PATTERN = r"\"(\w+)\"#\"?([\w\d\s\-]+)\"?"
    SIGNATURE_SIZE = 20

    def __init__(self):
        self.bytestream = None
    
    def parse_metadata(self, file_name: str) -> SupernoteMetadata:
        with open(file_name, "rb") as note:
            return self._parse_stream(note)

    def get_content_by_address(self, address: str):
        self.bytestream.seek(address, os.SEEK_SET)
        block_lenght = int.from_bytes(self.bytestream.read(self.WORD_SIZE), "little")
        
        content = self.bytestream.read(block_lenght)

        return content

    def _parse_stream(self, stream) -> SupernoteMetadata:
        self.bytestream = io.BytesIO(stream.read())

        # Get filetype
        self.bytestream.seek(0, os.SEEK_SET)
        filetype = self.bytestream.read(self.WORD_SIZE).decode()

        # Get file signature
        self.bytestream.seek(0, os.SEEK_CUR)
        signature = self.bytestream.read(self.SIGNATURE_SIZE).decode()
        
        footer_metadata = self._get_footer(self.bytestream)
       
        header_address = footer_metadata['FILE_FEATURE']
        header_metadata = self._get_block_metadata(int(header_address), self.bytestream)

        pages_metadata = self._get_pages(footer_metadata, self.bytestream)

        metadata = SupernoteMetadata()
        metadata.type = filetype
        metadata.signature = signature
        metadata.header = header_metadata
        metadata.footer = footer_metadata
        metadata.pages = pages_metadata

        return metadata


    def _get_footer(self, stream: io.BytesIO) -> dict:
         # Parse footer block
        stream.seek(-self.FOOTER_POSITION, os.SEEK_END) # footer address is the last word
        footer_address = int.from_bytes(stream.read(self.WORD_SIZE), 'little')
        footer_metadata = self._get_block_metadata(footer_address, stream)
        
        keyword_addresses = self._get_block_addresses(footer_metadata, 'KEYWORD_')
        link_addresses = self._get_block_addresses(footer_metadata, 'LINKO_')
        
        keywords = list(map(lambda addr: self._get_block_metadata(int(addr), stream), keyword_addresses))
        links = list(map(lambda addr: self._get_block_metadata(int(addr), stream), link_addresses))

        footer_metadata[KEY_KEYWORDS] = keywords
        footer_metadata[KEY_LINKS] = links

        return footer_metadata


    def _get_pages(self, footer_metadata: dict, stream: io.BytesIO) -> dict:
        page_addresses = self._get_block_addresses(footer_metadata, 'PAGE')
        pages = list(map(lambda addr: self._get_block_metadata(int(addr), stream), page_addresses))

        for page in pages:
            layer_addresses = self._get_block_addresses(page, 'LAYER', check_numeric=True)
            layers = list(map(lambda addr: self._get_block_metadata(int(addr), stream), layer_addresses))
            layers_num = len(layers)
            layers_info = re.findall(r'\{.*?\}', page.get('LAYERINFO'))
            
            page.pop('LAYERINFO')
            
            main_bg_info = list(map(lambda x: self._extract_parameter(self.INFO_PATTERN, x), layers_info[-2:]))

            layers[0].update({KEY_LAYER_INFOS: main_bg_info[0]})
            layers[-1].update({KEY_LAYER_INFOS: main_bg_info[1]})
            
            if layers_num > 2:
                for layer in layers[1:-1]:
                    for info in layers_info[:-2]:
                        info_dict = self._extract_parameter(self.INFO_PATTERN, info)
                        name = "".join(info_dict.get('name').split(" ")).upper()
                        if layer.get('LAYERNAME') == name:
                            layer.update({KEY_LAYER_INFOS: info_dict})

            page[KEY_LAYERS] = layers
        
        return pages


    def _get_block_addresses(self, footer: dict, key: str, check_numeric=False) -> list:
        addresses = []

        for k, v in footer.items():
            if key in k:
                if check_numeric:
                    if str.isdigit(v):
                        if int(v) != 0:
                            addresses.append(v)
                else:
                    addresses.extend(v) if type(v) == list else addresses.append(v)
        return addresses


    def _get_block_metadata(self, address: int, stream: io.BytesIO) -> dict:
        stream.seek(address, os.SEEK_SET)
        block_lenght = int.from_bytes(stream.read(self.WORD_SIZE), "little")
        contents = stream.read(block_lenght)
        params = self._extract_parameter(self.FIELD_PATTERN, contents.decode())

        return params


    def _extract_parameter(self, pattern, metadata) -> dict:
        result = re.finditer(pattern, metadata)
        params = {}

        for match in result:
            key = match[1]
            value = match[2]
            if params.get(key):
                if type(params.get(key)) != list:
                    first_value = params.pop(key)
                    params[key] = [first_value, value]
                else:
                    params[key].append(value)
            else:
                params[key] = value
        
        return params
