"""
Experimental Scanline image compressor.
Based on the implementation by Palm, Inc.
"""
# pylint: disable=pointless-statement


def compress_scanline(
    line: bytes,
    prev_line: bytes | None,
    first_line: bool,
) -> bytes:
    """
    Compress a single line of a bitmap using Scanline compression.
    If this is not compressing the first line,
    the current line and previous line must be of equal length.
    (This should be true for sane images).
    If not, the function will throw an AssertionError.

    :param line: The data for the current line.
    :param prev_line: The data for the previous line.
    :param first_line: True if this is the first line of the image, otherwise false
    """
    if not first_line:
        assert len(line) <= len(
            prev_line
        ), "Mismatched lines passed to compress_scanline"
    width = len(line) - 8  # mimic C behaviour

    buffer = bytearray()

    line_index = 0

    if first_line:
        while width >= 0:
            buffer.append(0xFF)  # all bytes change on the first row
            buffer.extend(line[line_index : line_index + 8])
            line_index += 8
            width -= 8

        width += 8
        if width > 0:
            # "finish off any stragglers"
            # making a pre-emptive guess here, and truncating
            # header byte at 8 bits. happy to be proven wrong
            buffer.append(0xFF << (8 - width) & 0xFF)
            buffer.extend(line[line_index : line_index + width])
            line_index += width

    else:  # not the first line
        while width >= 0:  # process eight bytes at a time
            flags = 0x00
            changed_bytes_buffer = bytearray()

            for _ in range(0, 8):
                flags << 1
                if line[line_index] != prev_line[line_index]:
                    flags += 1
                    changed_bytes_buffer.append(line[line_index])
                line_index += 1

            assert flags < 0x100, "Flag assignment has gone wrong, check your logic"
            buffer.append(flags)
            buffer.extend(changed_bytes_buffer)
            width -= 8

        width += 8
        if width > 0:
            # damn stragglers
            flags = 0x00
            changed_bytes_buffer = bytearray()
            for _ in range(0, width):
                flags << 1
                if line[line_index] != prev_line[line_index]:
                    flags += 1
                    changed_bytes_buffer.append(line[line_index])
                line_index += 1
            # pad flags byte
            flags = flags << (8 - width)

            assert flags < 0x100, "Flag assignment has gone wrong, check your logic"
            buffer.append(flags)
            buffer.extend(changed_bytes_buffer)

    return bytes(buffer)


def compress_data_with_scanline(data: bytes, width: int) -> bytes:
    """
    Helpful wrapper to compress a block of data with Scanline,
    instead of one line at a time.

    :param data: Image data.
    :param width: Width of one row of the image, in bytes.
    """
    buffer = bytearray()

    # assert (
    #     len(data) % width == 0
    # ), f"Invalid width {width} for data of length {len(data)}"
    lines = list(__divide_chunks(data, width))

    for index, line in enumerate(lines):
        if index == 0:
            buffer.extend(compress_scanline(line, None, True))
        else:
            buffer.extend(compress_scanline(line, lines[index - 1], False))

    return buffer


def __divide_chunks(l, n: int):
    "Helper function for splitting things into chunks"
    for i in range(0, len(l), n):
        yield l[i : i + n]
