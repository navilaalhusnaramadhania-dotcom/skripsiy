import os
import shutil
import sys
from pathlib import Path
from PIL import Image

def optimize_pngs(mobile_dir: Path, backup_dir: Path):
    if not mobile_dir.exists():
        print(f"Error: Direktori {mobile_dir} tidak ditemukan!", file=sys.stderr)
        sys.exit(1)

    backup_dir.mkdir(parents=True, exist_ok=True)
    png_files = sorted(list(mobile_dir.glob("*.png")))
    total_files = len(png_files)
    
    print(f"Ditemukan {total_files} file PNG di {mobile_dir}")
    print(f"Menyiapkan folder backup di {backup_dir}...\n")

    results = []
    total_orig_size = 0
    total_new_size = 0
    skipped_count = 0
    optimized_count = 0

    for idx, png_path in enumerate(png_files, 1):
        filename = png_path.name
        backup_path = backup_dir / filename
        temp_path = mobile_dir / f"{filename}.tmp"

        orig_size = png_path.stat().st_size
        total_orig_size += orig_size

        # 1. Backup file asli jika belum ada di folder backup
        if not backup_path.exists():
            shutil.copy2(png_path, backup_path)

        # 2. Proses optimasi lossless
        try:
            with Image.open(png_path) as im:
                # Simpan mode, info, dan data transparansi
                im.save(temp_path, format="PNG", optimize=True, compress_level=9)

            # Verifikasi integritas file hasil kompresi
            with Image.open(temp_path) as test_im:
                test_im.verify()

            new_size = temp_path.stat().st_size

            # Safety guardrail: Hanya timpa jika ukuran baru lebih kecil
            if new_size < orig_size:
                shutil.move(temp_path, png_path)
                saved_bytes = orig_size - new_size
                saved_pct = (saved_bytes / orig_size) * 100
                total_new_size += new_size
                optimized_count += 1
                status = "OPTIMIZED"
            else:
                if temp_path.exists():
                    temp_path.unlink()
                total_new_size += orig_size
                saved_bytes = 0
                saved_pct = 0.0
                skipped_count += 1
                status = "KEPT_ORIGINAL"

            results.append({
                "filename": filename,
                "orig_size": orig_size,
                "new_size": new_size if status == "OPTIMIZED" else orig_size,
                "saved_bytes": saved_bytes,
                "saved_pct": saved_pct,
                "status": status
            })

            print(f"[{idx:02d}/{total_files:02d}] {filename}: {orig_size:,} -> {results[-1]['new_size']:,} bytes ({saved_pct:.1f}% hemat) [{status}]")

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            total_new_size += orig_size
            results.append({
                "filename": filename,
                "orig_size": orig_size,
                "new_size": orig_size,
                "saved_bytes": 0,
                "saved_pct": 0.0,
                "status": f"ERROR: {e}"
            })
            print(f"[{idx:02d}/{total_files:02d}] {filename}: GAGAL ({e})", file=sys.stderr)

    total_saved = total_orig_size - total_new_size
    total_pct = (total_saved / total_orig_size) * 100 if total_orig_size > 0 else 0

    print("\n" + "="*70)
    print("                     RINGKASAN OPTIMASI PNG")
    print("="*70)
    print(f"Total File Diproses : {total_files} file")
    print(f"File Berhasil Dihemat: {optimized_count} file")
    print(f"File Dipertahankan   : {skipped_count} file (sudah optimal)")
    print(f"Ukuran Semula       : {total_orig_size / (1024*1024):.2f} MB ({total_orig_size:,} bytes)")
    print(f"Ukuran Setelahnya   : {total_new_size / (1024*1024):.2f} MB ({total_new_size:,} bytes)")
    print(f"Total Penghematan   : {total_saved / (1024*1024):.2f} MB ({total_saved:,} bytes) / {total_pct:.2f}%")
    print("="*70)

    # Tampilkan top 10 penghematan terbesar
    top_savings = sorted(results, key=lambda x: x["saved_bytes"], reverse=True)[:10]
    print("\nTop 10 File dengan Penghematan Ukuran Terbesar:")
    print(f"{'Filename':<35} {'Semula (KB)':<13} {'Hasil (KB)':<13} {'Hemat (KB)':<13} {'% Hemat'}")
    print("-" * 80)
    for item in top_savings:
        if item["saved_bytes"] > 0:
            print(f"{item['filename']:<35} {item['orig_size']/1024:<13.1f} {item['new_size']/1024:<13.1f} {item['saved_bytes']/1024:<13.1f} {item['saved_pct']:.1f}%")

if __name__ == "__main__":
    workspace = Path(__file__).resolve().parent.parent
    mobile_dir = workspace / "mobile"
    backup_dir = workspace / "backup_png_original"
    optimize_pngs(mobile_dir, backup_dir)
