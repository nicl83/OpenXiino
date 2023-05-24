import requests
import random
from lib.xiino_image_converter import EBDConverter
from html.parser import HTMLParser
from urllib.parse import urljoin
from PIL import Image, UnidentifiedImageError
from io import BytesIO

supported_tags = [
    "A",
    "ADDRESS",
    "AREA",
    "B",
    "BASE",
    "BASEFONT",
    "BLINK",
    "BLOCKQUOTE",
    "BODY",
    "BGCOLOR",
    "BR",
    "CLEAR",
    "CENTER",
    "CAPTION",
    "CITE",
    "CODE",
    "DD",
    "DIR",
    "DIV",
    "DL",
    "DT",
    "FONT",
    "FORM",
    "FRAME",
    "FRAMESET",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "HR",
    "I",
    "IMG",
    "INPUT",
    "ISINDEX",
    "KBD",
    "LI",
    "MAP",
    "META",
    "MULTICOL",
    "NOBR",
    "NOFRAMES",
    "OL",
    "OPTION",
    "P",
    "PLAINTEXT",
    "PRE",
    "S",
    "SELECT",
    "SMALL",
    "STRIKE",
    "STRONG",
    "STYLE",
    "SUB",
    "SUP",
    "TABLE",
    "TD",
    "TH",
    "TR",
    "TT",
    "U",
    "UL",
    "VAR",
    "XMP",
]


class XiinoHTMLParser(HTMLParser):
    "Parse HTML to Xiino spec."

    def __init__(
        self,
        *,
        base_url,
        convert_charrefs: bool = True,
    ) -> None:
        self.parsing_supported_tag = True
        self.__parsed_data_buffer = ""
        self.ebd_image_tags = []
        self.base_url = base_url

        self.requests_headers = {
            "User-Agent": "OpenXiino/1.0 (http://github.com/nicl83/openxiino) python-requests/2.27.1"
        }

        super().__init__(convert_charrefs=convert_charrefs)

    def handle_starttag(self, tag, attrs):
        if tag.upper() in supported_tags:
            if tag == "img":
                # Put EBD logic here
                source_url = [attr[1] for attr in attrs if attr[0].lower() == "src"]
                if source_url:
                    true_url = source_url[0]
                    self.parse_image(true_url)
                else:
                    print(f"WARNING: IMG with no SRC at {self.base_url}")
            else:
                if tag == "a":
                    # fix up links for poor little browser
                    new_attrs = []
                    for attr in attrs:
                        if attr[0] == "href":
                            new_url = urljoin(self.base_url, attr[1])
                            if new_url.startswith("https:"):
                                new_url = new_url.replace("https:", "http:", 1)
                            new_attrs.append(("href", str(new_url)))
                        else:
                            new_attrs.append(attr)
                    attrs = new_attrs

                self.parsing_supported_tag = True
                self.__parsed_data_buffer += f"<{tag.upper()} "
                self.__parsed_data_buffer += " ".join(
                    f'{x[0].upper()}="{x[1]}"' for x in attrs
                )
                self.__parsed_data_buffer += ">\n"

        else:
            self.parsing_supported_tag = False

    def handle_data(self, data):
        if self.parsing_supported_tag:
            self.__parsed_data_buffer += data.strip()
            if len(data) > 0:
                self.__parsed_data_buffer += "\n"

    def handle_endtag(self, tag):
        if tag.upper() in supported_tags:
            self.__parsed_data_buffer += f"</{tag.upper()}>\n"

    def get_parsed_data(self):
        "Get the parsed data from the buffer, then clear it."
        for tag in self.ebd_image_tags:
            self.__parsed_data_buffer += tag + "\n"
        data = self.__parsed_data_buffer
        self.__parsed_data_buffer = ""
        self.ebd_image_tags = []
        return data

    def parse_image(self, url: str):
        full_url = urljoin(self.base_url, url)
        image_buffer = BytesIO(
            requests.get(full_url, timeout=5, headers=self.requests_headers).content
        )

        try:
            image = Image.open(image_buffer)
        except UnidentifiedImageError as exception_info:
            print("Warn: unsupported image due to unsupported format at", full_url)
            print(exception_info.args[0])
            self.__parsed_data_buffer += "<p>[Unsupported image]</p>"
            image_buffer.close()
            return

        # pre-filter images
        if image.width / 2 <= 1 or image.width / 2 <= 1:
            print("Warn: unsupported image due to being too small at", full_url)
            self.__parsed_data_buffer += "<p>[Unsupported image]</p>"
            return

        ebd_converter = EBDConverter(image)

        colour_data = ebd_converter.convert_colour(compressed=True)

        ebd_ref = len(self.ebd_image_tags) + 1  # get next "slot"
        self.__parsed_data_buffer += (
            colour_data.generate_img_tag(name=f"#{ebd_ref}") + "\n"
        )
        self.ebd_image_tags.append(colour_data.generate_ebdimage_tag(name=ebd_ref))
        image_buffer.close()


if __name__ == "__main__":
    page_data = requests.get("http://en.wikipedia.org", timeout=5).text
    parser = XiinoHTMLParser(base_url="http://en.wikipedia.org")
    parser.feed(page_data)
    with open("wikipedia.html", "w", encoding="latin-1", errors="ignore") as handle:
        handle.write(parser.get_parsed_data())
