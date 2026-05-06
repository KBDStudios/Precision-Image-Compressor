<img width="1654" height="844" alt="Demonstration Precision Image Compressor" src="https://github.com/user-attachments/assets/7fc192b0-73ba-4947-9d4c-4df6e7a38a47" />

# Precision Image Compressor (Animated Edition)

A specialized, high-performance GUI utility developed by **KBDStudios** for compressing images to precise target file sizes (Bytes/KB/MB) purely in memory. 

Unlike standard compressors that ask for a generic "quality percentage," this tool allows you to input an exact target file size. It utilizes a binary search algorithm to perfectly calculate JPEG quality, and a dynamic resolution downscaler for formats like PNG, BMP, and animated files to ensure you hit your exact size requirements. 

## ✨ Features

* **Target-Size Compression:** Input your desired file size in Bytes, KB, MB, or GB, and the tool mathematically finds the best visual quality to match it.
* **Side-by-Side Comparison:** View your original and compressed images side-by-side in real-time.
* **Advanced Magnifier:** Hover over the preview panels with a dynamic magnifier. Adjust the magnification power via a slider to inspect pixel-perfect compression artifacts.
* **Full Animation Support:** Fully supports playback and frame-by-frame compression targeting for animated formats like GIF, WEBP, AVIF, and TIFF.
* **Format Conversion:** Convert between JPEG, PNG, GIF, BMP, TIFF, TGA, WEBP, AVIF, and HEIC/HEIF on the fly.
* **Exact Byte Padding:** Optionally pad the final output with null bytes (`\x00`) to match a specific size byte-for-byte.
* **In-Memory Processing:** No temporary cache folders are created. All rendering is done in your system's RAM for rapid real-time previews.

## 🚀 Installation & Usage

### Option 1: Standalone Executable (Easiest)
For users who just want to run the program without installing Python:
1. Navigate to the **Releases** tab on the right side of this page.
2. Download the latest `Precision_Image_Compressor.exe`.
3. Double-click to run! 

🛡️ **Note on Windows "Unknown Publisher" Warning:**
Because this is an independently developed freeware tool, the executable is not signed with a commercial Microsoft certificate. When you first run the program, Windows SmartScreen might show a blue "Windows protected your PC" popup. Don't worry! To bypass this, simply click **More info**, and then click **Run anyway**.

### Option 2: Running from Source
For developers or users running the raw Python script:
1. Ensure you have **Python 3.x** installed on your system.
2. Clone or download this repository.
3. Install the required image processing library by opening your command prompt and typing:

       pip install pillow

   **(Optional)** If you want support for Apple's HEIC/HEIF image formats, install the supplementary plugin:

       pip install pillow-heif

4. Run the `PrecisionImageCompressor.pyw` script.

## 📄 License
This software is provided under a custom Proprietary Freeware License. It is strictly for personal, non-commercial use. Modification or creation of derivative works is prohibited. Please see the LICENSE.txt file for complete details.

---
**Author:** KabirDigitalStudios (KBDStudios)
