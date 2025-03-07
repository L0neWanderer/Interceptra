import subprocess
import os
import os.path
import re
from xml.etree import ElementTree
import sys
import shutil


class Interceptra:
    # Default surgical instruments (configuration constants)
    DEFAULT_KEYSTORE = "debug.keystore"
    DEFAULT_KEYPASS = "android"
    DEFAULT_STOREPASS = "android" 
    DEFAULT_SIGALG = "SHA1withRSA"
    DEFAULT_DIGESTALG = "SHA1"
    DEFAULT_ALIAS = "androiddebugkey"
    DEFAULT_APKTOOL_JAR = "apktool_2.11.0.jar"

    def __init__(self, apk, verbose=False, tool_paths=None, keep_files=False):
        # Set verbosity level
        self.verbose = verbose
        
        # Configure tool paths (use defaults if not specified)
        self.tool_paths = {
            'apktool': self.DEFAULT_APKTOOL_JAR,
            'keystore': self.DEFAULT_KEYSTORE,
            'java': 'java',
            'zipalign': 'zipalign',
            'jarsigner': 'jarsigner',
            'apksigner': 'apksigner'
        }
        
        # Update with any user-provided tool paths
        if tool_paths:
            self.tool_paths.update(tool_paths)
            
        # Get the actual tools we'll use
        self.KEYSTORE = self.tool_paths['keystore']
        self.KEYPASS = self.DEFAULT_KEYPASS
        self.STOREPASS = self.DEFAULT_STOREPASS
        self.SIGALG = self.DEFAULT_SIGALG
        self.DIGESTALG = self.DEFAULT_DIGESTALG
        self.ALIAS = self.DEFAULT_ALIAS
        self.APKTOOL_JAR = self.tool_paths['apktool']
        
        # Keep intermediate files?
        self.keep_files = keep_files
        
        # Normalize and convert to absolute paths
        self.apk = os.path.abspath(os.path.expanduser(apk))
        self.file_name = os.path.splitext(os.path.basename(self.apk))[0]
        
        # Output file paths
        self.output_dir = os.path.dirname(self.apk)
        self.patched_apk = os.path.join(self.output_dir, f"{self.file_name}_patched.apk")
        self.zipaligned_apk = os.path.join(self.output_dir, f"{self.file_name}_patched_zipaligned.apk")
        
        # Extraction directory
        self.extraction_dir = os.path.join(os.path.dirname(self.apk), self.file_name)
        
        # Track SDK version
        self.compile_sdk = None
        
        # Verify dependencies
        self._check_dependencies()

    def _check_dependencies(self):
        """Check that required tools are available."""
        missing_tools = []
        
        # Check for apktool jar
        if not os.path.exists(self.APKTOOL_JAR):
            print(f"[!] Warning: {self.APKTOOL_JAR} not found in current directory")
            
        # Check for keystore
        if not os.path.exists(self.KEYSTORE):
            print(f"[!] Warning: {self.KEYSTORE} not found in current directory")
        
        # Check other tools are in PATH
        for tool, path in self.tool_paths.items():
            if tool in ['apktool', 'keystore']:
                continue  # We already checked these above
                
            try:
                # If it's a full path, check if it exists
                if os.path.isabs(path):
                    if not os.path.exists(path):
                        missing_tools.append(f"{tool} at {path}")
                # Otherwise check if it's in PATH
                else:
                    subprocess.run(["which", path], check=True, capture_output=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"[!] Warning: The following tools were not found: {', '.join(missing_tools)}")
            print("    You can specify custom tool paths using the --tools argument")
            
        if self.verbose:
            print("[*] Tool paths:")
            for tool, path in self.tool_paths.items():
                print(f"    {tool}: {path}")

    def _run_command(self, command, description, check=True):
        """Run a command with proper error handling and progress indication."""
        print(f"[+] {description}")
        
        # Only show the full command in verbose mode
        if self.verbose:
            print(f"    Command: {' '.join(command)}")
        
        # Print a progress indicator
        print("    ", end="", flush=True)
        
        try:
            # For long-running processes, show a progress indicator
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Track output and progress
            stdout_lines = []
            stderr_lines = []
            progress_chars = ["-", "\\", "|", "/"]
            i = 0
            
            # Process output while command is running
            while process.poll() is None:
                # Check for output but don't block
                stdout = process.stdout.readline()
                stderr = process.stderr.readline()
                
                if stdout:
                    stdout_lines.append(stdout)
                    if self.verbose:
                        print(f"    {stdout.strip()}")
                
                if stderr:
                    stderr_lines.append(stderr)
                    if self.verbose:
                        print(f"    [stderr] {stderr.strip()}")
                
                # Update progress indicator
                print(f"\b{progress_chars[i]}", end="", flush=True)
                i = (i + 1) % len(progress_chars)
                
                # Small delay to avoid CPU spinning
                import time
                time.sleep(0.1)
            
            # Get remaining output
            stdout, stderr = process.communicate()
            
            if stdout:
                stdout_lines.append(stdout)
                if self.verbose:
                    for line in stdout.split('\n'):
                        if line.strip():
                            print(f"    {line.strip()}")
            
            if stderr:
                stderr_lines.append(stderr)
                if self.verbose:
                    for line in stderr.split('\n'):
                        if line.strip():
                            print(f"    [stderr] {line.strip()}")
            
            # Clear progress indicator and print result
            print("\bDone")
            
            # Check return code
            if check and process.returncode != 0:
                stdout_text = ''.join(stdout_lines)
                stderr_text = ''.join(stderr_lines)
                error_msg = f"Command failed with return code {process.returncode}"
                
                print(f"[!] {error_msg}")
                if stderr_text:
                    print(f"    Error output: {stderr_text.strip()}")
                
                class CommandError(Exception):
                    def __init__(self, returncode, stdout, stderr, msg):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                        self.msg = msg
                        super().__init__(msg)
                
                raise CommandError(
                    process.returncode,
                    stdout_text,
                    stderr_text,
                    error_msg
                )
            
            # Create a result object similar to subprocess.run
            class CommandResult:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            return CommandResult(
                process.returncode,
                ''.join(stdout_lines),
                ''.join(stderr_lines)
            )
            
        except Exception as e:
            print("\bFailed")
            print(f"[!] Error executing command: {str(e)}")
            if check:
                raise
            return e

    def cut(self):
        """Main surgical procedure with cleanup option."""
        if not os.path.isfile(self.apk):
            print(f"[!] Error: APK file not found: {self.apk}")
            return False
        
        try:
            print(f"[+] Starting Interceptra on: {os.path.basename(self.apk)}")
            print(f"[+] Original APK size: {os.path.getsize(self.apk) / (1024*1024):.2f} MB")
            
            # Step 1: Open the APK
            self._decompile_apk()
            
            # Step 2: Implant network security configuration
            self._add_network_file()
            self._add_network_attribute_to_manifest()
            
            # Step 3: Check compile SDK version
            self._check_compile_sdk_version()
            
            # Step 4: Close the incision - repackage, sign, and align
            self._repackage_apk()
            
            if self.compile_sdk >= 30:
                self._zipalign_apk()
                self._apksign_apk()
                final_apk = self.zipaligned_apk
            else:
                self._jarsign_apk()
                self._zipalign_apk()
                final_apk = self.zipaligned_apk
            
            # Verify the final APK exists
            if os.path.exists(final_apk):
                # Clean up intermediate files if requested
                if not self.keep_files:
                    self._cleanup_files()
                
                final_size = os.path.getsize(final_apk) / (1024*1024)
                print(f"[+] Interceptra completed successfully: {final_apk}")
                print(f"[+] Modified APK size: {final_size:.2f} MB")
                return True
            else:
                print(f"[!] Error: Failed to create modified APK: {final_apk}")
                return False
                
        except Exception as e:
            print(f"[!] Error during APK modification: {str(e)}")
            return False
    
    def _cleanup_files(self):
        """Clean up intermediate files."""
        print("[+] Cleaning up temporary files...")
        
        # Remove extraction directory
        if os.path.exists(self.extraction_dir):
            print(f"    Removing extraction directory: {self.extraction_dir}")
            try:
                import shutil
                shutil.rmtree(self.extraction_dir)
            except Exception as e:
                print(f"    Warning: Could not remove directory: {str(e)}")
        
        # Remove intermediate APK if different from final
        if os.path.exists(self.patched_apk) and self.patched_apk != self.zipaligned_apk:
            print(f"    Removing intermediate APK: {self.patched_apk}")
            try:
                os.remove(self.patched_apk)
            except Exception as e:
                print(f"    Warning: Could not remove file: {str(e)}")

    def _decompile_apk(self):
        """Decompile the APK using apktool."""
        # Remove existing extraction directory if it exists
        if os.path.exists(self.extraction_dir):
            if self.verbose:
                print(f"[*] Removing existing directory: {self.extraction_dir}")
            shutil.rmtree(self.extraction_dir)
            
        # Calculate file size for progress information
        file_size_mb = os.path.getsize(self.apk) / (1024*1024)
        
        command = [
            self.tool_paths["java"], "-jar", self.APKTOOL_JAR,
            "-f", "d", self.apk,
            "-o", self.extraction_dir
        ]
        
        self._run_command(command, f"STEP 1/5: Decompiling APK ({file_size_mb:.2f} MB)")

    def _add_network_file(self):
        """Add network security configuration file."""
        path = os.path.join(self.extraction_dir, "res/xml")
        os.makedirs(path, exist_ok=True)
        
        # Security configuration that enables proxy interception
        network_file = """<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config>
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
    <debug-overrides>
        <trust-anchors>
            <certificates src="user" />
        </trust-anchors>
    </debug-overrides>
</network-security-config>"""
        
        file_path = os.path.join(path, "network_security_config.xml")
        print(f"[+] STEP 2/5: Creating network security config at {file_path}")
        
        with open(file_path, "w") as xml_file:
            xml_file.write(network_file)

    def _add_network_attribute_to_manifest(self):
        """Add network security config attribute to AndroidManifest.xml."""
        xml_path = os.path.join(self.extraction_dir, "AndroidManifest.xml")
        
        if not os.path.isfile(xml_path):
            print(f"[!] Error: AndroidManifest.xml not found at {xml_path}")
            raise FileNotFoundError(f"AndroidManifest.xml not found at {xml_path}")
            
        try:
            # Parse the manifest
            ElementTree.register_namespace("android", "http://schemas.android.com/apk/res/android")
            tree = ElementTree.parse(xml_path)
            root = tree.getroot()
            
            # Find and modify the application element
            application = root.find("application")
            if application is None:
                print("[!] Error: application element not found in AndroidManifest.xml")
                raise ValueError("application element not found in AndroidManifest.xml")
                
            # Add network security config attribute
            application.set(
                "{http://schemas.android.com/apk/res/android}networkSecurityConfig", 
                "@xml/network_security_config"
            )
            
            # Write back the modified manifest
            with open(xml_path, "wb") as xml_file:
                xml_file.write('<?xml version="1.0" encoding="utf-8" standalone="no"?>'.encode())
                xml_file.write(ElementTree.tostring(root))
                
            print(f"[+] STEP 2/5: Updated AndroidManifest.xml with network security config attribute")
            
        except Exception as e:
            print(f"[!] Error modifying AndroidManifest.xml: {str(e)}")
            raise

    def _check_compile_sdk_version(self):
        """Check and extract the compile SDK version from AndroidManifest.xml."""
        xml_path = os.path.join(self.extraction_dir, "AndroidManifest.xml")
        
        try:
            ElementTree.register_namespace("android", "http://schemas.android.com/apk/res/android")
            tree = ElementTree.parse(xml_path)
            root = tree.getroot()
            
            # Get compileSdkVersion attribute
            compile_sdk_attr = "{http://schemas.android.com/apk/res/android}compileSdkVersion"
            
            if compile_sdk_attr in root.attrib:
                self.compile_sdk = int(root.attrib[compile_sdk_attr])
                print(f"[+] STEP 3/5: Detected Android SDK version: {self.compile_sdk}")
            else:
                # Default to SDK 30 if not found
                self.compile_sdk = 30
                print(f"[!] STEP 3/5: compileSdkVersion not found in manifest, defaulting to {self.compile_sdk}")
                
        except Exception as e:
            print(f"[!] Error checking SDK version: {str(e)}")
            # Default to SDK 30 if an error occurs
            self.compile_sdk = 30
            print(f"[!] Defaulting to SDK version {self.compile_sdk}")

    def _repackage_apk(self):
        """Repackage the modified files into a new APK."""
        command = [
            self.tool_paths["java"], "-jar", self.APKTOOL_JAR,
            "-f", "b", self.extraction_dir,
            "-o", self.patched_apk,
            "--use-aapt2"
        ]
        
        self._run_command(command, f"STEP 4/5: Repackaging APK to {os.path.basename(self.patched_apk)}")
        
        # Verify the patched APK was created
        if not os.path.exists(self.patched_apk):
            raise FileNotFoundError(f"Failed to create patched APK: {self.patched_apk}")

    def _jarsign_apk(self):
        """Sign the APK using jarsigner (for SDK < 30)."""
        apk_size_mb = os.path.getsize(self.patched_apk) / (1024*1024)
        
        command = [
            self.tool_paths["jarsigner"],
            "-verbose",
            "-keystore", self.KEYSTORE,
            "-keypass", self.KEYPASS,
            "-storepass", self.STOREPASS,
            "-sigalg", self.SIGALG,
            "-digestalg", self.DIGESTALG,
            self.patched_apk,
            self.ALIAS
        ]
        
        self._run_command(command, f"STEP 5/5: Signing APK with jarsigner ({apk_size_mb:.2f} MB)")

    def _apksign_apk(self):
        """Sign the APK using apksigner (for SDK >= 30)."""
        apk_size_mb = os.path.getsize(self.zipaligned_apk) / (1024*1024)
        
        command = [
            self.tool_paths["apksigner"], "sign",
            "--ks", self.KEYSTORE,
            "--ks-key-alias", self.ALIAS,
            f"--ks-pass", f"pass:{self.STOREPASS}",
            self.zipaligned_apk
        ]
        
        self._run_command(command, f"STEP 5/5: Signing APK with apksigner ({apk_size_mb:.2f} MB)")

    def _zipalign_apk(self):
        """Align the APK using zipalign for better performance."""
        # Make sure output directory exists
        os.makedirs(os.path.dirname(self.zipaligned_apk), exist_ok=True)
        
        apk_size_mb = os.path.getsize(self.patched_apk) / (1024*1024)
        
        command = [
            self.tool_paths["zipalign"],
            "-p", "-f", "4",
            self.patched_apk,
            self.zipaligned_apk
        ]
        
        self._run_command(command, f"STEP 5/5: Aligning APK for performance ({apk_size_mb:.2f} MB)")
        
        # Verify the zipaligned APK was created
        if not os.path.exists(self.zipaligned_apk):
            raise FileNotFoundError(f"Failed to create aligned APK: {self.zipaligned_apk}")