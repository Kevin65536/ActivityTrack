#!/usr/bin/env python3
"""
Build script for ActivityTrack
Automates the PyInstaller build process
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def print_step(message):
    """Print a formatted step message"""
    print(f"\n{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}\n")

def check_requirements():
    """Check if all build requirements are met"""
    print_step("Checking build requirements")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✓ PyInstaller found: {PyInstaller.__version__}")
    except ImportError:
        print("✗ PyInstaller not found")
        print("  Install with: pip install pyinstaller")
        return False
    
    # Check required packages
    required = {
        'PySide6': 'PySide6',
        'pywin32': 'win32api',  # pywin32 imports as win32api
        'psutil': 'psutil',
        'matplotlib': 'matplotlib',
        'numpy': 'numpy'
    }
    missing = []
    
    for display_name, import_name in required.items():
        try:
            __import__(import_name)
            print(f"✓ {display_name} found")
        except ImportError:
            print(f"✗ {display_name} not found")
            missing.append(display_name)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    # Check spec file
    if not Path('ActivityTrack.spec').exists():
        print("✗ ActivityTrack.spec not found")
        return False
    print("✓ ActivityTrack.spec found")
    
    return True

def clean_build():
    """Clean previous build artifacts"""
    print_step("Cleaning previous builds")
    
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            print(f"Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    print("✓ Clean complete")

def run_pyinstaller():
    """Run PyInstaller build"""
    print_step("Running PyInstaller")
    
    cmd = ['pyinstaller', 'ActivityTrack.spec', '--clean']
    
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print("\n✗ PyInstaller build failed")
        return False
    
    print("\n✓ PyInstaller build successful")
    return True

def verify_build():
    """Verify the build output"""
    print_step("Verifying build output")
    
    exe_path = Path('dist/ActivityTrack/ActivityTrack.exe')
    
    if not exe_path.exists():
        print(f"✗ Executable not found: {exe_path}")
        return False
    
    print(f"✓ Executable found: {exe_path}")
    
    # Check file size
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"  Size: {size_mb:.1f} MB")
    
    # Check for critical files
    dist_dir = Path('dist/ActivityTrack')
    critical_files = ['config.json']
    
    for file_name in critical_files:
        file_path = dist_dir / file_name
        if file_path.exists():
            print(f"✓ {file_name} included")
        else:
            print(f"✗ {file_name} missing")
    
    return True

def create_portable_zip():
    """Create portable ZIP distribution"""
    print_step("Creating portable ZIP")
    
    import zipfile
    
    dist_dir = Path('dist/ActivityTrack')
    zip_path = Path('dist/ActivityTrack-Portable.zip')
    
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in dist_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(dist_dir.parent)
                zipf.write(file_path, arcname)
                print(f"  Added: {arcname}")
    
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n✓ ZIP created: {zip_path}")
    print(f"  Size: {size_mb:.1f} MB")
    
    return True

def print_summary():
    """Print build summary"""
    print_step("Build Summary")
    
    print("Build artifacts:")
    print(f"  Executable: dist/ActivityTrack/ActivityTrack.exe")
    print(f"  Portable:   dist/ActivityTrack-Portable.zip")
    
    print("\nNext steps:")
    print("  1. Test the executable in dist/ActivityTrack/")
    print("  2. Test on a clean Windows VM (no Python)")
    print("  3. Create installer with Inno Setup (optional)")
    print("  4. Create GitHub Release and upload artifacts")

def main():
    """Main build process"""
    print_step("ActivityTrack Build Script")
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Build requirements not met")
        return 1
    
    # Clean previous builds
    clean_build()
    
    # Run PyInstaller
    if not run_pyinstaller():
        print("\n❌ Build failed")
        return 1
    
    # Verify build
    if not verify_build():
        print("\n❌ Build verification failed")
        return 1
    
    # Create portable ZIP
    if not create_portable_zip():
        print("\n⚠️  Failed to create ZIP (non-critical)")
    
    # Print summary
    print_summary()
    
    print("\n✅ Build complete!")
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
