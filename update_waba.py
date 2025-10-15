import argparse
import os
import time
import re


def backup_file(path):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.{timestamp}.bak"
    with open(path, "r", encoding="utf-8") as f_in, open(backup_path, "w", encoding="utf-8") as f_out:
        f_out.write(f_in.read())
    return backup_path

def update_waba(env_path, new_waba, dry_run=False):
    if not os.path.exists(env_path):
        print(f"[ERROR] .env file not found: {env_path}")
        return
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found = False
    old_value = None
    pattern = re.compile(r'^(\s*META_WABA_ID\s*=\s*)(.*)$')
    new_lines = []
    for line in lines:
        m = pattern.match(line)
        if m:
            found = True
            old_value = m.group(2)
            new_line = f"{m.group(1)}{new_waba}\n"
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"META_WABA_ID={new_waba}\n")

    print(f"[INFO] META_WABA_ID found: {found}")
    if old_value:
        print(f"[INFO] Old value: {old_value}")
    print(f"[INFO] New value: {new_waba}")

    if dry_run:
        print("[DRY RUN] No changes written. Preview:")
        for l in new_lines:
            print(l, end="")
        return

    backup_path = backup_file(env_path)
    print(f"[INFO] Backup created at: {backup_path}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"[SUCCESS] META_WABA_ID updated in {env_path}")


def main():
    parser = argparse.ArgumentParser(description="Update META_WABA_ID in .env file.")
    parser.add_argument("--env", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("--new", required=True, help="New META_WABA_ID value")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    update_waba(args.env, args.new, args.dry_run)

if __name__ == "__main__":
    main()
