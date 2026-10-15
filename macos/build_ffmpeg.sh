#!/bin/bash
# Build the ffmpeg and ffprobe that Oncemore.app carries, so the app needs
# nothing installed beside it (DECISIONS §130).
#
#   macos/build_ffmpeg.sh <out-dir>
#
# Static programs from pinned, checksum-verified sources: FFmpeg with x264
# (H.264 for Blu-ray and the web version) and FreeType + HarfBuzz (drawtext,
# the menu text). Everything else FFmpeg needs is in FFmpeg itself or in
# macOS (zlib, bzip2, iconv); nothing is linked from Homebrew. With x264 the
# programs are GPL, which fits oncemore's GPL-3.0; the sources are copied to
# <out-dir>/sources so a release can carry them.
#
# <out-dir> gets ffmpeg, ffprobe, licenses/, sources/ and README.txt.
# Built once per architecture and kept in FFMPEG_CACHE (default
# dist/.cache/ffmpeg); a change to this script builds again.
#
# Needs: a C compiler, make, pkg-config, meson + ninja (HarfBuzz), and nasm
# on Intel. Runs on Linux too (to try the configuration), where it makes
# Linux programs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="${1:?usage: build_ffmpeg.sh <out-dir>}"
ARCH="${ARCH:-$(uname -m)}"
CACHE="${FFMPEG_CACHE:-$ROOT/dist/.cache/ffmpeg}"
JOBS="$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

FFMPEG_VERSION=9.0.2
X264_COMMIT=b35605ace3ddf7c1a5d67a2eb553f034aef41d55   # the stable branch, 2025-06-08
FREETYPE_VERSION=2.15.0
HARFBUZZ_VERSION=14.6.0

# file  sha256  url
SOURCES="
ffmpeg-$FFMPEG_VERSION.tar.xz 8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e https://ffmpeg.org/releases/ffmpeg-$FFMPEG_VERSION.tar.xz
x264-$X264_COMMIT.tar.bz2 6eeb82934e69fd51e043bd8c5b0d152839638d1ce7aa4eea65a3fedcf83ff224 https://code.videolan.org/videolan/x264/-/archive/$X264_COMMIT/x264-$X264_COMMIT.tar.bz2
freetype-$FREETYPE_VERSION.tar.xz 93cd47eb719c325107f2d3cf087d06299e944c3b48a40b55537302304dea1dd5 https://download.savannah.gnu.org/releases/freetype/freetype-$FREETYPE_VERSION.tar.xz
harfbuzz-$HARFBUZZ_VERSION.tar.xz d07a007327277708a2a73ae437887cdbaf282937f6d03ca5467723e9099af586 https://github.com/harfbuzz/harfbuzz/releases/download/$HARFBUZZ_VERSION/harfbuzz-$HARFBUZZ_VERSION.tar.xz
"

FFMPEG_CONFIGURE=(
  --enable-gpl --enable-libx264 --enable-libfreetype --enable-libharfbuzz
  --disable-autodetect --enable-zlib --enable-bzlib --enable-iconv
  --disable-network --disable-ffplay --disable-doc --disable-debug
  --enable-static --disable-shared --pkg-config-flags=--static
)

sha256() {
  if command -v shasum >/dev/null; then shasum -a 256 "$1"; else sha256sum "$1"; fi | cut -d' ' -f1
}

# the cache key: this script (versions, checksums, flags) and the architecture
STAMP="$(sha256 "$0" | cut -c1-16)-$ARCH"
WORK="$CACHE/$STAMP"
PREFIX="$WORK/prefix"
mkdir -p "$CACHE/src"

echo "==> sources"
while read -r file sum url; do
  [ -n "$file" ] || continue
  dest="$CACHE/src/$file"
  if [ ! -f "$dest" ] || [ "$(sha256 "$dest")" != "$sum" ]; then
    curl -fsSL --retry 3 -o "$dest.part" "$url"
    mv "$dest.part" "$dest"
  fi
  got="$(sha256 "$dest")"
  [ "$got" = "$sum" ] || { echo "checksum mismatch for $file: $got" >&2; rm -f "$dest"; exit 1; }
done <<< "$SOURCES"

if [ ! -x "$PREFIX/bin/ffmpeg" ] || [ ! -x "$PREFIX/bin/ffprobe" ]; then
  rm -rf "$WORK"
  mkdir -p "$WORK/build" "$PREFIX"
  B="$WORK/build"
  if [ "$(uname -s)" = Darwin ]; then
    export MACOSX_DEPLOYMENT_TARGET=12.0
    export CC="clang -arch $ARCH" CXX="clang++ -arch $ARCH"
  fi
  export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"
  export PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig"   # only what is built here

  echo "==> x264"
  tar -xjf "$CACHE/src/x264-$X264_COMMIT.tar.bz2" -C "$B"
  (cd "$B/x264-$X264_COMMIT" &&
    ./configure --prefix="$PREFIX" --enable-static --disable-cli --enable-pic \
      --disable-opencl --disable-lavf --disable-swscale --disable-ffms --disable-gpac \
      --disable-lsmash &&
    make -j"$JOBS" && make install)

  echo "==> FreeType"
  tar -xJf "$CACHE/src/freetype-$FREETYPE_VERSION.tar.xz" -C "$B"
  (cd "$B/freetype-$FREETYPE_VERSION" &&
    ./configure --prefix="$PREFIX" --enable-static --disable-shared --with-pic \
      --with-zlib=no --with-bzip2=no --with-png=no --with-harfbuzz=no --with-brotli=no &&
    make -j"$JOBS" && make install)

  echo "==> HarfBuzz"
  tar -xJf "$CACHE/src/harfbuzz-$HARFBUZZ_VERSION.tar.xz" -C "$B"
  (cd "$B/harfbuzz-$HARFBUZZ_VERSION" &&
    meson setup build --prefix="$PREFIX" --libdir=lib --buildtype=release \
      --default-library=static -Dfreetype=enabled -Dglib=disabled -Dgobject=disabled \
      -Dcairo=disabled -Dchafa=disabled -Dpng=disabled -Dzlib=disabled -Dicu=disabled \
      -Dgraphite2=disabled -Dcoretext=disabled -Draster=disabled -Dvector=disabled \
      -Dgpu=disabled -Dgpu_demo=disabled -Dsubset=disabled -Dtests=disabled \
      -Dintrospection=disabled -Ddocs=disabled -Dutilities=disabled -Dbenchmark=disabled &&
    meson compile -C build -j "$JOBS" && meson install -C build)

  echo "==> FFmpeg $FFMPEG_VERSION"
  tar -xJf "$CACHE/src/ffmpeg-$FFMPEG_VERSION.tar.xz" -C "$B"
  (cd "$B/ffmpeg-$FFMPEG_VERSION" &&
    ./configure --prefix="$PREFIX" ${CC:+--cc="$CC"} ${CXX:+--cxx="$CXX"} \
      --extra-cflags="-I$PREFIX/include" --extra-ldflags="-L$PREFIX/lib" \
      "${FFMPEG_CONFIGURE[@]}" &&
    make -j"$JOBS" && make install)
  strip "$PREFIX/bin/ffmpeg" "$PREFIX/bin/ffprobe"

  # licences of what is inside the programs
  L="$PREFIX/licenses"
  mkdir -p "$L"
  cp "$B/ffmpeg-$FFMPEG_VERSION/COPYING.GPLv2" "$L/FFmpeg-COPYING.GPLv2"
  cp "$B/ffmpeg-$FFMPEG_VERSION/LICENSE.md" "$L/FFmpeg-LICENSE.md"
  cp "$B/x264-$X264_COMMIT/COPYING" "$L/x264-COPYING"
  cp "$B/freetype-$FREETYPE_VERSION/LICENSE.TXT" "$L/FreeType-LICENSE.TXT"
  cp "$B/freetype-$FREETYPE_VERSION/docs/GPLv2.TXT" "$L/FreeType-GPLv2.TXT"
  cp "$B/harfbuzz-$HARFBUZZ_VERSION/COPYING" "$L/HarfBuzz-COPYING"
  rm -rf "$B"
fi

echo "==> checking the programs"
"$PREFIX/bin/ffmpeg" -hide_banner -filters | grep -qE '^\s*\S+\s+drawtext\s' \
  || { echo "ffmpeg has no drawtext" >&2; exit 1; }
"$PREFIX/bin/ffmpeg" -hide_banner -encoders | grep -qE '^\s*V\S*\s+libx264\s' \
  || { echo "ffmpeg has no libx264" >&2; exit 1; }
if [ "$(uname -s)" = Darwin ]; then
  # only system libraries: nothing from Homebrew or this build's prefix
  if otool -L "$PREFIX/bin/ffmpeg" "$PREFIX/bin/ffprobe" | tail -n +2 \
      | grep -vE '^\S|^\s+(/usr/lib/|/System/Library/)'; then
    echo "the programs link libraries outside macOS" >&2; exit 1
  fi
fi

rm -rf "$OUTDIR"
mkdir -p "$OUTDIR/sources"
cp "$PREFIX/bin/ffmpeg" "$PREFIX/bin/ffprobe" "$OUTDIR/"
cp -R "$PREFIX/licenses" "$OUTDIR/licenses"
while read -r file sum url; do
  [ -n "$file" ] && cp "$CACHE/src/$file" "$OUTDIR/sources/"
done <<< "$SOURCES"
cat > "$OUTDIR/README.txt" <<EOF
ffmpeg and ffprobe for oncemore

FFmpeg $FFMPEG_VERSION (https://ffmpeg.org) with x264 ($X264_COMMIT),
FreeType $FREETYPE_VERSION and HarfBuzz $HARFBUZZ_VERSION, built by
macos/build_ffmpeg.sh in oncemore's repository
(https://github.com/kajisho5/oncemore). Configured with:

  ${FFMPEG_CONFIGURE[*]}

Because x264 is included, these programs are licensed under the GNU General
Public License, version 2 or later (licenses/FFmpeg-COPYING.GPLv2). FreeType
is used under the GPLv2 option of its licence, HarfBuzz under its own
licence (licenses/). The source code of all four, exactly as built, is
attached to each oncemore release on GitHub, next to the app.
EOF
du -sh "$OUTDIR/ffmpeg" "$OUTDIR/ffprobe"
echo "==> $OUTDIR"
