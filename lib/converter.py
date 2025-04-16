from PIL import Image
from queue import LifoQueue

COLORCODE_BLACK = 0x61
COLORCODE_BACKGROUND = 0x62
COLORCODE_DARK_GRAY = 0x63
COLORCODE_GRAY = 0x64
COLORCODE_WHITE = 0x65
COLORCODE_MARKER_BLACK = 0x66
COLORCODE_MARKER_DARK_GRAY = 0x67
COLORCODE_MARKER_GRAY = 0x68


class Colormap:
    colormap = {
        COLORCODE_BLACK: 0x00,
        COLORCODE_BACKGROUND: 0xFF,
        COLORCODE_DARK_GRAY: 0x9D,
        COLORCODE_GRAY: 0xC9,
        COLORCODE_WHITE: 0x65,
        COLORCODE_MARKER_BLACK: 0x00, 
        COLORCODE_MARKER_DARK_GRAY: 0x9D,
        COLORCODE_MARKER_GRAY: 0xC9
    }

    def get_color(self, color_code: int) -> int | None:
        return self.colormap.get(color_code)


class Decoder:
    SPECIAL_LENGTH = 0x4000

    def decode(self, data, page_width: int, page_height: int, horizontal=False) -> bytes:
        content = data.get_content()

        if horizontal:
            page_height, page_width = (page_width, page_height)

        is_divisible = len(content) % 2 == 0

        if not is_divisible:
            raise Exception("Wrong content length")
        
        layer_as_tuples = list((content[i], content[i+1]) for i in range(0, len(content), 2))
        
        decoded_bitmap = bytearray()
        
        i = 0
        while i < len(layer_as_tuples):
            color, length = layer_as_tuples[i]

            if length == 0xFF:
                length = self.SPECIAL_LENGTH
            
            elif ((length & 0x80) != 0):
                next_color_code, next_length = layer_as_tuples[i+1]
                if color == next_color_code:
                    color = next_color_code
                    length = 1 + next_length + (((length & 0x7f) + 1) << 7)
                    i += 1
                else:
                    length = ((length & 0x7F) + 1) << 7
            else:
                length += 1
            
            i += 1

            decoded_bitmap.extend(self._create_color_bytearray(color, length))

        expected_length = page_height * page_width

        if len(decoded_bitmap) != expected_length:
            raise Exception(f"Decoded bitmap length {len(decoded_bitmap)} is different from expected lenght {expected_length}")

        return decoded_bitmap, (page_width, page_height)

    def _create_color_bytearray(self, color: int, length: int):
        colormap = Colormap()

        decoded_color = colormap.get_color(color)

        if decoded_color == None:
            # antialiasing pixels
            decoded_color = color
        
        return bytearray([decoded_color]) * length 

class Converter:
    def __init__(self):
        self.decoder = Decoder()

    def convert_to_pdf(self, notebook):
        pages_as_img = []
        layer_img_queue = LifoQueue()

        for page in notebook.get_pages():
            for layer in page.get_layers():
                layer_bitmap, size = self.decoder.decode(layer, notebook.get_page_width(), notebook.get_page_height(), page.is_horizontal())
                
                img = self._generate_image(layer_bitmap, size)

                if layer.get_name() != 'BGLAYER':
                    img = self._make_it_transparent(img)
                
                layer_img_queue.put(img)
            
            pages_as_img.append(self._flatten(layer_img_queue))

        pages_as_img[0].save(f'{notebook.get_filename()}.pdf', "PDF", resolution=100.0, save_all=True, append_images=pages_as_img[1:])


    def _generate_image(self, layer_bitmap: bytearray, size: tuple) -> Image:
        return Image.frombytes('L', size, layer_bitmap)


    def _make_it_transparent(self, image: Image) -> Image:
        transparent_image = Image.new('RGBA', image.size, (255, 255, 255, 0))
        mask = image.point(lambda x: 1 if x == 0xFF else 0, mode='1')
        image = image.convert('RGBA')
        
        return Image.composite(transparent_image, image, mask)
    

    def _flatten(self, image_queue: LifoQueue) -> Image:
        img = image_queue.get_nowait()

        while not image_queue.empty():
            current_layer = image_queue.get_nowait()
            img.paste(current_layer, img)
        
        return img

