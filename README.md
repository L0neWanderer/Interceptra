# Interceptra

Interceptra is a tool for modifying Android APKs to enable network proxy interception through tools like Burp Suite. It adds the necessary network security configuration to allow user certificates, then repackages and signs the application.

## Features

- Automatically adds network security configuration to allow proxy inspection
- Handles all decompiling, repackaging, alignment, and signing
- Supports all Android SDK versions with proper signing procedures
- Includes progress indicators and detailed logging
- Allows custom tool path configurations

## Dependencies

- **Java/JDK** (for jarsigner & apktool): `brew install --cask temurin` or `brew install --cask oracle-jdk`
- **Android SDK Build Tools** (for apksigner & zipalign): Install via Android Studio or SDK Manager
- **apktool_2.11.0.jar**: Included with Interceptra (or download from [apktool.org](https://apktool.org/))
- **Debug Keystore**: Generate your own using the instructions below

### Creating a Debug Keystore

Generate a new debug keystore with this command:

```bash
keytool -genkey -v -keystore debug.keystore -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
```

Place the generated `debug.keystore` in the same directory as the `interceptra.py` script.

### Build Tools Path Setup

Make sure Android SDK build-tools folder is in your PATH (add to .bashrc, .zshrc, etc.):

```bash
# For macOS - Add to your shell profile
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/34.0.0
```

Replace `34.0.0` with your installed build-tools version.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/interceptra.git
   cd interceptra
   ```

2. Ensure the script is executable:
   ```bash
   chmod +x interceptra.py
   ```

## Usage

### Basic Usage:

```bash
python3 interceptra.py -a path/to/app.apk
```

### Advanced Options:

```bash
python3 interceptra.py -a path/to/app.apk --verbose --keep-files
```

### All Available Options:

```
usage: interceptra [-h] --apk APK [--verbose] [--keep-files] [--tools TOOLS]

Interceptra v1.1.0 - Patch Android APKs to enable proxy interception

optional arguments:
  -h, --help            show this help message and exit
  --apk APK, -a APK     Path to the APK file to patch
  --verbose, -v         Enable verbose output
  --keep-files, -k      Keep intermediate files after patching
  --tools TOOLS         Specify custom paths to tools in JSON format

Example: interceptra.py -a path/to/app.apk --verbose
```

### Custom Tool Paths

You can specify custom paths to the required tools using JSON:

```bash
# Using a JSON string
python3 interceptra.py -a app.apk --tools '{"apktool": "/path/to/apktool.jar", "zipalign": "/custom/path/zipalign"}'

# Or using a JSON file
python3 interceptra.py -a app.apk --tools tool_paths.json
```

Example `tool_paths.json`:
```json
{
  "apktool": "/path/to/apktool.jar",
  "keystore": "/path/to/debug.keystore",
  "java": "/usr/bin/java",
  "zipalign": "/path/to/zipalign",
  "jarsigner": "/path/to/jarsigner",
  "apksigner": "/path/to/apksigner"
}
```

## Output Files

After successful execution, you'll find:
- `appname_patched_zipaligned.apk` - The modified APK ready for proxy testing

## Example Output

```
[+] Starting Interceptra on: example.apk
[+] Original APK size: 25.4 MB
[+] STEP 1/5: Decompiling APK (25.4 MB)
    -Done
[+] STEP 2/5: Creating network security config at example/res/xml/network_security_config.xml
[+] STEP 2/5: Updated AndroidManifest.xml with network security config attribute
[+] STEP 3/5: Detected Android SDK version: 30
[+] STEP 4/5: Repackaging APK to example_patched.apk
    -Done
[+] STEP 5/5: Aligning APK for performance (26.0 MB)
    -Done
[+] STEP 5/5: Signing APK with apksigner (26.0 MB)
    -Done
[+] Interceptra completed successfully: example_patched_zipaligned.apk
[+] Modified APK size: 26.1 MB
[+] Interceptra completed! The APK has been patched to allow proxy interception.
```

## Notes

- Processing time varies based on APK size (can take several minutes for large apps)
- The script needs appropriate permissions to read/write files in the working directory

## Troubleshooting

If the script fails to produce the expected output file, you can attempt to manually perform the steps:

1. **Manually repackage the modified APK folder**:
   ```bash
   java -jar apktool_2.11.0.jar b path/to/extracted/apk/folder --use-aapt2 -o manual_patched.apk
   ```

2. **Align the APK**:
   ```bash
   zipalign -p -f 4 manual_patched.apk manual_patched_zipaligned.apk
   ```

3. **Sign the APK**:
   For newer APKs (SDK 30+):
   ```bash
   apksigner sign --ks debug.keystore --ks-key-alias androiddebugkey --ks-pass pass:android manual_patched_zipaligned.apk
   ```
   
   For older APKs:
   ```bash
   jarsigner -verbose -keystore debug.keystore -keypass android -storepass android -sigalg SHA1withRSA -digestalg SHA1 manual_patched.apk androiddebugkey
   zipalign -p -f 4 manual_patched.apk manual_patched_zipaligned.apk
   ```

### Common Issues

1. **Decompilation fails**:
   - Check that APK is not corrupted
   - Try using the latest version of apktool
   - Check console output for specific errors

2. **Repackaging fails**:
   - Ensure you have sufficient disk space
   - Look for error messages in the verbose output
   - Make sure all dependencies are properly installed

3. **Signing fails**:
   - Verify keystore is accessible and password is correct
   - Ensure apksigner/jarsigner is in PATH

## Credits

- Uses [apktool](https://apktool.org/) for APK decompilation and repackaging