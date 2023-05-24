import requests
import re
import http.server
from http.server import BaseHTTPRequestHandler
from lib.xiino_html_converter import XiinoHTMLParser
import base64

import yattag


def iso8859(string: str) -> bytes:
    "Shorthand to convert a string to iso-8859"
    return bytes(string, encoding="iso-8859-1")


class XiinoDataServer(BaseHTTPRequestHandler):
    DATASERVER_VERSION = "Pre-Alpha Development Release"

    COLOUR_DEPTH_REGEX = re.compile(r"\/c([0-9]*)\/")
    GSCALE_DEPTH_REGEX = re.compile(r"\/g([0-9]*)\/")
    SCREEN_WIDTH_REGEX = re.compile(r"\/w([0-9]*)\/")
    TXT_ENCODING_REGEX = re.compile(r"\/[de]{1,2}([a-zA-Z0-9-]*)\/")
    URL_REGEX = re.compile(r"\/\?(.*)\s")  # damn, length sync broken :(

    REQUESTS_HEADER = {
        "User-Agent": "OpenXiino/1.0 (http://github.com/nicl83/openxiino) python-requests/2.27.1"
    }

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        url = self.URL_REGEX.search(self.requestline)

        # send magic padding xiino expects
        self.wfile.write(bytes([0x00] * 12))
        self.wfile.write(bytes([0x0D, 0x0A] * 2))
        # TODO: real actual websites
        if url:
            print(url)
            url = url.group(1)
            if url == "http://about/":
                self.about()
            elif url == "http://github/":
                self.github()
            elif url == "http://about2/":
                self.more_info()
            elif url == "http://deviceinfo/":
                self.device_info()
            else:
                print(url)
                response = requests.get(url, headers=self.REQUESTS_HEADER, timeout=5)
                parser = XiinoHTMLParser(base_url=response.url)
                print(response.url)
                parser.feed(response.text)
                clean_html = parser.get_parsed_data()
                self.wfile.write(clean_html.encode("latin-1", errors="ignore"))

        else:
            self.wfile.write(
                "Invalid request! Please contact the devs.".encode("latin-1")
            )
            self.wfile.write(f"<br>Request: {self.requestline}".encode("latin-1"))

    def about(self):
        "Show the About screen."
        self.__internal_file_page_handler("about.html")

    def github(self):
        "Show a QR code linking to my GitHub."
        self.__internal_file_page_handler("github.html")

    def more_info(self):
        "Show more info about OpenXiino."
        self.__internal_file_page_handler("about2.html")

    def device_info(self):
        "Show info about the device making the request."
        colour_depth = self.COLOUR_DEPTH_REGEX.search(self.requestline)
        gscale_depth = self.GSCALE_DEPTH_REGEX.search(self.requestline)
        screen_width = self.SCREEN_WIDTH_REGEX.search(self.requestline)
        txt_encoding = self.TXT_ENCODING_REGEX.search(self.requestline)
        infopage = yattag.Doc()
        with infopage.tag("html"):
            infopage.line("title", "Device Info")
            with infopage.tag("body"):
                infopage.line("h1", "Device Info")
                with infopage.tag("ul"):
                    if colour_depth:
                        depth = colour_depth.group(1)
                        with infopage.tag("li"):
                            infopage.line("b", f"{depth}-bit colour ")
                            infopage.text("reported by Xiino.")
                    elif gscale_depth:
                        depth = gscale_depth.group(1)
                        with infopage.tag("li"):
                            infopage.line("b", f"{depth}-bit grayscale ")
                            infopage.text("reported by Xiino.")
                    else:
                        with infopage.tag("li"):
                            infopage.text("Your device isn't reporting a colour depth!")
                            infopage.text(
                                "Please tell the OpenXiino devs about your Xiino version."
                            )

                    if screen_width:
                        width = screen_width.group(1)
                        with infopage.tag("li"):
                            infopage.line("b", f"{width}px ")
                            infopage.text("viewport reported by Xiino. ")
                            if int(width) > 153:
                                infopage.text("This is a high-density device.")
                    else:
                        with infopage.tag("li"):
                            infopage.text("Your device isn't reporting a screen width!")
                            infopage.text(
                                "Please tell the OpenXiino devs about your Xiino version."
                            )

                    if txt_encoding:
                        encoding = txt_encoding.group(1)
                        with infopage.tag("li"):
                            infopage.text("Your text encoding is set to ")
                            infopage.stag("br")
                            infopage.line("b", str(encoding))
                    else:
                        with infopage.tag("li"):
                            infopage.text("Your device isn't reporting an encoding!")
                            infopage.text(
                                "Please tell the OpenXiino devs about your Xiino version."
                            )

                infopage.line("h2", "Request Headers")
                infopage.line("pre", self.headers.as_string())

        self.wfile.write(infopage.getvalue().encode("latin-1", errors="replace"))

    def __internal_file_page_handler(self, filename: str):
        "Load a page from the server's own files."
        with open(filename, encoding="utf-8") as handle:
            self.wfile.write(handle.read().encode("latin-1", errors="replace"))


if __name__ == "__main__":
    web_server = http.server.HTTPServer(("0.0.0.0", 4040), XiinoDataServer)
    print("Dataserver running on port 4040")
    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        pass

    web_server.server_close()
    print("Dataserver stopped.")
