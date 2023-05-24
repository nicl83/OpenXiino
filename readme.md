# OpenXiino
An open-source replacement for the data server required by the Palm OS browser "Xiino".

Converts images from any format supported by Pillow to Xiino's proprietary format, and reduces HTML to only tags supported by Xiino. (`SCRIPT` tags are not included, as modern Javascript far exceeds the capabilities of Xiino.)

## Setup
1. You will need to have TCP/IP configured on your Palm OS device.
    - For devices with Wi-Fi or Bluetooth, see the [PalmDB guide](https://palmdb.net/help/internet-connect).
    - For older devices that lack wireless connectivity, I recommend [Softick PPP](https://palmdb.net/app/softick-ppp). This will require a USB or serial connection.
    - Other methods of connecting to the internet - such as through a GSM mobile phone - will work, as long as the dataserver host is reachable.
2. Install the requirements from `requirements.txt`. (`pip -r requirements.txt`)
3. Run the server. (`python dataserver.py`)  
The server will run on port 4040 - this cannot be changed at this time
4. If you haven't already, install [Xiino](https://palmdb.net/app/xiino) on your Palm OS device.
5. Press Menu on your Palm OS device. Go to Options > Prefs, and scroll down to "DataServer" (or similar). On v3.4.1, this is on Page 3. On all versions I have tested, the default is `pds.mobirus.com` or `pds.ilinx.com`. 
6. Change "DataServer" to `[ip]:4040`. For instance, if the DataServer host uses the IP address `192.168.1.5`, set the DataServer to `192.168.1.5:4040`. Click OK to close Prefs.
7. To test OpenXiino is working correctly, tap "Select", then tap "URL...". Enter `http://about/` as the URL. You should see a page with the OpenXiino logo.

## Known issues
- Images embedded into pages using `data:` will cause that page to fail to load.
- SVG images are not yet supported.
- Some images render garbled or otherwise incorrectly. 
    - If you find a page with such an image, please open an issue.
- Many images will have white "spots" on dark areas.
- Images will only be sent in colour, even if Xiino requests grayscale.

If you find an issue not listed here, please open an issue with the URL of the page that causes the issue, a description of the issue, and an exception traceback (if applicable).

## Disclaimer 1
This code was uploaded at ~1:30am as a Minimum Viable Product. It has many bugs. Expect Requests or Pillow to throw exceptions on many pages.

## Disclaimer 2.
As stated in `about.html`:

**This project does is not endorsed by or associated with Mobirus, Inc., ILINX, Inc., or Kazuho Oku.**