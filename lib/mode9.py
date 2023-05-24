"Compress a PIL image using Xiino mode 9."
import PIL.Image
from lib.ebd_control_codes import CONTROL_CODES
from lib.xiino_palette_common import PALETTE

xiino_palette = PIL.Image.open("lib/paletised.png")


def compress_mode9(image: PIL.Image.Image):
    image = image.quantize(palette=xiino_palette).convert(
        "RGB"
    )  # quantise and then un-quantise
    data = list(image.getdata())
    rows = []
    buffer = bytearray()
    for y in range(0, image.height):
        rows.append(data[(y * image.width) : (y + 1) * image.width])

    for index, row in enumerate(rows):
        if index == 0:
            buffer.extend(compress_line(row, None, True))
        else:
            buffer.extend(compress_line(row, rows[index - 1], False))

    return bytes(buffer)


def compress_line(line: list, prev_line: list | None, first_line: bool):
    active_colour = 0x00
    buffer = bytearray()

    index = 0
    while index < len(line):
        pixel = line[index]

        lb_copy_length_a = 0
        lb_copy_length_b = 0
        lb_copy_length_c = 0

        if not first_line:
            # lookback compression
            # only applicable past first line

            # so there's three possibilities for "lookback" compression
            # one behind, directly above, one ahead
            # calculate all 3 and see which one saves the most space

            # see how much can be copied from previous line, offset -1
            while (
                index + lb_copy_length_a < len(line)
                and line[index + lb_copy_length_a]
                == prev_line[(index - 1) + lb_copy_length_a]
            ):
                lb_copy_length_a += 1

            # see how much can be copied from previous line, offset 0
            while (
                index + lb_copy_length_b < len(line)
                and line[index + lb_copy_length_b]
                == prev_line[(index) + lb_copy_length_b]
            ):
                lb_copy_length_b += 1

            # see how much can be copied from previous line, offset 1
            # special crash guard rail for this one
            while (index + 1) + lb_copy_length_c < len(line) and line[
                index + lb_copy_length_c
            ] == prev_line[(index + 1) + lb_copy_length_c]:
                lb_copy_length_c += 1

            # print("LOOKBACK TEST RUN RESULTS")
            # print(
            #     "OFFSET -1:",
            #     f"LEN {lb_copy_length_a}",
            #     f"DATA {prev_line[index-1:index-1+lb_copy_length_a]}",
            # )
            # print(
            #     "OFFSET 0:",
            #     f"LEN {lb_copy_length_b}",
            #     f"DATA {prev_line[index-1:index-1+lb_copy_length_b]}",
            # )
            # print(
            #     "OFFSET 1:",
            #     f"LEN {lb_copy_length_c}",
            #     f"DATA {prev_line[index-1:index-1+lb_copy_length_c]}",
            # )

        # RLE compression
        # less preferable
        if index + 1 > len(line) - 1:
            # bail here! we'll except if we try to check RLE viability!
            rle_length = 0
        elif line[index + 1] != pixel:
            # RLE does not apply here
            rle_length = 0
        else:
            rle_length = 0
            while (
                index + rle_length < len(line)
                and line[index + rle_length] == pixel
                # and gandalf the grey
                # and gandalf the white
                # and monty python and the holy grail's black knight
            ):
                rle_length += 1

        # and now, Fight to the Death:tm:
        # whichever of these compressed more data wins

        compare_dict = {
            "rle": rle_length,
            "lb_-1": lb_copy_length_a,
            "lb_0": lb_copy_length_b,
            "lb_1": lb_copy_length_c,
        }
        best_compression = max(compare_dict, key=compare_dict.get)

        if all(value == 0 for value in compare_dict.values()):
            # data can't be compressed
            # rle not applicable
            # and does not appear anywhere on previous line
            # just write the colour to the buffer
            active_colour = 0 if pixel not in PALETTE else PALETTE.index(pixel)
            buffer.append(active_colour)
        # HACK force RLE
        elif best_compression == "rle":
            active_colour = 0 if pixel not in PALETTE else PALETTE.index(pixel)
            buffer.append(active_colour)

            if rle_length >= 6:
                # RLE beyond 6 uses 6's code and a length
                buffer.append(CONTROL_CODES["RLE_6"])
                buffer.append(rle_length - 6)
            else:
                buffer.append(CONTROL_CODES[f"RLE_{rle_length}"])

            index += rle_length

        elif best_compression == "lb_-1":
            if 1 <= lb_copy_length_a <= 5:
                buffer.append(CONTROL_CODES[f"COPY_{lb_copy_length_a}_OFFSET_-1"])
            else:
                buffer.append(CONTROL_CODES["COPY_6_OFFSET_-1"])
                buffer.append(lb_copy_length_a - 6)
            index += lb_copy_length_a - 1

        elif best_compression == "lb_0":
            if 1 <= lb_copy_length_b <= 5:
                buffer.append(CONTROL_CODES[f"COPY_{lb_copy_length_b}_OFFSET_0"])
            else:
                buffer.append(CONTROL_CODES["COPY_6_OFFSET_0"])
                buffer.append(lb_copy_length_b - 6)
            index += lb_copy_length_b - 1

        elif best_compression == "lb_1":
            if 1 <= lb_copy_length_c <= 5:
                buffer.append(CONTROL_CODES[f"COPY_{lb_copy_length_c}_OFFSET_1"])
            else:
                buffer.append(CONTROL_CODES["COPY_6_OFFSET_1"])
                buffer.append(lb_copy_length_c - 6)
            index += lb_copy_length_c - 1

        index += 1

    return bytes(buffer)
