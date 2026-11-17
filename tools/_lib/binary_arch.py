"""Read the architecture out of an ELF, Mach-O, or PE container.

A wheel whose filename says `x86_64` can carry an `aarch64` extension: maturin
with a cross toolchain takes the host architecture for the tag while the
payload is whatever the compiler produced, or the reverse. The published wheel
then installs on the wrong platform and fails at import, after the release.
A container SHA-256 cannot detect that, because it says nothing about what is
inside. This reads the few header fields needed and nothing else.

Deliberately hand-rolled: `readelf` and `file` are not guaranteed present in
every environment this template targets, and the formats need a dozen bytes
each.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

_ELF_MAGIC = b"\x7fELF"
_MACHO_MAGICS: frozenset[bytes] = frozenset(
    {
        b"\xfe\xed\xfa\xce",  # 32-bit big-endian
        b"\xce\xfa\xed\xfe",  # 32-bit little-endian
        b"\xfe\xed\xfa\xcf",  # 64-bit big-endian
        b"\xcf\xfa\xed\xfe",  # 64-bit little-endian
        b"\xca\xfe\xba\xbe",  # fat/universal (same as Java class; disambiguated by offset)
    }
)
_PE_MAGIC = b"MZ"
_ELF_HEADER_BYTES = 20
_MACHO_HEADER_BYTES = 8
_PE_LFANEW_OFFSET = 0x3C
_PE_MIN_BYTES = 24

# ELF e_machine values.
_EM_X86_64 = 62
_EM_AARCH64 = 183
# Mach-O cputype values.
_CPU_TYPE_X86_64 = 0x01000007
_CPU_TYPE_ARM64 = 0x0100000C
# PE machine values.
_PE_MACHINE_AMD64 = 0x8664
_PE_MACHINE_ARM64 = 0xAA64

_ELF32 = 1
_ELF64 = 2


@dataclass(frozen=True)
class PayloadArch:
    """What a container declares about itself."""

    container: str
    arch: str
    detail: str

    @property
    def is_known(self) -> bool:
        """True when the architecture was recognised."""
        return self.arch != "unknown"


def _elf_arch(header: bytes) -> PayloadArch:
    if len(header) < _ELF_HEADER_BYTES:
        return PayloadArch("elf", "unknown", "truncated ELF header")
    elf_class = header[4]
    endian: Literal["little", "big"] = "little" if header[5] == 1 else "big"
    machine = int.from_bytes(header[18:20], endian)
    bits = {_ELF32: "32", _ELF64: "64"}.get(elf_class, "?")
    arch = {_EM_X86_64: "x86_64", _EM_AARCH64: "aarch64"}.get(machine, "unknown")
    return PayloadArch("elf", arch, f"ELF{bits} e_machine={machine} ({arch})")


def _macho_arch(header: bytes) -> PayloadArch:
    if len(header) < _MACHO_HEADER_BYTES:
        return PayloadArch("macho", "unknown", "truncated Mach-O header")
    magic = header[:4]
    if magic == b"\xca\xfe\xba\xbe":
        return PayloadArch("macho", "universal", "fat Mach-O (multiple architectures)")
    little = magic in (b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe")
    cputype = int.from_bytes(header[4:8], "little" if little else "big")
    arch = {_CPU_TYPE_X86_64: "x86_64", _CPU_TYPE_ARM64: "aarch64"}.get(cputype, "unknown")
    return PayloadArch("macho", arch, f"Mach-O cputype=0x{cputype:x} ({arch})")


def _pe_arch(data: bytes) -> PayloadArch:
    if len(data) < _PE_MIN_BYTES:
        return PayloadArch("pe", "unknown", "truncated DOS header")
    lfanew = int.from_bytes(data[_PE_LFANEW_OFFSET : _PE_LFANEW_OFFSET + 4], "little")
    pe_offset = lfanew + 4
    if len(data) < pe_offset + 2 or data[lfanew:pe_offset] != b"PE\0\0":
        return PayloadArch("pe", "unknown", "missing PE signature")
    machine = int.from_bytes(data[pe_offset : pe_offset + 2], "little")
    arch = {_PE_MACHINE_AMD64: "x86_64", _PE_MACHINE_ARM64: "aarch64"}.get(machine, "unknown")
    return PayloadArch("pe", arch, f"PE machine=0x{machine:x} ({arch})")


def read_payload_arch(data: bytes) -> PayloadArch:
    """Identify the container format and architecture from the leading bytes."""
    if data[:4] == _ELF_MAGIC:
        return _elf_arch(data)
    if data[:2] == _PE_MAGIC:
        return _pe_arch(data)
    if data[:4] in _MACHO_MAGICS:
        return _macho_arch(data)
    return PayloadArch("unknown", "unknown", "not an ELF, Mach-O, or PE container")


def read_file_payload_arch(path: Path) -> PayloadArch:
    """Read a container's architecture from disk."""
    with path.open("rb") as handle:
        head = handle.read(4096)
        if head[:2] != _PE_MAGIC:
            return read_payload_arch(head)
        handle.seek(0)
        return read_payload_arch(handle.read(4096))


# A suffix does not identify a container on its own: `.so` is ELF on Linux and
# Mach-O on macOS, which is exactly the distinction this module exists to make.
# Each suffix maps to every container it is allowed to hold.
_EXTENSION_CONTAINERS: dict[str, frozenset[str]] = {
    ".so": frozenset({"elf", "macho"}),
    ".pyd": frozenset({"pe"}),
    ".dylib": frozenset({"macho"}),
    ".dll": frozenset({"pe"}),
}
# A wheel's extension module must be importable, which rules out a bare dylib.
_UNIMPORTABLE_WHEEL_SUFFIXES: frozenset[str] = frozenset({".dylib", ".dll"})


def extension_containers(suffix: str) -> frozenset[str] | None:
    """Map an extension to the containers it may hold, if the extension is known."""
    return _EXTENSION_CONTAINERS.get(suffix.lower())


def tag_wants(platform_tag: str) -> tuple[str, str] | None:
    """Map a wheel platform tag to `(container, arch)`, or None when undecidable."""
    tag = platform_tag.lower()
    if tag.startswith("win"):
        return ("pe", "x86_64" if "amd64" in tag or "win_amd64" in tag else "aarch64")
    if tag.startswith("macosx"):
        if "universal2" in tag:
            return ("macho", "universal")
        return ("macho", "aarch64" if "arm64" in tag else "x86_64")
    if "linux" in tag:
        return ("elf", "aarch64" if "aarch64" in tag else "x86_64")
    return None
