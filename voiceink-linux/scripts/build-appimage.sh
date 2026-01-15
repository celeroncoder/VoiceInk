#!/bin/bash
# Build AppImage for VoiceInk
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build-appimage"
APPDIR="$BUILD_DIR/AppDir"

echo "Building VoiceInk AppImage..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build with meson
cd "$PROJECT_DIR"
meson setup "$BUILD_DIR/meson" --prefix=/usr
meson compile -C "$BUILD_DIR/meson"
DESTDIR="$APPDIR" meson install -C "$BUILD_DIR/meson"

# Install Python dependencies
pip install --target="$APPDIR/usr/lib/python3/dist-packages" \
    sounddevice numpy httpx keyring secretstorage

# Install the voiceink package
pip install --target="$APPDIR/usr/lib/python3/dist-packages" "$PROJECT_DIR"

# Download linuxdeploy if not present
LINUXDEPLOY="$BUILD_DIR/linuxdeploy-x86_64.AppImage"
if [ ! -f "$LINUXDEPLOY" ]; then
    wget -O "$LINUXDEPLOY" \
        "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
    chmod +x "$LINUXDEPLOY"
fi

# Download GTK plugin
GTK_PLUGIN="$BUILD_DIR/linuxdeploy-plugin-gtk.sh"
if [ ! -f "$GTK_PLUGIN" ]; then
    wget -O "$GTK_PLUGIN" \
        "https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/master/linuxdeploy-plugin-gtk.sh"
    chmod +x "$GTK_PLUGIN"
fi

# Create AppRun
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/lib/python3/dist-packages:${PYTHONPATH}"
export GI_TYPELIB_PATH="${HERE}/usr/lib/girepository-1.0:${GI_TYPELIB_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}"
export GSETTINGS_SCHEMA_DIR="${HERE}/usr/share/glib-2.0/schemas"

exec python3 -m voiceink "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Create desktop file in AppDir root
cp "$APPDIR/usr/share/applications/org.voiceink.VoiceInk.desktop" "$APPDIR/" 2>/dev/null || \
cat > "$APPDIR/org.voiceink.VoiceInk.desktop" << 'DESKTOP'
[Desktop Entry]
Name=VoiceInk
Comment=Voice-to-text transcription
Exec=voiceink
Icon=org.voiceink.VoiceInk
Type=Application
Categories=AudioVideo;Audio;Utility;
Keywords=voice;speech;transcription;whisper;
DESKTOP

# Create icon (placeholder if not exists)
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
if [ ! -f "$APPDIR/usr/share/icons/hicolor/256x256/apps/org.voiceink.VoiceInk.png" ]; then
    # Create a simple placeholder icon
    convert -size 256x256 xc:'#3584e4' \
        -gravity center -pointsize 72 -fill white \
        -annotate 0 "VI" \
        "$APPDIR/usr/share/icons/hicolor/256x256/apps/org.voiceink.VoiceInk.png" 2>/dev/null || \
    echo "Warning: Could not create icon, install ImageMagick for icon generation"
fi

# Link icon to AppDir root
ln -sf usr/share/icons/hicolor/256x256/apps/org.voiceink.VoiceInk.png "$APPDIR/"

# Build AppImage
cd "$BUILD_DIR"
export DEPLOY_GTK_VERSION=4
"$LINUXDEPLOY" --appdir "$APPDIR" --plugin gtk --output appimage

echo "AppImage built: $BUILD_DIR/VoiceInk-*.AppImage"
