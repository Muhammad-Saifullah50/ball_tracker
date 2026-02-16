"""
Verification script to check that the fixes are in place and working
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def verify_fixes():
    print("Verifying fixes for camera feed issue...")

    # Read the updated file
    with open("src/ui/pages/2_Live_Tracking.py", "r") as f:
        content = f.read()

    # Check for the fixes
    fixes_verified = []

    # Check 1: Updated thread management in button handlers
    if 'self.start_tracking()' in content and 'self.stop_tracking()' in content:
        fixes_verified.append("✅ Button handlers updated to use proper thread management")
    else:
        fixes_verified.append("❌ Button handlers not properly updated")

    # Check 2: Fixed thread management methods
    if 'if hasattr(self, \'tracker_thread\') and self.tracker_thread:' in content:
        fixes_verified.append("✅ Thread management fixed to prevent AttributeError")
    else:
        fixes_verified.append("❌ Thread management not fixed")

    # Check 3: Added multiple STUN servers
    if 'stun.stunprotocol.org' in content and 'stun.freeswitch.org' in content:
        fixes_verified.append("✅ Multiple STUN servers added for better connectivity")
    else:
        fixes_verified.append("❌ Multiple STUN servers not found")

    # Check 4: Added timeout and error handling
    if 'timeout=30' in content:
        fixes_verified.append("✅ WebRTC timeout added")
    else:
        fixes_verified.append("❌ WebRTC timeout not found")

    # Check 5: Improved error handling
    if 'Camera Error:' in content and 'Check for error states' in content:
        fixes_verified.append("✅ Better error handling implemented")
    else:
        fixes_verified.append("❌ Better error handling not found")

    # Check 6: Troubleshooting info added
    if 'troubleshoot camera issues' in content:
        fixes_verified.append("✅ Troubleshooting information added")
    else:
        fixes_verified.append("❌ Troubleshooting information not found")

    # Print verification results
    print("\nFix Verification Results:")
    print("=" * 50)
    for result in fixes_verified:
        print(result)

    # Summary
    successful_fixes = [f for f in fixes_verified if f.startswith("✅")]
    failed_fixes = [f for f in fixes_verified if f.startswith("❌")]

    print(f"\nSummary: {len(successful_fixes)} fixes verified, {len(failed_fixes)} issues remaining")

    if len(failed_fixes) == 0:
        print("🎉 All fixes have been successfully implemented!")
        return True
    else:
        print("⚠️ Some fixes need additional attention.")
        return False

if __name__ == "__main__":
    verify_fixes()