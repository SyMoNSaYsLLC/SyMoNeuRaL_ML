# SyMoNeuRaL-View Professional

## Dependencies

### Python (>=3.10)
- PyQt6
- requests
- python-vlc (optional, for VLC playback backend)

### System (optional)
- ffmpeg (for recording)
- VLC (for playback)
- bcc (for XDP accelerator, requires root)

### Installation (Debian/Ubuntu)

```bash
# System Python dependencies
sudo apt install python3-pyqt6 python3-requests

# Optional: VLC playback backend
pip3 install python-vlc

# Optional: ffmpeg and VLC
sudo apt install ffmpeg vlc

# Optional: bcc for XDP
sudo apt install bpfcc-tools python3-bcc
```

### Usage

Run the application:

```bash
python3 usr/lib/symoneural-view/symoneural-view.py
```

Or if installed as a Debian package:

```bash
symoneural-view
```

### Notes

- For XDP acceleration, run as root and ensure bcc is installed.
- VLC playback will fall back to subprocess mode if python-vlc is not installed.

---

**For any issues, see the Troubleshooting section or contact the maintainer.**

# SyMoNeuRaL-View Integration with Yocto (meta-symoneural)

## Building SyMoNeuRaL-View into a Yocto Custom Image (Poky, No Distro)

### 1. Add SyMoNeuRaL-View to Your Layer

- Clone your application into your Yocto workspace, e.g.:
  ```bash
  git clone https://github.com/your-org/symoneural-view.git meta-symoneural/recipes-apps/symoneural-view
  ```

### 2. Create a Recipe

- In `meta-symoneural/recipes-apps/symoneural-view/`, create `symoneural-view.bb`:

  ```bitbake
  SUMMARY = "SyMoNeuRaL-View IPTV/Playlist Wizard"
  LICENSE = "MIT"
  SRC_URI = "file://symoneural-view"
  S = "${WORKDIR}/symoneural-view"

  inherit setuptools3

  RDEPENDS:${PN} += "python3-pyqt6 python3-requests"

  do_install() {
      install -d ${D}${bindir}
      cp -r ${S}/usr/lib/symoneural-view ${D}${bindir}/symoneural-view
      echo '#!/bin/sh\npython3 ${bindir}/symoneural-view/symoneural-view.py "$@"' > ${D}${bindir}/symoneural-view-launch
      chmod +x ${D}${bindir}/symoneural-view-launch
  }
  ```

### 3. Add Layer to Your Build

- Add `meta-symoneural` to your `bblayers.conf`:
  ```bash
  bitbake-layers add-layer ../meta-symoneural
  ```

### 4. Set the BSP (Board Support Package)

#### x86 (Generic PC)
```bash
MACHINE="qemux86-64"
```

#### ARM (Raspberry Pi, Firestick, Smart TV, etc.)
- **Raspberry Pi 4:**
  ```bash
  MACHINE="raspberrypi4"
  ```
- **Amazon Firestick (ARMv7):**
  ```bash
  MACHINE="armv7a-hf-neon"
  ```
  *(You may need a custom BSP or use a generic ARM machine as a starting point.)*
- **Smart TV (ARM, AArch64):**
  ```bash
  MACHINE="generic-armv8-64"
  ```
  *(Choose the closest match for your TV SoC, or use the vendor's BSP if available.)*

#### Other Boards
- See [Yocto BSPs](https://layers.openembedded.org/layerindex/branch/master/layers/) for more options.

### 5. Add to Custom Image Recipe

- In your custom image recipe (e.g. `recipes-core/images/symoneural-image.bb`):

  ```bitbake
  IMAGE_INSTALL += "symoneural-view"
  ```

### 6. Build Your Image

- Build with Poky (no distro):
  ```bash
  source oe-init-build-env
  bitbake symoneural-image
  ```

### 7. Run on Target

- After flashing your image, run:
  ```bash
  symoneural-view-launch
  ```

---

**Notes:**
- Ensure Python3, PyQt6, and requests are in your Yocto build.
- For customizations, extend your image recipe or layer as needed.

---

For more details, see [Yocto Project Documentation](https://www.yoctoproject.org/docs/).

---

## Running SyMoNeuRaL-View on Windows

### 1. Install Python

- Download and install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/).
- Add Python to your PATH during installation.

### 2. Install Dependencies

Open Command Prompt and run:
```cmd
pip install PyQt6 requests python-vlc
```

### 3. Run the Application

```cmd
python usr\lib\symoneural-view\symoneural-view.py
```

---

## Running SyMoNeuRaL-View on macOS

### 1. Install Python

- Use [Homebrew](https://brew.sh/) or download from [python.org](https://www.python.org/downloads/macos/):
  ```sh
  brew install python
  ```

### 2. Install Dependencies

```sh
pip3 install PyQt6 requests python-vlc
```

### 3. Run the Application

```sh
python3 usr/lib/symoneural-view/symoneural-view.py
```

---

## Notes

- On Windows, ensure VLC is installed for the VLC playback backend.
- For GUI issues, ensure your system has the required Qt platform plugins.

---

For troubleshooting and more details, contact the maintainer.

# SyMoNeuRaL-View Integration with OpenEmbedded (No Poky/Meta-Yocto)

## Building SyMoNeuRaL-View with OpenEmbedded and BitBake 2.8

### 1. Prepare OpenEmbedded Core

- Clone OpenEmbedded core (no Poky, no meta-yocto):
  ```bash
  git clone https://github.com/openembedded/openembedded-core.git
  cd openembedded-core
  ```

### 2. Add meta-symoneural Layer

- Place your layer in the `openembedded-core` directory:
  ```bash
  git clone https://github.com/your-org/meta-symoneural.git
  ```

### 3. Configure bblayers.conf

- Edit `conf/bblayers.conf` to include your layer:
  ```
  BBLAYERS ?= " \
    ${TOPDIR}/openembedded-core/meta \
    ${TOPDIR}/openembedded-core/meta-symoneural \
  "
  ```

### 4. Configure local.conf

- Set your target machine (BSP) in `conf/local.conf`:
  ```
  MACHINE ?= "qemux86-64"           # For x86
  # MACHINE ?= "raspberrypi4"       # For ARM/Raspberry Pi
  # MACHINE ?= "generic-armv8-64"   # For ARMv8/Smart TV
  ```

### 5. Add SyMoNeuRaL-View to Your Image

- Create a custom image recipe in `meta-symoneural/recipes-core/images/symoneural-image.bb`:
  ```bitbake
  SUMMARY = "SyMoNeuRaL Custom Image"
  LICENSE = "MIT"
  IMAGE_INSTALL += "symoneural-view"
  inherit core-image
  ```

### 6. Add SyMoNeuRaL-View Recipe

- In `meta-symoneural/recipes-apps/symoneural-view/symoneural-view.bb`:
  ```bitbake
  SUMMARY = "SyMoNeuRaL-View IPTV/Playlist Wizard"
  LICENSE = "MIT"
  SRC_URI = "file://symoneural-view"
  S = "${WORKDIR}/symoneural-view"

  inherit setuptools3

  RDEPENDS:${PN} += "python3-pyqt6 python3-requests"

  do_install() {
      install -d ${D}${bindir}
      cp -r ${S}/usr/lib/symoneural-view ${D}${bindir}/symoneural-view
      echo '#!/bin/sh\npython3 ${bindir}/symoneural-view/symoneural-view.py "$@"' > ${D}${bindir}/symoneural-view-launch
      chmod +x ${D}${bindir}/symoneural-view-launch
  }
  ```

### 7. Build with BitBake

- Initialize build environment:
  ```bash
  source ./oe-init-build-env
  ```
- Build your image:
  ```bash
  bitbake symoneural-image
  ```

### 8. Flash and Run

- Flash the image to your device.
- Boot and run:
  ```bash
  symoneural-view-launch
  ```

---

**Notes:**
- No Poky or meta-yocto required; only OpenEmbedded core and your custom layer.
- Ensure all Python and Qt dependencies are available in your layer or via upstream layers.
- For custom BSPs, add or modify machine configs in your layer.
- For advanced hardware, add required kernel modules and firmware to your image.

---

For more details, see [OpenEmbedded Documentation](https://www.openembedded.org/wiki/Main_Page).

# SyMoNeuRaL-View Dependencies Explained

Below is a list of all major dependencies, what they do, and what would be required if you want to remove or replace them.

---

## Python Dependencies

### PyQt6
- **What it does:** Provides the graphical user interface (GUI) framework for SyMoNeuRaL-View.
- **If you remove it:**
  - You must rewrite the entire UI using another toolkit (e.g., Tkinter, wxPython, Kivy, or a web frontend).
  - All QtWidgets, layouts, dialogs, and signals/slots must be replaced.

### requests
- **What it does:** Handles HTTP requests for Xtream API and EPG fetching.
- **If you remove it:**
  - Replace all HTTP calls with another library (e.g., `http.client`, `urllib`, or `aiohttp`).
  - Update all code that uses `requests.get`, `requests.post`, etc.

### python-vlc (optional)
- **What it does:** Provides the VLC playback backend via libvlc bindings.
- **If you remove it:**
  - Playback falls back to launching VLC as a subprocess.
  - The subprocess backend has fewer controls (no pause, volume, subtitles).

---

## Optional/Advanced Dependencies

### ffmpeg, VLC
- **What they do:** Provide media playback and recording capabilities.
- **If you remove them:**
  - Remove or replace playback/recording features.
  - Use another player or library (e.g., GStreamer, or a web-based player).

### bcc (for XDP accelerator)
- **What it does:** Enables network acceleration via eBPF/XDP (config toggle exists in UI).
- **If you remove it:**
  - Disable the XDP checkbox in settings.
  - Network acceleration will not be available.

---

## Summary Table

| Dependency         | Purpose                | Required | If Removed...                        |
|--------------------|-----------------------|----------|--------------------------------------|
| PyQt6              | GUI                   | Yes      | Rewrite UI with another toolkit      |
| requests           | HTTP requests         | Yes      | Use another HTTP library             |
| python-vlc         | VLC playback bindings | No       | Falls back to subprocess playback    |
| ffmpeg/VLC         | Playback/recording    | No       | Remove/replace playback features     |
| bcc                | Network acceleration  | No       | Disable XDP features                 |

---

**If you want to minimize dependencies, keep PyQt6 and requests. Everything else is optional.**

For further help, contact the maintainer.

# Advanced: Extending SyMoNeuRaL-View with Rust, C, or C++

## Adding Rust, C, or C++ Modules

- **Rust:**
  - Use [PyO3](https://pyo3.rs/) or [rust-cpython](https://github.com/dgrunwald/rust-cpython) to write fast, memory-safe modules for filtering, EPG parsing, or networking.
  - Add to your Yocto/OpenEmbedded recipe:
    ```bitbake
    inherit cargo
    ```
- **C/C++:**
  - Extend with SIMD, OpenMP, or GPU-accelerated filtering.
  - Add custom media codecs, hardware acceleration, or native UI widgets.
  - Note: `symon_fast_filter.cpp` and `xdp_accelerator.c` exist in the source tree as starting points.

## Building a Super-Tiny Image

- Use `core-image-minimal` as your base image in Yocto/OpenEmbedded.
- Remove all optional features (advanced playback, XDP, etc.).
- Only include Python, PyQt6, and your app.
- Example minimal image recipe:
  ```bitbake
  SUMMARY = "Minimal SyMoNeuRaL Image"
  LICENSE = "MIT"
  IMAGE_INSTALL += "python3 python3-pyqt6 symoneural-view"
  inherit core-image
  ```

## Kernel Examples & Suggestions

- **Standard Kernel Configs:**
  - For most embedded devices, use `linux-yocto` or `linux-raspberrypi` as your kernel provider.
  - Enable only required drivers (framebuffer, input, networking).
  - Example config fragment:
    ```
    CONFIG_FB=y
    CONFIG_DRM=y
    CONFIG_INPUT_EVDEV=y
    CONFIG_USB=y
    CONFIG_NETFILTER=y
    ```
- **Tiny Kernel:**
  - Use `CONFIG_EMBEDDED=y` and disable all unnecessary modules.
  - Remove sound, Bluetooth, and other unused subsystems.
  - Use [kernel config fragments](https://www.yoctoproject.org/docs/3.1/kernel-dev/kernel-dev.html#using-config-fragments) in your layer.

## Out-of-Tree Kernels for NVIDIA GPU

- **NVIDIA L4T (Linux for Tegra):**
  - Use NVIDIA's BSP for Jetson boards: [L4T Kernel Sources](https://developer.nvidia.com/embedded/linux-tegra)
  - Integrate with Yocto using [meta-tegra](https://github.com/OE4T/meta-tegra).
- **Mainline Kernel + NVIDIA Proprietary Driver:**
  - Use mainline kernel and install NVIDIA driver out-of-tree.
  - Example: Download driver from NVIDIA, build kernel modules, and add to your image.
- **Custom Kernel Recipe:**
  - Add your own kernel recipe in Yocto:
    ```bitbake
    require recipes-kernel/linux/linux-yocto.inc
    SRC_URI += "file://my-nvidia-config"
    ```
  - Add custom patches or modules for GPU acceleration.

## Summary Table

| Extension         | Benefit                        | How to Add/Replace                |
|-------------------|-------------------------------|-----------------------------------|
| Rust module       | Fast, safe backend/filtering   | Use PyO3, cargo, update recipe    |
| C/C++ module      | Native speed, hardware access  | Build .so/.dll, update recipe     |
| Tiny image        | Minimal footprint              | Use core-image-minimal, prune deps|
| Custom kernel     | Hardware support, performance  | Use BSP/meta-tegra, config frags  |
| Out-of-tree kernel| NVIDIA GPU, special hardware   | Use vendor kernel, add modules    |

---

**For more details on kernel customization, see [Yocto Kernel Development Manual](https://www.yoctoproject.org/docs/3.1/kernel-dev/kernel-dev.html).
For Rust/C++ integration, see [PyO3](https://pyo3.rs/) and [Yocto Rust Layer](https://github.com/meta-rust/meta-rust).**
