#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Mikael Masson
"""Horai — Standalone M365/IMAP mailbox dumper.

Dumps an entire mailbox (all folders) into mbox files, bundled in a tar.gz
archive. No server required, no complex setup — just Python 3.10+ and msal.

Named after the Horai (Horai), the Greek goddesses of seasons and order,
companions of Hermes.

Usage:
    # M365 (OAuth2 device flow — no credentials to store)
    python horai.py --email user@company.com --name client-dupont

    # Generic IMAP (Gmail with app password, Fastmail, etc.)
    python horai.py --email user@gmail.com --name gmail-perso --imap

    # Custom IMAP server
    python horai.py --email user@example.com --name custom \\
        --imap --host imap.example.com --port 993

    # Resume an interrupted dump (skips already-dumped folders)
    python horai.py --email user@company.com --name client-dupont --resume

    # Dump specific folders only
    python horai.py --email user@company.com --name client-dupont \\
        --folders INBOX "Sent Items"

    # Write archive to a specific directory
    python horai.py --email user@company.com --name client-dupont \\
        --output /mnt/backup/

Output:
    ./client-dupont_2026-04-01.tar.gz
    Contains one .mbox file per IMAP folder.

Compatible with Hermes (github.com/mikaelmasson/hermes) for import.
"""

from __future__ import annotations

import argparse
import getpass
import imaplib
import mailbox
import os
import re
import shutil
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path


# ── Constants ────────────────────────────────────────────────────────────────

# Thunderbird's well-known public client ID — safe to embed, read-only OAuth2 scopes.
THUNDERBIRD_CLIENT_ID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["https://outlook.office.com/IMAP.AccessAsUser.All"]

# How many message UIDs to fetch per IMAP round-trip.
# 500 is a good balance between speed and memory usage.
BATCH_SIZE = 500

# Exponential back-off delays (seconds) before reconnect attempts.
RECONNECT_DELAYS = [2, 8, 32]

# Domain → (host, port) lookup table for common IMAP providers.
KNOWN_SERVERS: dict[str, tuple[str, int]] = {
    "gmail.com": ("imap.gmail.com", 993),
    "googlemail.com": ("imap.gmail.com", 993),
    "outlook.com": ("outlook.office365.com", 993),
    "hotmail.com": ("outlook.office365.com", 993),
    "live.com": ("outlook.office365.com", 993),
    "yahoo.com": ("imap.mail.yahoo.com", 993),
    "yahoo.fr": ("imap.mail.yahoo.com", 993),
    "fastmail.com": ("imap.fastmail.com", 993),
    "fastmail.fm": ("imap.fastmail.com", 993),
    "icloud.com": ("imap.mail.me.com", 993),
    "me.com": ("imap.mail.me.com", 993),
    "free.fr": ("imap.free.fr", 993),
    "orange.fr": ("imap.orange.fr", 993),
    "laposte.net": ("imap.laposte.net", 993),
    "protonmail.com": ("127.0.0.1", 1143),  # Requires ProtonMail Bridge
    "proton.me": ("127.0.0.1", 1143),       # Requires ProtonMail Bridge
}


# ── IMAP helpers ─────────────────────────────────────────────────────────────


def _decode_modified_utf7(s: str) -> str:
    """Decode an IMAP modified UTF-7 encoded folder name to a Unicode string.

    IMAP folder names are encoded in a variant of UTF-7 where Base64 ranges
    are delimited by '&' and '-', and '/' is replaced by ','.

    Args:
        s: Encoded folder name from the IMAP LIST response.

    Returns:
        Human-readable folder name.
    """
    if "&" not in s:
        return s
    import base64

    result: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "&":
            end = s.index("-", i + 1)
            if end == i + 1:
                result.append("&")
            else:
                encoded = s[i + 1 : end].replace(",", "/")
                padding = 4 - len(encoded) % 4
                if padding != 4:
                    encoded += "=" * padding
                decoded = base64.b64decode(encoded).decode("utf-16-be")
                result.append(decoded)
            i = end + 1
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


def _encode_modified_utf7(s: str) -> str:
    """Encode a Unicode folder name to IMAP modified UTF-7.

    This is the inverse of _decode_modified_utf7 and is required when
    selecting a folder that contains non-ASCII characters.

    Args:
        s: Unicode folder name.

    Returns:
        IMAP modified UTF-7 encoded string suitable for IMAP commands.
    """
    import base64

    result: list[str] = []
    non_ascii: list[str] = []

    def flush_non_ascii() -> None:
        if non_ascii:
            raw = "".join(non_ascii).encode("utf-16-be")
            encoded = base64.b64encode(raw).decode("ascii").rstrip("=")
            encoded = encoded.replace("/", ",")
            result.append("&" + encoded + "-")
            non_ascii.clear()

    for ch in s:
        if ch == "&":
            flush_non_ascii()
            result.append("&-")
        elif 0x20 <= ord(ch) <= 0x7E:
            flush_non_ascii()
            result.append(ch)
        else:
            non_ascii.append(ch)

    flush_non_ascii()
    return "".join(result)


# ── Connection ────────────────────────────────────────────────────────────────


def connect_m365(email: str) -> imaplib.IMAP4_SSL:
    """Authenticate against Microsoft 365 via OAuth2 device flow and XOAUTH2.

    Uses Thunderbird's public client ID — no application registration needed.
    The OAuth2 token is cached locally so subsequent runs are silent.

    Args:
        email: The M365 / Office 365 email address to authenticate.

    Returns:
        An authenticated IMAP4_SSL connection ready for use.

    Raises:
        SystemExit: If msal is not installed or authentication fails.
    """
    try:
        import msal
    except ImportError:
        print("ERROR: msal is not installed. Run: pip install msal")
        sys.exit(1)

    cache_file = Path(f".token_cache_{email}.json")
    cache = msal.SerializableTokenCache()
    if cache_file.exists():
        cache.deserialize(cache_file.read_text())

    app = msal.PublicClientApplication(
        THUNDERBIRD_CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )

    # Attempt silent token refresh from cache before prompting.
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result or "access_token" not in result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "error" in flow:
            print(f"ERROR: {flow.get('error_description', flow['error'])}")
            sys.exit(1)
        print(f"\n  Open:  {flow['verification_uri']}")
        print(f"  Code:  {flow['user_code']}\n")
        result = app.acquire_token_by_device_flow(flow)
        if "error" in result:
            print(f"ERROR: {result.get('error_description', result['error'])}")
            sys.exit(1)

    # Persist token cache with restricted permissions.
    if cache.has_state_changed:
        cache_file.write_text(cache.serialize())
        os.chmod(cache_file, 0o600)

    token = result["access_token"]
    imap = imaplib.IMAP4_SSL("outlook.office365.com", 993)
    auth_string = f"user={email}\x01auth=Bearer {token}\x01\x01"
    imap.authenticate("XOAUTH2", lambda _: auth_string.encode())
    return imap


def connect_imap(
    email: str,
    password: str,
    host: str | None,
    port: int,
) -> imaplib.IMAP4_SSL:
    """Connect to an IMAP server using standard login/password authentication.

    If no host is provided, the server is auto-detected from the email domain
    using KNOWN_SERVERS. Falls back to ``imap.<domain>`` if unknown.

    Args:
        email: Email address (used for login and domain detection).
        password: IMAP password or app-specific password.
        host: Explicit IMAP hostname, or None for auto-detection.
        port: IMAP port (default 993 for TLS).

    Returns:
        An authenticated IMAP4_SSL connection ready for use.
    """
    if not host:
        domain = email.split("@")[-1].lower()
        host, port = KNOWN_SERVERS.get(domain, (f"imap.{domain}", 993))
    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(email, password)
    return imap


# ── Folder operations ─────────────────────────────────────────────────────────


def list_folders(imap: imaplib.IMAP4_SSL) -> list[str]:
    """Return a sorted list of all IMAP folder names.

    Decodes IMAP modified UTF-7 folder names to Unicode.

    Args:
        imap: An authenticated IMAP connection.

    Returns:
        Sorted list of human-readable folder names.
    """
    status, data = imap.list()
    if status != "OK":
        return []
    folders: list[str] = []
    for line in data:
        if not line:
            continue
        raw = line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line
        match = re.match(r'\(.*?\)\s+"(.*)"\s+"?(.*)"?', raw)
        if match:
            name = match.group(2).strip('"')
            name = _decode_modified_utf7(name)
            folders.append(name)
    return sorted(folders)


def fetch_folder(
    imap: imaplib.IMAP4_SSL,
    folder: str,
    mbox_path: Path,
    resume_uids: set[int] | None = None,
) -> int:
    """Fetch all messages from one IMAP folder and append them to an mbox file.

    Messages are fetched in batches of BATCH_SIZE to avoid timeouts on large
    folders. Transient IMAP errors trigger exponential back-off retries.

    Args:
        imap: An authenticated IMAP connection.
        folder: The folder name to dump (Unicode).
        mbox_path: Destination path for the mbox file.
        resume_uids: Set of UIDs already stored; those will be skipped.

    Returns:
        Number of messages written to the mbox file.
    """
    encoded_folder = _encode_modified_utf7(folder)
    status, _ = imap.select(f'"{encoded_folder}"', readonly=True)
    if status != "OK":
        return 0

    status, data = imap.uid("search", None, "ALL")
    if status != "OK" or not data[0]:
        return 0

    all_uids = [int(u) for u in data[0].split()]
    if resume_uids:
        all_uids = [u for u in all_uids if u not in resume_uids]
    if not all_uids:
        return 0

    mbox_file = mailbox.mbox(str(mbox_path))
    mbox_file.lock()
    count = 0
    t0 = time.monotonic()
    total = len(all_uids)

    try:
        for i in range(0, total, BATCH_SIZE):
            batch = all_uids[i : i + BATCH_SIZE]
            uid_set = ",".join(str(u) for u in batch)

            # Fetch with exponential back-off on transient errors.
            for attempt, delay in enumerate(RECONNECT_DELAYS + [0]):
                try:
                    status, raw_data = imap.uid("fetch", uid_set, "(RFC822)")
                    break
                except (imaplib.IMAP4.abort, imaplib.IMAP4.error, ConnectionError) as exc:
                    if attempt < len(RECONNECT_DELAYS):
                        print(f"\n    Retry in {delay}s ({exc})")
                        time.sleep(delay)
                    else:
                        raise

            if status != "OK":
                continue

            for item in raw_data:
                if isinstance(item, tuple) and len(item) >= 2:
                    raw = item[1]
                    if isinstance(raw, bytes):
                        try:
                            msg = mailbox.mboxMessage(raw)
                            mbox_file.add(msg)
                            count += 1
                        except Exception:
                            pass

            # Flush to disk every batch so progress isn't lost on interrupt
            mbox_file.flush()

            done = min(i + BATCH_SIZE, total)
            elapsed = time.monotonic() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = int((total - done) / rate) if rate > 0 else 0
            eta_str = f"{eta // 60}m{eta % 60:02d}s" if eta >= 60 else f"{eta}s"
            print(f"    {done}/{total} ({rate:.0f} msg/s, ETA {eta_str})   ", end="\r", flush=True)
    finally:
        mbox_file.unlock()
        mbox_file.close()

    # Clear the progress line
    print(f"    {total}/{total}" + " " * 30, end="\r", flush=True)
    return count


# ── CLI entry point ───────────────────────────────────────────────────────────


def main() -> None:
    """Parse arguments and orchestrate the mailbox dump."""
    parser = argparse.ArgumentParser(
        prog="horai",
        description="Dump an entire email mailbox into a portable mbox tar.gz archive.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  horai --email user@company.com --name backup-2026\n"
            "  horai --email user@gmail.com --name gmail --imap\n"
            "  horai --email user@example.com --name custom \\\n"
            "        --imap --host imap.example.com --port 993\n"
            "  horai --email user@company.com --name backup --resume\n"
            "  horai --email user@company.com --name backup \\\n"
            '        --folders INBOX "Sent Items"\n'
        ),
    )
    parser.add_argument("--email", required=True, help="Email address to dump")
    parser.add_argument("--name", required=True, help="Archive base name (used in the filename)")
    parser.add_argument(
        "--imap",
        action="store_true",
        help="Use IMAP login/password instead of M365 OAuth2 device flow",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="IMAP server hostname (auto-detected from domain if omitted)",
    )
    parser.add_argument("--port", type=int, default=993, help="IMAP port (default: 993)")
    parser.add_argument(
        "--password",
        default=None,
        help="IMAP password (prompted interactively if omitted)",
    )
    parser.add_argument(
        "--output",
        default=".",
        help="Output directory for the tar.gz archive (default: current directory)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted dump — skip folders already completed",
    )
    parser.add_argument(
        "--folders",
        nargs="*",
        default=None,
        metavar="FOLDER",
        help="Dump only these folders (default: all folders)",
    )
    args = parser.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_name = f"{args.name}_{today}"
    output_dir = Path(args.output)
    work_dir = output_dir / f".work_{archive_name}"
    archive_path = output_dir / f"{archive_name}.tar.gz"

    # ── Connect ──────────────────────────────────────────────────────────────
    print(f"Connecting to {args.email}...")
    if args.imap:
        password = args.password or getpass.getpass("Password (app password for Gmail/Yahoo): ")
        imap = connect_imap(args.email, password, args.host, args.port)
    else:
        imap = connect_m365(args.email)
    print("Connected.\n")

    # ── List folders ─────────────────────────────────────────────────────────
    folders = list_folders(imap)
    if args.folders:
        folders = [f for f in folders if f in args.folders]
    print(f"Found {len(folders)} folder(s):")
    for f in folders:
        print(f"  - {f}")
    print()

    # ── Prepare work directory ────────────────────────────────────────────────
    work_dir.mkdir(parents=True, exist_ok=True)

    # Track completed folders for --resume support.
    done_marker = work_dir / ".done_folders"
    done_folders: set[str] = set()
    if args.resume and done_marker.exists():
        done_folders = set(done_marker.read_text().strip().splitlines())
        print(f"Resuming: {len(done_folders)} folder(s) already completed.\n")

    # ── Dump each folder ──────────────────────────────────────────────────────
    total_messages = 0
    for i, folder in enumerate(folders, 1):
        safe_name = (
            folder.replace("/", "_")
                  .replace("\\", "_")
                  .replace(" ", "_")
        )
        mbox_path = work_dir / f"{safe_name}.mbox"

        if folder in done_folders:
            print(f"[{i}/{len(folders)}] {folder} — skipped (already done)")
            continue

        print(f"[{i}/{len(folders)}] {folder}...", end=" ", flush=True)
        try:
            count = fetch_folder(imap, folder, mbox_path)
            total_messages += count
            print(f"{count} messages")

            with open(done_marker, "a") as fh:
                fh.write(folder + "\n")

        except Exception as exc:
            print(f"ERROR: {exc}")

    # ── Logout ────────────────────────────────────────────────────────────────
    try:
        imap.logout()
    except Exception:
        pass

    # ── Pack archive ──────────────────────────────────────────────────────────
    print(f"\nPacking {archive_path}...")
    with tarfile.open(archive_path, "w:gz") as tar:
        for mbox_file in sorted(work_dir.glob("*.mbox")):
            if mbox_file.stat().st_size > 0:
                tar.add(mbox_file, arcname=mbox_file.name)

    size_mb = archive_path.stat().st_size / (1024 * 1024)

    # Clean up temporary work directory.
    shutil.rmtree(work_dir)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("Done.")
    print(f"  Archive  : {archive_path}")
    print(f"  Size     : {size_mb:.1f} MB")
    print(f"  Messages : {total_messages}")
    print(f"  Folders  : {len(folders)}")
    print()
    print("Compatible with Hermes (github.com/mikaelmasson/hermes) for import:")
    print(f"  1. Copy {archive_path.name} to your Hermes /imports/ volume")
    print(f"  2. hermes import-archive /imports/{archive_path.name} --name {args.name}")


if __name__ == "__main__":
    main()
