"""Tests for the hand-rolled ELF / Mach-O / PE header reader.

Fixtures are synthesised here rather than committed, so the suite stays
text-only and the expected offsets are visible next to the assertion.
"""

from __future__ import annotations

import struct

import pytest

from tools._lib.binary_arch import extension_container, read_payload_arch, tag_wants

_ELF_64_LITTLE = 2
_ELF_64_BIG = 2


def _elf(machine: int, *, elf_class: int = _ELF_64_LITTLE, little: bool = True) -> bytes:
    """Build the leading bytes of an ELF header with a chosen e_machine."""
    order = "<" if little else ">"
    header = bytearray(20)
    header[0:4] = b"\x7fELF"
    header[4] = elf_class
    header[5] = 1 if little else 2
    header[18:20] = struct.pack(f"{order}H", machine)
    return bytes(header)


def _macho(cputype: int, *, little: bool = True) -> bytes:
    """Build a Mach-O header with a chosen cputype."""
    magic = b"\xcf\xfa\xed\xfe" if little else b"\xfe\xed\xfa\xcf"
    order = "<" if little else ">"
    return magic + struct.pack(f"{order}I", cputype) + b"\x00" * 4


def _pe(machine: int) -> bytes:
    """Build a minimal DOS + PE header carrying a machine field."""
    dos = bytearray(0x40)
    dos[0:2] = b"MZ"
    dos[0x3C:0x40] = struct.pack("<I", 0x40)
    pe = b"PE\0\0" + struct.pack("<H", machine) + b"\x00" * 14
    return bytes(dos) + pe


def test_elf_x86_64() -> None:
    """e_machine 62 is x86_64."""
    result = read_payload_arch(_elf(62))
    assert (result.container, result.arch) == ("elf", "x86_64")


def test_elf_aarch64() -> None:
    """e_machine 183 is aarch64; this is the mismatch a wrong tag hides."""
    result = read_payload_arch(_elf(183))
    assert (result.container, result.arch) == ("elf", "aarch64")


def test_elf_big_endian_machine_is_read_in_its_own_order() -> None:
    """The machine field follows the header's byte order, not the host's."""
    result = read_payload_arch(_elf(183, little=False))
    assert result.arch == "aarch64"


def test_macho_x86_64_and_arm64() -> None:
    """Mach-O cputype distinguishes Intel from Apple silicon."""
    assert read_payload_arch(_macho(0x01000007)).arch == "x86_64"
    assert read_payload_arch(_macho(0x0100000C)).arch == "aarch64"


def test_macho_universal_is_its_own_answer() -> None:
    """A fat binary is not one architecture, so it is not reported as one."""
    assert read_payload_arch(b"\xca\xfe\xba\xbe" + b"\x00" * 8).arch == "universal"


def test_pe_amd64_and_arm64() -> None:
    """The PE machine field lives behind the DOS stub pointer."""
    assert read_payload_arch(_pe(0x8664)).arch == "x86_64"
    assert read_payload_arch(_pe(0xAA64)).arch == "aarch64"


def test_non_container_is_unknown() -> None:
    """Random bytes are not silently assumed to be anything."""
    result = read_payload_arch(b"just some text, not a binary at all")
    assert result.container == "unknown"
    assert not result.is_known


def test_truncated_elf_is_unknown() -> None:
    """A short read must not crash or guess."""
    result = read_payload_arch(b"\x7fELF\x02\x01")
    assert not result.is_known


@pytest.mark.parametrize(
    ("suffix", "container"),
    [(".so", "elf"), (".pyd", "pe"), (".dylib", "macho"), (".dll", "pe"), (".bin", None)],
)
def test_extension_container_mapping(suffix: str, container: str | None) -> None:
    """Extensions imply a container, and an unknown extension implies nothing."""
    assert extension_container(suffix) == container


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("win_amd64", ("pe", "x86_64")),
        ("win_arm64", ("pe", "aarch64")),
        ("manylinux_2_28_x86_64", ("elf", "x86_64")),
        ("manylinux_2_28_aarch64", ("elf", "aarch64")),
        ("macosx_11_0_arm64", ("macho", "aarch64")),
        ("macosx_10_9_x86_64", ("macho", "x86_64")),
        ("musllinux_1_2_x86_64", ("elf", "x86_64")),
    ],
)
def test_tag_wants(tag: str, expected: tuple[str, str]) -> None:
    """A platform tag states both the container and the architecture."""
    assert tag_wants(tag) == expected


def test_unknown_tag_is_undecidable() -> None:
    """An unrecognised tag yields nothing rather than a wrong guess."""
    assert tag_wants("some_new_platform") is None
