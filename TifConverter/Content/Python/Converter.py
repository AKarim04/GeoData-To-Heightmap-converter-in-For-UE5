import os
from PIL import Image
import numpy as np
import unreal
import tkinter as tk
from tkinter import filedialog



# 1. Välj TIF-fil via Tkinter
def select_tif_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select TIF heightmap",
        filetypes=[("TIF files", "*.tif *.tiff")]
    )
    return file_path



# 2. Läs TIF → numpy-array (endast PIL)
def load_tif_as_array(path):
    img = Image.open(path)
    arr = np.array(img).astype(np.float32)
    return arr



# 3. Normalisera och spara PNG

def save_normalized_png(arr, out_path):
    # ersätt NaN om de finns
    if np.isnan(arr).any():
        arr = np.nan_to_num(arr, nan=np.nanmin(arr))

    min_h = float(np.min(arr))
    max_h = float(np.max(arr))

    # normalisera 
    if max_h - min_h == 0:
        norm = np.zeros_like(arr, dtype=np.uint16)
    else:
        norm = ((arr - min_h) / (max_h - min_h) * 65535).astype(np.uint16)

    img = Image.fromarray(norm)
    img.save(out_path)

    return min_h, max_h


# ---------------------------------------------------------
# 4. Importera PNG till Unreal
# ---------------------------------------------------------
def import_png_to_unreal(local_path, asset_name, dest_folder="/Game/ImportedHeightmaps"):

    # skapa mapp om den saknas
    if not unreal.EditorAssetLibrary.does_directory_exist(dest_folder):
        unreal.EditorAssetLibrary.make_directory(dest_folder)

    asset_path = f"{dest_folder}/{asset_name}"

    # om asset redan finns
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        return asset_path, True

    task = unreal.AssetImportTask()
    task.set_editor_property("automated", True)
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("destination_path", dest_folder)
    task.set_editor_property("filename", local_path)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    imported = task.get_editor_property("imported_object_paths")
    if imported:
        return imported[0], False

    return None, False

# ---------------------------------------------------------
# 5. Huvudfunktion som Editor Utility Widget kan anropa
# ---------------------------------------------------------
LastResult = None

def convert_and_import_heightmap():
    global LastResult

    result = {
        "height_data": None,
        "min_height": None,
        "max_height": None,
        "imported_asset_path": None,
        "Height_Map_Asset": None,
        "already_loaded": False,
        "conversion_error": False,
        "import_error": False,
        "message": ""
    }

    tif_path = select_tif_file()
    if not tif_path:
        result["conversion_error"] = True
        result["message"] = "No file selected."
        LastResult = result
        return result

    try:
        arr = load_tif_as_array(tif_path)
        result["height_data"] = arr
        print("height array loaded:", arr)

        # spara PNG i projektets Saved-mapp
        project_dir = unreal.SystemLibrary.get_project_directory()
        out_dir = os.path.join(project_dir, "Content", "ImportedHeightmaps")
        os.makedirs(out_dir, exist_ok=True)

        out_name = os.path.splitext(os.path.basename(tif_path))[0]
        out_png = os.path.join(out_dir, out_name + ".png")

        min_h, max_h = save_normalized_png(arr, out_png)
        result["min_height"] = min_h
        result["max_height"] = max_h

    except Exception as e:
        result["conversion_error"] = True
        result["message"] = f"Conversion error: {e}"
        LastResult = result
        return result

    # Importera till Unreal
    try:
        asset_path, already = import_png_to_unreal(out_png, out_name)
        result["imported_asset_path"] = asset_path
        result["already_loaded"] = already
        result["message"] = "Import successful." if asset_path else "Import failed."
        if not asset_path:
            result["import_error"] = True

    except Exception as e:
        result["import_error"] = True
        result["message"] = f"Import error: {e}"

    LastResult = result
    return  result

