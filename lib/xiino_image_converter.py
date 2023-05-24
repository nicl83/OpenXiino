"Classes for converting from PIL image to Xiino-format bytes."
import math
from base64 import b64encode
from dataclasses import dataclass
import PIL.Image
import PIL.ImageOps
import bitstring
import lib.scanline as scanline
import lib.mode9 as mode9
from lib.xiino_palette_common import PALETTE


@dataclass
class EBDImage:
    """
    An image that has been converted to an EBDIMAGE.
    """

    raw_data: bytes
    width: int
    height: int
    mode: int

    def generate_ebdimage_tag(self, name) -> str:
        "Generate an EBDIMAGE tag for the data of this image."
        base64 = b64encode(self.raw_data).decode("latin-1")
        return (
            f"""<EBDIMAGE MODE="{self.mode}" NAME="{name}"><!--{base64}--></EBDIMAGE>"""
        )

    def generate_img_tag(self, name, alt_text: str | None = None) -> str:
        "Generate an IMG tag for this image."
        return f"""<IMG ALT="{alt_text}" WIDTH="{self.width}" HEIGHT="{self.height}" EBDWIDTH="{self.width}" EBDHEIGHT="{self.height}" EBD="{name}">"""


class EBDConverter:
    """
    Convert from a PIL image to any of the modes known to be supported by Xiino.
    """

    def __init__(
        self, image: PIL.Image.Image | str, override_scale_logic: bool = False
    ) -> None:
        # Image is resized at class init to meet Xiino's specification.
        # To quote "HTMLSpecifications.txt":
        # Size WIDTH > 306pixel -> WIDTH = 153pixel（reduced to 153 pixels）
        # WIDTH <= 306pixel -> WIDTH = WIDTH * 0.5pixel（reduce to half the width）
        # HEIGHT is reduced to the same proportion as WIDTH.

        if isinstance(image, str):
            image = PIL.Image.open(image)

        if not override_scale_logic:
            if image.width > 306:
                new_width = 153
                new_height = math.ceil((image.height / image.width) * 153)
            else:
                new_width = math.ceil(image.width / 2)
                new_height = math.ceil(image.height / 2)

            image = image.resize((new_width, new_height))

        # discard transparency... this'll help later, trust me
        # do this by compositing the image onto a white background
        try:
            if image.mode == "RGBA":
                background = PIL.Image.new("RGBA", image.size, (255, 255, 255))
                self.image = PIL.Image.alpha_composite(background, image).convert("RGB")
            else:
                self.image = image.convert("RGB")  # Just in case :)
        except ValueError as exception_data:
            print(f"OH NO! Image composite fail?? {image.size}")
            raise exception_data

    def convert_bw(self, compressed: bool = False) -> EBDImage:
        """
        Convert the image to black and white (1-bit.)
        For greyscale, use `convert_gs`.
        """
        if compressed:
            return EBDImage(
                self.__convert_mode1(),
                width=self.image.width,
                height=self.image.height,
                mode=1,
            )
        return EBDImage(
            self.__convert_mode0(),
            width=self.image.width,
            height=self.image.height,
            mode=0,
        )

    def convert_gs(self, depth=4, compressed: bool = False) -> EBDImage:
        """
        Convert the image to greyscale.
        Defaults to 16-grey (4-bit) mode. For 4-grey (2-bit) mode,
        set `depth=2`.
        """
        if depth == 2:
            if compressed:
                return EBDImage(
                    self.__convert_mode3(),
                    width=self.image.width,
                    height=self.image.height,
                    mode=3,
                )
            return EBDImage(
                self.__convert_mode2(),
                width=self.image.width,
                height=self.image.height,
                mode=2,
            )
        elif depth == 4:
            if compressed:
                return EBDImage(
                    self.__convert_mode4(),
                    width=self.image.width,
                    height=self.image.height,
                    mode=4,
                )
            return EBDImage(
                self.__convert_mode5(),
                width=self.image.width,
                height=self.image.height,
                mode=5,
            )
        else:
            raise ValueError("Unsupported bit depth for greyscale.")

    def convert_colour(self, compressed: bool = False) -> EBDImage:
        "Convert the image to 8-bit (231 colour)."
        # TODO: uncompressed/mode8
        # not hard but getting burned out
        if compressed:
            return EBDImage(
                mode9.compress_mode9(self.image),
                width=self.image.width,
                height=self.image.height,
                mode=9,
            )
        return EBDImage(
            self.__convert_mode8(),
            width=self.image.width,
            height=self.image.height,
            mode=8,
        )

    def __convert_mode0(self) -> bytes:
        """
        Internal function for converting to mode0 (one-bit, no compression.)
        """
        buf = []
        im_bw = self.image.convert("1")
        for y in range(0, self.image.height):
            row_data = [im_bw.getpixel((x, y)) for x in range(0, self.image.width)]
            for chunk in self.__divide_chunks(row_data, 8):
                binary = bitstring.BitArray(bin="0b00000000")
                index = 0
                for pixel in chunk:
                    if pixel:
                        binary.set(False, index)
                    else:
                        binary.set(True, index)
                    index += 1
                buf.append(binary.uint)
        return bytes(buf)

    def __convert_mode1(self) -> bytes:
        """
        Internal function for converting to mode1 (one-bit, scanline compression)
        """
        # TODO writing a scanline converter is hurting my brain. later.
        return self.__convert_mode0()

    def __convert_mode2(self) -> bytes:
        """
        Internal function to convert to uncompressed two-bit grey.
        """
        buf = []
        im_gs = PIL.ImageOps.invert(self.image.convert("L"))
        raw_data = list(im_gs.getdata())
        for y in range(0, self.image.height):
            raw_data = [im_gs.getpixel((x, y)) for x in range(0, self.image.width)]
            for chunk in self.__divide_chunks(raw_data, 4):
                if len(chunk) == 1:
                    byte = math.floor(chunk[0] / 64) << 6
                elif len(chunk) == 2:
                    byte = (
                        math.floor(chunk[0] / 64) << 6 | math.floor(chunk[1] / 64) << 4
                    )
                elif len(chunk) == 3:
                    byte = (
                        math.floor(chunk[0] / 64) << 6
                        | math.floor(chunk[1] / 64) << 4
                        | math.floor(chunk[2] / 64) << 2
                    )
                elif len(chunk) == 4:
                    byte = (
                        math.floor(chunk[0] / 64) << 6
                        | math.floor(chunk[1] / 64) << 4
                        | math.floor(chunk[2] / 64) << 2
                        | math.floor(chunk[3] / 64)
                    )
                buf.append(byte)

        return bytes(buf)

    def __convert_mode3(self) -> bytes:
        """
        Internal function to convert to Scanline compressed two-bit grey.
        """
        width_bytes = math.ceil(self.image.width / 2)
        return scanline.compress_data_with_scanline(self.__convert_mode2(), width_bytes)

    def __convert_mode4(self) -> bytes:
        """
        Internal function to convert to uncompressed four-bit grey.
        """
        buf = []
        im_gs = PIL.ImageOps.invert(self.image.convert("L"))
        for y in range(0, self.image.height):
            raw_data = [im_gs.getpixel((x, y)) for x in range(0, self.image.width)]
            for chunk in self.__divide_chunks(raw_data, 2):
                byte = (round(chunk[0] / 16)) << 4 | (
                    0 if len(chunk) < 2 else round(chunk[1] / 16)
                ) << 0
                buf.append(byte)

        return bytes(buf)

    def __convert_mode5(self) -> bytes:
        """
        Internal function to convert to Scanline compressed four-bit grey.
        """
        width_bytes = math.ceil(self.image.width / 4)
        return scanline.compress_data_with_scanline(self.__convert_mode4(), width_bytes)

    def __convert_mode8(self) -> bytes:
        xiino_palette = PIL.Image.open("lib/paletised.png")
        image = self.image.quantize(palette=xiino_palette).convert("RGB")
        buf = bytearray()
        for px in image.getdata():
            if px in PALETTE:
                buf.append(PALETTE.index(px))
            else:
                buf.append(0xE6)
        return buf

    def __divide_chunks(self, l: list, n: int):
        "Helper function for splitting things into chunks"
        for i in range(0, len(l), n):
            yield l[i : i + n]


if __name__ == "__main__":
    im = PIL.Image.open("py_scripts/converter/test.jpg")
    xim = EBDConverter(im)
    with open("mode9.bin", "wb") as h:
        print(h.write(xim.convert_colour(compressed=True)))
    print(xim.image.width, xim.image.height)
