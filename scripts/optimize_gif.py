import os
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image

def optimize_gifs(mobile_dir: Path, backup_dir: Path):
    if not mobile_dir.exists():
        print(f"Error: Direktori {mobile_dir} tidak ditemukan!", file=sys.stderr)
        sys.exit(1)

    backup_dir.mkdir(parents=True, exist_ok=True)
    gif_files = sorted(list(mobile_dir.glob("*.gif")), key=lambda p: p.stat().st_size, reverse=True)
    total_files = len(gif_files)

    print(f"Ditemukan {total_files} file GIF di {mobile_dir}")
    print(f"Menyiapkan folder backup di {backup_dir}...\n")

    results = []
    total_orig_size = 0
    total_new_size = 0
    optimized_count = 0
    skipped_count = 0

    for idx, gif_path in enumerate(gif_files, 1):
        filename = gif_path.name
        backup_path = backup_dir / filename
        temp_path = mobile_dir / f"{filename}.tmp.gif"

        orig_size = gif_path.stat().st_size
        total_orig_size += orig_size

        # 1. Salin ke folder cadangan jika belum ada
        if not backup_path.exists():
            shutil.copy2(gif_path, backup_path)

        # 2. Jalankan Gifsicle dengan parameter Visually Lossless
        cmd = [
            "npx", "gifsicle",
            "-O3",
            "--lossy=45",
            "--no-comments",
            "--no-names",
            str(gif_path),
            "-o", str(temp_path)
        ]

        try:
            # Gunakan shell=True untuk Windows npx
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
            
            if proc.returncode != 0 or not temp_path.exists():
                raise RuntimeError(f"Gifsicle error: {proc.stderr}")

            # 3. Verifikasi file hasil kompresi dengan Pillow
            with Image.open(temp_path) as im:
                frames_count = getattr(im, "n_frames", 1)
                if frames_count < 1:
                    raise ValueError("File terkompresi tidak memiliki frame yang valid")

            new_size = temp_path.stat().st_size

            # Safety guardrail: Hanya timpa jika ukuran baru lebih kecil
            if new_size < orig_size:
                shutil.move(temp_path, gif_path)
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

            orig_mb = orig_size / (1024 * 1024)
            new_mb = results[-1]["new_size"] / (1024 * 1024)
            print(f"[{idx:02d}/{total_files:02d}] {filename}: {orig_mb:.2f} MB -> {new_mb:.2f} MB ({saved_pct:.1f}% hemat) [{status}]")

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
    print("                     RINGKASAN OPTIMASI GIF")
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
    print(f"{'Filename':<25} {'Semula (MB)':<13} {'Hasil (MB)':<13} {'Hemat (MB)':<13} {'% Hemat'}")
    print("-" * 75)
    for item in top_savings:
        if item["saved_bytes"] > 0:
            orig_m = item['orig_size'] / (1024*1024)
            new_m = item['new_size'] / (1024*1024)
            saved_m = item['saved_bytes'] / (1024*1024)
            print(f"{item['filename']:<25} {orig_m:<13.2f} {new_m:<13.2f} {saved_m:<13.2f} {item['saved_pct']:.1f}%")

if __name__ == "__main__":
    workspace = Path(__file__).resolve().parent.parent
    mobile_dir = workspace / "mobile"
    backup_dir = workspace / "backup_gif_original"
    optimize_gifs(mobile_dir, backup_dir)
