#!/usr/bin/env python3
"""
Diagnostic script to check if your environment is ready to run sync_rss_status.py
"""

import os
import sys

print("=" * 70)
print("🔍 Environment Diagnostic Check")
print("=" * 70)
print()

# Check Python version
print("1. Python Version:")
print(f"   ✓ Python {sys.version}")
print(f"   ✓ Executable: {sys.executable}")
print()

# Check if we're in the right directory
print("2. Current Directory:")
current_dir = os.getcwd()
print(f"   Current: {current_dir}")
script_path = os.path.join(current_dir, "sync_rss_status.py")
if os.path.exists(script_path):
    print(f"   ✓ sync_rss_status.py found at: {script_path}")
else:
    print(f"   ❌ sync_rss_status.py NOT found!")
    print(f"   Expected at: {script_path}")
print()

# Check for required Python packages
print("3. Required Python Packages:")
required_packages = [
    ("google.cloud.firestore", "google-cloud-firestore"),
    ("google.cloud.storage", "google-cloud-storage"),
]

all_installed = True
for module_name, package_name in required_packages:
    try:
        __import__(module_name)
        print(f"   ✓ {package_name} installed")
    except ImportError:
        print(f"   ❌ {package_name} NOT installed")
        print(f"      Install with: pip3 install {package_name}")
        all_installed = False
print()

# Check for gcloud CLI
print("4. Google Cloud SDK (gcloud):")
gcloud_paths = [
    "/usr/bin/gcloud",
    "/usr/local/bin/gcloud",
    os.path.expanduser("~/google-cloud-sdk/bin/gcloud"),
]
gcloud_found = False
for path in gcloud_paths:
    if os.path.exists(path):
        print(f"   ✓ Found at: {path}")
        gcloud_found = True
        break

# Also check PATH
import shutil
gcloud_in_path = shutil.which("gcloud")
if gcloud_in_path:
    print(f"   ✓ Found in PATH: {gcloud_in_path}")
    gcloud_found = True

if not gcloud_found:
    print("   ⚠️  gcloud not found")
    print("   This is OK if you're using a service account key file")
    print("   Or if you'll authenticate via: gcloud auth application-default login")
print()

# Check environment variables
print("5. Environment Variables:")
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "NOT SET (will use default: regal-scholar-453620-r7)")
bucket = os.getenv("GCP_AUDIO_BUCKET", "NOT SET (will use default: regal-scholar-453620-r7-podcast-storage)")
print(f"   GOOGLE_CLOUD_PROJECT: {project_id}")
print(f"   GCP_AUDIO_BUCKET: {bucket}")
print()

# Check for GCP credentials
print("6. GCP Authentication:")
credential_paths = [
    os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
    os.path.expanduser("~/.config/gcloud/legacy_credentials"),
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
]

has_creds = False
for cred_path in credential_paths:
    if cred_path and os.path.exists(cred_path):
        print(f"   ✓ Found credentials at: {cred_path}")
        has_creds = True
        break

if not has_creds:
    print("   ⚠️  No application default credentials found")
    print("   You may need to run: gcloud auth application-default login")
    print("   Or set GOOGLE_APPLICATION_CREDENTIALS to a service account key file")
print()

# Summary
print("=" * 70)
print("📊 Summary:")
print("=" * 70)

issues = []
if not os.path.exists(script_path):
    issues.append("❌ sync_rss_status.py not found in current directory")
if not all_installed:
    issues.append("❌ Required Python packages not installed")
if not has_creds:
    issues.append("⚠️  GCP credentials not found (may need authentication)")

if not issues:
    print("✅ All checks passed! You should be able to run sync_rss_status.py")
    print()
    print("Next steps:")
    print("  1. Run: python3 sync_rss_status.py --dry-run")
    print("  2. If that works, run: python3 sync_rss_status.py")
else:
    print("Issues found:")
    for issue in issues:
        print(f"  {issue}")
    print()
    print("Fix the issues above, then try again.")

print("=" * 70)
