"""Minimal COM smoke test for AutoCAD 2026"""

def test_connection():
    try:
        import win32com.client
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
        version = acad.Version
        print(f"++ AutoCAD connected. Version: {version}")
        doc_count = acad.Documents.Count
        print(f"   Open documents: {doc_count}")
        if doc_count > 0:
            doc = acad.ActiveDocument
            print(f"   Active document: {doc.Name}")
        return True
    except Exception as e:
        print(f"-- AutoCAD connection failed: {e}")
        print("   Suggestion: Start AutoCAD 2026 first, then retry.")
        return False

def test_registry():
    prog_ids = ["AutoCAD.Application", "AutoCAD.Application.25", "AutoCAD.Application.25.1"]
    for pid in prog_ids:
        try:
            from win32com.client import gencache
            clsid = gencache.ProgIDToCLSID(pid)
            print(f"   {pid} -> CLSID: {clsid}")
        except Exception:
            print(f"   {pid} -> NOT REGISTERED")

if __name__ == "__main__":
    print("=== CAD Direct Control - COM Smoke Test ===")
    test_registry()
    print()
    test_connection()
